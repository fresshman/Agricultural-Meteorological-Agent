# -*- coding: utf-8 -*-
"""智能问答路由：会话记忆 + UQ 置信度分级 + 合规审查 + 短临降水提示 + 反馈闭环"""
import asyncio
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import get_agent_for_chat, get_current_user, get_settings
from ..schemas.chat import (
    ChatRequest, ChatResponse, DisasterWarningItem, DiseaseRiskItem,
    ComplianceInfo, UncertaintyInfo,
    FeedbackRequest, FeedbackResponse, FeedbackStatsResponse,
)

router = APIRouter()
logger = logging.getLogger("agri-backend.chat")

USER_TYPE_MAP = {
    "普通农户": "FARMER",
    "种植大户": "LARGE_FARMER",
    "农技人员": "TECHNICIAN",
}

def _resolve_crop(name: str):
    """中文作物名 → CropType 枚举；未知名称回退 CORN"""
    from src.models import CropType
    try:
        return CropType(name.strip() if isinstance(name, str) else "")
    except (ValueError, KeyError, TypeError):
        return CropType.CORN

NOWCAST_HOURS = 6

# 准备上下文阶段每这么久没动静就补一帧进度，保证连接上始终有字节在流
HEARTBEAT_SECONDS = 2.0


def _sse(payload: dict) -> str:
    """一行 SSE data 帧"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------- 短临降水提示 ----------

def _compute_nowcast(weather_list) -> Optional[str]:
    """从已拉取的气象列表计算未来 NOWCAST_HOURS 小时内降水提示（不再单独请求 API）"""
    if not weather_list:
        return None
    now = datetime.now()
    end = now + timedelta(hours=NOWCAST_HOURS)

    def _ts(d):
        # weather_list 里的 timestamp 是 datetime（WeatherData.dict()），不是字符串；
        # 只按字符串解析会让未来时次永远为空 → 短临降水提示从未触发
        if isinstance(d, datetime):
            return d
        if isinstance(d, date):
            return datetime.combine(d, datetime.min.time())
        try:
            return datetime.fromisoformat(str(d))
        except Exception:
            return None

    future = []
    for w in weather_list:
        ts = _ts(w.get("timestamp", ""))
        if ts and now <= ts <= end:
            future.append(w)

    rainy = [w for w in future if w.get("precipitation") and w.get("precipitation", 0) > 0.1]
    if not rainy:
        return None

    first = rainy[0]
    try:
        ts = _ts(first.get("timestamp"))
        hour = ts.hour if ts else None
    except Exception:
        hour = None
    total = sum(w.get("precipitation", 0) for w in rainy)
    when = f"{hour}时前后" if hour is not None else "近期"
    if total >= 10:
        level = "较强降水"
    elif total >= 3:
        level = "明显降水"
    else:
        level = "弱降水"
    return (
        f"短临提示：未来{NOWCAST_HOURS}小时内{when}有{level}"
        f"（累计约{total:.1f}mm），喷药/施肥/收获等作业请规避该时段。"
    )


# ---------- 合规 + UQ ----------

def _classify_compliance(response) -> tuple:
    """调用 AdviceClassificationTool 做建议分级 + 不确定性标注"""
    try:
        from src.tools.compliance_tools import AdviceClassificationTool
        tool = AdviceClassificationTool()
        classification = tool.classify_advice(
            advice_id=f"api_{uuid.uuid4().hex[:12]}",
            content=response.content or "",
            forecast_days=1,
        )
        compliance = ComplianceInfo(
            advice_level=getattr(classification.advice_level, "value", str(classification.advice_level)),
            disclaimer=classification.disclaimer,
            requires_local_consultation=bool(classification.requires_local_consultation),
            regulatory_notes=list(classification.regulatory_notes or []),
        )
        uncertainty = UncertaintyInfo(
            level=getattr(classification.uncertainty, "value", str(classification.uncertainty)),
            confidence_score=float(classification.confidence_score),
        )
        return compliance, uncertainty
    except Exception as e:
        logger.warning(f"合规分级失败（不影响主流程）: {e}")
        return ComplianceInfo(), UncertaintyInfo()


# ---------- 响应组装 ----------

def _build_response(response, req: ChatRequest, nowcast: Optional[str]) -> ChatResponse:
    disaster_warnings = []
    for w in (response.disaster_warnings or []):
        disaster_warnings.append(DisasterWarningItem(
            disaster_type=getattr(w.disaster_type, "value", str(w.disaster_type)),
            risk_level=getattr(w.risk_level, "value", str(w.risk_level)),
            occur_time=str(w.occur_time) if getattr(w, "occur_time", None) else None,
            duration=getattr(w, "duration", None),
            intensity=getattr(w, "intensity", None),
            defense_measures=getattr(w, "defense_measures", []) or [],
            emergency_actions=getattr(w, "emergency_actions", []) or [],
        ))

    disease_risks = []
    for r in (response.disease_risks or []):
        disease_risks.append(DiseaseRiskItem(
            disease_name=r.disease_name,
            risk_level=getattr(r.risk_level, "value", str(r.risk_level)),
            occur_probability=getattr(r, "occur_probability", None),
            control_measures=getattr(r, "control_measures", []) or [],
            prevention_methods=getattr(r, "prevention_methods", []) or [],
        ))

    compliance, uncertainty = _classify_compliance(response)

    return ChatResponse(
        session_id=req.session_id,
        content=response.content,
        evidence=response.evidence or "",
        confidence=response.confidence or 0.0,
        disaster_warnings=disaster_warnings,
        disease_risks=disease_risks,
        compliance=compliance,
        uncertainty=uncertainty,
        nowcast_alert=nowcast,
    )


# ---------- 主问答接口 ----------

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, agent=Depends(get_agent_for_chat), user: dict = Depends(get_current_user)):
    """智能问答（完整返回，含会话记忆/合规/UQ/短临提示）"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    if not req.session_id:
        req.session_id = f"s_{uuid.uuid4().hex[:12]}"

    # 身份只认服务端会话：未登录（AUTH_REQUIRED=true）由依赖直接 401，不接受请求体覆盖
    user_id = user["id"]

    from src.models import UserType, CropType, Location

    user_type_val = getattr(UserType, USER_TYPE_MAP.get(req.user_type, "FARMER"), UserType.FARMER)
    crop_type_val = _resolve_crop(req.crop_type)

    location = Location(
        province=req.province, city=req.city,
        latitude=req.latitude, longitude=req.longitude,
    )

    try:
        # 复用 prepare_query 拿 ctx（含 weather_list），nowcast 不再二次请求气象 API
        ctx = await agent.prepare_query(
            query=req.query.strip(),
            user_id=user_id,
            session_id=req.session_id,
            user_type=user_type_val,
            location=location,
            crop_type=crop_type_val,
        )
        if agent.llm_available:
            final_response = await agent.llm_client.chat_async(ctx["messages"], temperature=0.3)
        else:
            final_response = agent._fallback_response(ctx["structured_results"], ctx["weather_data"])

        response = agent._finalize_response(ctx, final_response)
        nowcast = _compute_nowcast(ctx.get("weather_list") or [])
        return _build_response(response, req, nowcast)
    except Exception as e:
        logger.error(f"问答处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {e}")


@router.post("/stream")
async def chat_stream(req: ChatRequest, agent=Depends(get_agent_for_chat), user: dict = Depends(get_current_user)):
    """智能问答（SSE 流式）：status 进度 + token 逐步推送，done 事件携带元数据"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    if not req.session_id:
        req.session_id = f"s_{uuid.uuid4().hex[:12]}"

    # 身份只认服务端会话：未登录（AUTH_REQUIRED=true）由依赖直接 401，不接受请求体覆盖
    user_id = user["id"]

    async def event_generator() -> AsyncGenerator[str, None]:
        started_at = time.perf_counter()
        ttft = None            # 首个 token 相对开流的秒数
        n_tokens = 0
        outcome = "done"
        prepare_task = None

        try:
            from src.models import UserType, Location
            user_type_val = getattr(UserType, USER_TYPE_MAP.get(req.user_type, "FARMER"), UserType.FARMER)
            crop_type_val = _resolve_crop(req.crop_type)
            location = Location(
                province=req.province, city=req.city,
                latitude=req.latitude, longitude=req.longitude,
            )

            # 意图/天气/规则/检索这段没有 token 可吐，用进度帧把连接填上，
            # 否则前端只能对着空气泡转圈，看起来就像问答挂了
            yield _sse({"type": "status", "content": "正在识别意图、获取气象、检索知识库…"})
            prepare_task = asyncio.create_task(agent.prepare_query(
                query=req.query.strip(),
                user_id=user_id,
                session_id=req.session_id,
                user_type=user_type_val,
                location=location,
                crop_type=crop_type_val,
            ))
            waited = 0.0
            while True:
                ready, _ = await asyncio.wait({prepare_task}, timeout=HEARTBEAT_SECONDS)
                if ready:
                    break
                waited += HEARTBEAT_SECONDS
                yield _sse({"type": "status", "content": f"上下文准备中（已 {waited:.0f} 秒）…"})
            ctx = prepare_task.result()

            # nowcast 复用 ctx 已拉取的气象数据（不再二次请求）
            nowcast = _compute_nowcast(ctx.get("weather_list") or [])
            if nowcast:
                yield _sse({"type": "nowcast", "content": nowcast})

            yield _sse({"type": "status", "content": "开始生成回答…"})

            tokens = []
            if not agent.llm_available:
                # LLM 不可用：一次性产出规则引擎兜底内容
                fallback = agent._fallback_response(ctx["structured_results"], ctx["weather_data"])
                tokens.append(fallback)
                if fallback:
                    yield _sse({"type": "token", "content": fallback})
            else:
                async for chunk in agent.llm_client.astream_chat(ctx["messages"], temperature=0.3):
                    if ttft is None:
                        ttft = time.perf_counter() - started_at
                    n_tokens += 1
                    tokens.append(chunk)
                    if chunk:
                        yield _sse({"type": "token", "content": chunk})

            content = "".join(tokens)
            response = agent._finalize_response(ctx, content)

            meta = _build_response(response, req, nowcast)
            meta.content = ""
            yield _sse({"type": "done", "meta": meta.model_dump()})
        except Exception as e:  # noqa: BLE001
            outcome = "error"
            error_text = str(e) or type(e).__name__
            logger.error(f"流式问答失败: {error_text}", exc_info=True)
            yield _sse({"type": "error", "message": error_text})
        finally:
            if prepare_task is not None and not prepare_task.done():
                prepare_task.cancel()
            # access 日志打在响应头那一刻，看不出成败；这条才是真正的问题答案
            logger.info(
                "流式问答收口 | 结果=%s 首token=%.1fs 总耗时=%.1fs token块=%d 问题=%.40s",
                outcome,
                ttft if ttft is not None else -1.0,
                time.perf_counter() - started_at,
                n_tokens,
                req.query.strip(),
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------- 反馈闭环 ----------

def _feedback_db():
    s = get_settings()
    db_path = Path(s.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS advice_feedback (
            message_id TEXT PRIMARY KEY,
            session_id TEXT,
            rating TEXT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP
        )
    ''')
    return conn


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """建议采纳反馈：accepted / rejected / partial"""
    if req.rating not in ("accepted", "rejected", "partial"):
        raise HTTPException(status_code=400, detail="rating 必须是 accepted/rejected/partial")
    conn = _feedback_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO advice_feedback (message_id, session_id, rating, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (req.message_id, req.session_id, req.rating, req.reason, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return FeedbackResponse(status=True, message="反馈已记录")


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats():
    """采纳率统计（运营指标）"""
    conn = _feedback_db()
    try:
        rows = conn.execute("SELECT rating, COUNT(*) FROM advice_feedback GROUP BY rating").fetchall()
        counts = {r: c for r, c in rows}
        total = sum(counts.values())
        accepted = counts.get("accepted", 0)
        return FeedbackStatsResponse(
            total=total,
            accepted=accepted,
            rejected=counts.get("rejected", 0),
            partial=counts.get("partial", 0),
            acceptance_rate=round(accepted / total, 4) if total else 0.0,
        )
    finally:
        conn.close()

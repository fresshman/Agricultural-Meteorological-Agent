# -*- coding: utf-8 -*-
"""预警分析路由：包装 weather_warning_tools"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_weather_processor
from ..schemas.warning import (
    DisasterWarningRequest, PestWarningRequest, SuitabilityRequest,
    WarningResponse, WarningItem,
)

router = APIRouter()
logger = logging.getLogger("agri-backend.warning")


def _resolve_crop(name: str):
    """中文作物名 → CropType 枚举；未知名称回退 CORN"""
    from src.models import CropType
    try:
        return CropType(name.strip() if isinstance(name, str) else "")
    except (ValueError, KeyError, TypeError):
        return CropType.CORN

GROWTH_STAGE_MAP = {
    "播种期": "SOWING", "出苗期": "SEEDLING", "分蘖期": "TILLERING",
    "拔节期": "JOINTING", "抽穗期": "HEADING", "开花期": "FLOWERING",
    "灌浆期": "FILLING", "成熟期": "MATURITY",
}
OPERATION_WINDOW_MAP = {
    "播种": "SOWING", "移栽": "TRANSPLANTING", "授粉": "POLLINATION",
    "喷药": "SPRAYING", "追肥": "FERTILIZING", "采收": "HARVESTING", "灌溉": "IRRIGATING",
}


async def _fetch_weather(req, wp):
    """拉取气象预报数据供预警工具使用"""
    from src.models import Location
    location = Location(province=req.province, city=req.city, latitude=req.latitude, longitude=req.longitude)
    now = datetime.now()
    return await wp.fetch_weather_data(
        location=location, start_time=now, end_time=now + timedelta(hours=72),
    )


@router.post("/disaster", response_model=WarningResponse)
async def disaster_warning(req: DisasterWarningRequest, wp=Depends(get_weather_processor)):
    """灾害风险预警"""
    from src.tools.weather_warning_tools import DisasterWarningTool
    from src.models import CropType, GrowthStage

    if not wp:
        return WarningResponse(status=False, message="气象 API 未配置，无法进行预警分析")

    try:
        weather = await _fetch_weather(req, wp)
        crop_val = _resolve_crop(req.crop_type)
        stage_val = None
        if req.growth_stage:
            stage_val = getattr(GrowthStage, GROWTH_STAGE_MAP.get(req.growth_stage), None)

        tool = DisasterWarningTool()
        warnings = tool.predict_disaster(weather, crop_val, stage_val)

        items = []
        for w in warnings:
            items.append(WarningItem(
                type=getattr(w.disaster_type, "value", str(w.disaster_type)),
                risk_level=getattr(w.risk_level, "value", str(w.risk_level)),
                details={
                    "occur_time": str(w.occur_time) if hasattr(w, "occur_time") else None,
                    "duration": getattr(w, "duration", None),
                    "intensity": getattr(w, "intensity", None),
                    "defense_measures": getattr(w, "defense_measures", []),
                    "emergency_actions": getattr(w, "emergency_actions", []),
                },
            ))
        return WarningResponse(status=True, warnings=items)
    except Exception as e:
        logger.error(f"灾害预警失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pest", response_model=WarningResponse)
async def pest_warning(req: PestWarningRequest, wp=Depends(get_weather_processor)):
    """病虫害风险预警"""
    from src.tools.weather_warning_tools import PestDiseasePredictionTool
    from src.models import CropType, GrowthStage

    if not wp:
        return WarningResponse(status=False, message="气象 API 未配置，无法进行预警分析")

    try:
        weather = await _fetch_weather(req, wp)
        crop_val = _resolve_crop(req.crop_type)
        stage_val = None
        if req.growth_stage:
            stage_val = getattr(GrowthStage, GROWTH_STAGE_MAP.get(req.growth_stage), None)

        tool = PestDiseasePredictionTool()
        risks = tool.predict_pest_disease_risk(weather, crop_val, stage_val)

        items = []
        for r in risks:
            items.append(WarningItem(
                type=getattr(r.pest_disease_type, "value", str(r.pest_disease_type)),
                risk_level=getattr(r.risk_level, "value", str(r.risk_level)),
                details={
                    "occur_probability": getattr(r, "occur_probability", None),
                    "prevention_measures": getattr(r, "prevention_measures", []),
                    "control_measures": getattr(r, "control_measures", []),
                    "confidence": getattr(r, "confidence", None),
                },
            ))
        return WarningResponse(status=True, warnings=items)
    except Exception as e:
        logger.error(f"病虫害预警失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suitability", response_model=WarningResponse)
async def suitability(req: SuitabilityRequest, wp=Depends(get_weather_processor)):
    """农事操作适宜度评估"""
    from src.tools.weather_warning_tools import WeatherSuitabilityTool
    from src.models import CropType, OperationWindow

    if not wp:
        return WarningResponse(status=False, message="气象 API 未配置，无法评估适宜度")

    try:
        weather = await _fetch_weather(req, wp)
        op_val = getattr(OperationWindow, OPERATION_WINDOW_MAP.get(req.operation_type, "SOWING"), OperationWindow.SOWING)
        crop_val = None
        if req.crop_type:
            crop_val = _resolve_crop(req.crop_type)

        tool = WeatherSuitabilityTool()
        score = tool.assess_operation_suitability(op_val, weather, crop_val)

        return WarningResponse(
            status=True,
            warnings=[WarningItem(
                type=req.operation_type,
                risk_level=getattr(score.risk_level, "value", str(score.risk_level)) if hasattr(score, "risk_level") else "",
                details=score.model_dump() if hasattr(score, "model_dump") else score.__dict__,
            )],
        )
    except Exception as e:
        logger.error(f"适宜度评估失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

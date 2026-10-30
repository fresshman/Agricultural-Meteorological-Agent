# -*- coding: utf-8 -*-
"""FastAPI 入口：农业气象智能体后端"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .deps import get_agent, get_weather_processor, get_amap, get_settings
from .auth import _init_auth_db, session_secret_key, cookie_secure
from .routers import health, chat, weather, location, farm, warning
from .routers.auth import router as auth_router, auth_callback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agri-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时预初始化单例（失败不阻断启动，路由里会兜底）
    s = get_settings()
    logger.info("=" * 60)
    logger.info("🌾 农业气象智能体 FastAPI 后端启动中...")
    logger.info("=" * 60)
    try:
        _init_auth_db()
        logger.info("✅ 账户授权数据库已就绪")
    except Exception as e:
        logger.error(f"❌ 账户授权数据库初始化失败: {e}")
    logger.info(f"LLM 模型: {s.LLM_MODEL}")
    logger.info(f"Embedding 模型: {s.EMBEDDING_MODEL}")
    logger.info(f"LLM API Key: {'✅' if s.LLM_API_KEY else '❌ 未配置'}")
    logger.info(f"气象 API Key: {'✅' if s.WEATHER_API_KEY else '❌ 未配置'}")
    logger.info(f"高德 API Key: {'✅' if get_amap() else '❌ 未配置'}")

    try:
        agent = get_agent()
        logger.info(f"✅ 智能体初始化成功 | RAG={'启用' if agent.rag_engine and agent.rag_engine.vector_db else '未启用'}")
    except Exception as e:
        logger.error(f"❌ 智能体初始化失败: {e}")

    wp = get_weather_processor()
    logger.info(f"气象处理器: {'✅' if wp else '⚠️ 未启用'}")
    logger.info("=" * 60)
    yield
    logger.info("后端关闭")


app = FastAPI(
    title="农业气象智能体 API",
    description="基于气象数据和农业知识的智能农事决策助手",
    version="2.0.0",
    lifespan=lifespan,
)

# 修复：CORS 安全配置
# 前端经 nginx 同源反代访问 /api，无需跨域；故不开放 credentials+任意来源的组合。
# 如需跨域调试，可通过环境变量 CORS_ORIGINS 显式指定（逗号分隔）。
import os

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
if _cors_origins_env:
    _cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    _cors_allow_credentials = True
else:
    _cors_origins = ["*"]
    _cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 账户授权依赖：authlib 的 OAuth 状态回环（authorize_redirect ↔ authorize_access_token）需要 request.session
# 与魔搭官方示例一致：same_site=lax + https_only（Studio 必然 HTTPS，否则 state cookie 会被浏览器丢弃）
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret_key(),
    same_site="lax",
    https_only=cookie_secure(),
)

app.include_router(health.router, prefix="/api", tags=["健康"])
app.include_router(chat.router, prefix="/api/chat", tags=["智能问答"])
app.include_router(weather.router, prefix="/api/weather", tags=["气象数据"])
app.include_router(location.router, prefix="/api/location", tags=["地理编码"])
app.include_router(farm.router, prefix="/api/farm", tags=["农场管理"])
app.include_router(warning.router, prefix="/api/warning", tags=["预警分析"])
app.include_router(auth_router, tags=["账户授权"])

# 魔搭 OIDC 回调必须注册在 /api 前缀之外（参照魔搭创空间官方文档）
app.get("/auth/callback")(auth_callback)

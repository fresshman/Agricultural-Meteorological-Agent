# -*- coding: utf-8 -*-
"""FastAPI 后端依赖注入：单例化 agent / weather_processor / amap + 用户会话 / 每用户农场管理器"""
import logging
import os
import sys
import threading
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request

# 把 modelscope_space 根目录加入 sys.path，以便 import src / config
_BACKEND_DIR = Path(__file__).resolve().parent
_MODELSCOPE_ROOT = _BACKEND_DIR.parent.parent
if str(_MODELSCOPE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODELSCOPE_ROOT))

# 在导入 config.settings 之前加载 .env（settings 在 import 时读取环境变量）
load_dotenv(_MODELSCOPE_ROOT / ".env")

from config.settings import settings, user_db_path
from .auth import get_session_user

logger = logging.getLogger("agri-backend.deps")

# 智能体初始化很慢（要下载/加载 Embedding 模型），并发请求或预热线程可能同时进入，
# lru_cache 不保证只算一次，用锁串行化，避免起两份模型把内存打爆
_AGENT_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def get_agent():
    """单例获取 AgriculturalWeatherAgent"""
    with _AGENT_LOCK:
        from src.agents import AgriculturalWeatherAgent
        agent = AgriculturalWeatherAgent(
            llm_api_key=settings.LLM_API_KEY,
            weather_api_key=settings.WEATHER_API_KEY,
            weather_subscription_id=settings.WEATHER_SUBSCRIPTION_ID,
            llm_model=settings.LLM_MODEL,
            embedding_model=settings.EMBEDDING_MODEL,
        )
        return agent


@lru_cache(maxsize=1)
def get_weather_processor():
    """单例获取 WeatherProcessor；依赖导入/初始化失败时降级为 None，不拖垮整个服务。"""
    try:
        from src.data.weather_processor import WeatherProcessor
    except Exception as e:  # faiss/numpy 等重依赖导入失败时，天气接口降级而非启动崩溃
        logger.error(f"天气处理器依赖导入失败，气象功能将不可用: {e}")
        return None
    if settings.WEATHER_API_KEY and settings.WEATHER_SUBSCRIPTION_ID:
        return WeatherProcessor(
            api_key=settings.WEATHER_API_KEY,
            subscription_id=settings.WEATHER_SUBSCRIPTION_ID,
        )
    return None


@lru_cache(maxsize=1)
def get_amap():
    """单例获取高德地理编码客户端；依赖导入失败时降级为 None。"""
    try:
        from src.utils.amap_geocoding import AmapGeocoding
    except Exception as e:
        logger.error(f"高德地理编码依赖导入失败，定位功能将不可用: {e}")
        return None
    api_key = os.getenv("AMAP_API_KEY", "")
    if api_key:
        return AmapGeocoding(api_key)
    return None


@lru_cache(maxsize=1)
def get_farm_manager_deprecated():
    """（保留）单例获取农场管理器（SQLite 持久化版本，指向全局库）。"""
    from backend.app.services.farm_persistence import PersistentFarmManager
    return PersistentFarmManager()


def get_current_user(request: Request) -> dict:
    """FastAPI 依赖：当前登录用户（未登录抛 401）。"""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    return user


def get_optional_user(request: Request) -> dict | None:
    """FastAPI 依赖：当前登录用户（未登录返回 None，用于兼容未鉴权兜底）。"""
    return get_session_user(request)


# 每用户农场管理器缓存：key = user_id，value = PersistentFarmManager(指向该用户独立子库)
_FARM_MANAGERS: dict = {}


def get_farm_manager(user=Depends(get_current_user)):
    """按当前登录用户返回其独立子库的农场管理器（数据磁盘级隔离）。"""
    from backend.app.services.farm_persistence import PersistentFarmManager
    uid = user["id"]
    if uid not in _FARM_MANAGERS:
        _FARM_MANAGERS[uid] = PersistentFarmManager(db_path=str(user_db_path(uid)), user_id=uid)
    return _FARM_MANAGERS[uid]


def get_settings():
    return settings

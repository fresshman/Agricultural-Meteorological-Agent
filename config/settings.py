# -*- coding: utf-8 -*-
"""
农业气象智能体配置管理（ModelScope创空间版本）
"""
import os
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from pathlib import Path


# 项目根目录（config/ 的上一级 = modelscope_space/）
# 修复：将数据/知识库/日志路径统一基于根目录绝对化，避免依赖运行时工作目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 运行时数据根目录（auth.db + 每用户数据库）
# 默认容器内 data/；若部署环境提供持久卷，用 AGRI_DATA_DIR 指向挂载点即可整体迁移，无需改代码。
DATA_ROOT = Path(os.getenv("AGRI_DATA_DIR") or (BASE_DIR / "data"))


def user_db_path(user_id: str) -> Path:
    """每个用户独立的 SQLite 数据库路径（磁盘级隔离：{DATA_ROOT}/users/{user_id}/agri_weather.db）。"""
    user_dir = DATA_ROOT / "users" / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "agri_weather.db"


class Settings(BaseSettings):
    PROJECT_NAME: str = "农业气象智能体"
    VERSION: str = "1.0.0"

    DATABASE_PATH: str = str(DATA_ROOT / "agri_weather.db")
    KNOWLEDGE_BASE_PATH: str = str(BASE_DIR / "knowledge_bases")

    # 从环境变量读取，适配ModelScope Secrets
    # 中科天机气象预测API（官方示例：https://api.tjweather.com/v2）
    WEATHER_API_KEY: Optional[str] = os.getenv("WEATHER_API_KEY", None)
    WEATHER_API_URL: str = os.getenv("WEATHER_API_URL", "https://api.tjweather.com/v2")
    WEATHER_SUBSCRIPTION_ID: Optional[str] = os.getenv("WEATHER_SUBSCRIPTION_ID", None)

    # 默认模型改为 ModelScope 免费推理上可用的 Qwen/Qwen3.8-27B
    # （此前 GLM-5.3:Zhipu-Coding 跑完后该 Token 余额不足 → 429 code:1113；Qwen3.8-27B 经本地 curl 实测可用）
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Qwen/Qwen3.8-27B")
    # ModelScope模型ID格式（使用bge-large-zh-v1.5）
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-small-zh-v1.5")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", None)
    LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api-inference.modelscope.cn/v1")

    # ---------- 魔搭账户授权（OIDC / OAuth2 授权码流程） ----------
    # Studio 部署时由平台自动注入 OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET；本地开发手动填 .env
    OAUTH_CLIENT_ID: Optional[str] = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: Optional[str] = os.getenv("OAUTH_CLIENT_SECRET", "")
    # 平台注入的授权范围（空格分隔，创空间 OAuth 设置里勾选的结果），默认 openid + profile
    OAUTH_SCOPES: str = os.getenv("OAUTH_SCOPES") or "openid profile"
    # 魔搭 OIDC Issuer 地址（自动发现 /.well-known/openid-configuration）
    OPENID_PROVIDER_URL: str = os.getenv("OPENID_PROVIDER_URL", "https://www.modelscope.cn")
    # 魔搭创空间域名（用于拼 redirect_uri，如 your-studio.modelscope.cn）
    STUDIO_HOST: str = os.getenv("STUDIO_HOST", "")
    # Cookie 是否 secure（Studio HTTPS 下强制 true；本地 http 必须 false）
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    VECTOR_DB_PATH: str = str(BASE_DIR / "knowledge_bases" / "agri_knowledge")
    FAISS_INDEX_TYPE: str = "flat"

    MAX_HISTORY_LENGTH: int = 10
    MAX_CONTEXT_LENGTH: int = 4000

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(BASE_DIR / "logs" / "app.log")

    class Config:
        # 创空间不使用.env文件，使用环境变量
        case_sensitive = True


WEATHER_THRESHOLDS = {
    "播种": {
        "玉米": {"最低温度": 10, "适宜温度范围": (15, 25), "无霜期要求": 120},
        "小麦": {"春化温度": (0, 7), "春化天数": 30, "播种温度": (5, 15)},
        "水稻": {"最低温度": 12, "适宜温度范围": (18, 28)},
        "大豆": {"最低温度": 10, "适宜温度范围": (15, 25)},
    },
    "灌溉": {
        "土壤墒情下限": 60,
        "土壤墒情上限": 80,
        "降水阈值": 5,
    },
    "植保": {
        "风速上限": 3,
        "温度范围": (15, 30),
        "湿度上限": 85,
    },
    "施肥": {
        "降水阈值": 5,
        "温度范围": (15, 30),
        "风速上限": 4,
        "基肥": {
            "适宜时期": ["播种前", "苗期"],
            "注意事项": ["避免大雨前施肥", "结合耕作施入"]
        },
        "追肥": {
            "适宜时期": ["拔节期", "抽穗期", "灌浆期"],
            "注意事项": ["雨后施肥效果佳", "避开高温时段"]
        },
        "叶面肥": {
            "适宜时期": ["全生育期"],
            "注意事项": ["避开强光时段", "温度15-25℃最佳"]
        }
    },
    "收获": {
        "适宜天气": ["晴", "多云"],
        "避开天气": ["雨", "大风", "高温高湿"],
        "籽粒含水率上限": 20,
        "晾晒天数": 3,
    },
    "仓储": {
        "温度上限": 25,
        "湿度上限": 70,
        "通风要求": "良好",
        "防虫温度": 15,
    }
}

CROP_GROWTH_STAGES = {
    "玉米": ["播种期", "出苗期", "三叶期", "拔节期", "抽雄期", "吐丝期", "灌浆期", "成熟期"],
    "小麦": ["播种期", "出苗期", "分蘖期", "越冬期", "返青期", "拔节期", "抽穗期", "开花期", "灌浆期", "成熟期"],
    "水稻": ["播种期", "秧苗期", "分蘖期", "拔节期", "孕穗期", "抽穗期", "开花期", "灌浆期", "成熟期"],
    "大豆": ["播种期", "出苗期", "分枝期", "开花期", "结荚期", "鼓粒期", "成熟期"],
}

DISEASE_RISK_THRESHOLDS = {
    "霜霉病": {"温度范围": (15, 25), "湿度下限": 85, "降水天数": 3},
    "白粉病": {"温度范围": (20, 28), "湿度范围": (60, 80)},
    "蚜虫": {"温度范围": (20, 28), "湿度上限": 70},
    "红蜘蛛": {"温度范围": (25, 35), "湿度上限": 60},
}

DISASTER_THRESHOLDS = {
    "霜冻": {"温度阈值": 0, "预警等级": {"轻": 2, "中": 0, "重": -2}},
    "暴雨": {"降水阈值": 50, "预警等级": {"轻": 50, "中": 100, "重": 150}},
    "高温热害": {"温度阈值": 35, "持续天数": 3},
    "干热风": {"温度阈值": 30, "湿度上限": 30, "风速下限": 3},
    "大风": {"风速阈值": 8, "预警等级": {"轻": 8, "中": 12, "重": 17}},
}

AGRICULTURAL_REGIONS = {
    "东北春播区": {"无霜期范围": (120, 150), "积温范围": (2500, 3200), "主要作物": ["玉米", "大豆", "水稻"]},
    "黄淮海两熟区": {"无霜期范围": (180, 220), "积温范围": (4000, 5000), "主要作物": ["小麦", "玉米"]},
    "南方稻区": {"无霜期范围": (280, 365), "积温范围": (5500, 7000), "主要作物": ["水稻"]},
    "西北旱作区": {"无霜期范围": (140, 180), "积温范围": (3000, 4000), "主要作物": ["小麦", "玉米", "马铃薯"]},
}

USER_TYPES = {
    "普通农户": {"输出风格": "通俗化", "详细程度": "中等", "关注点": ["操作指导", "风险提示"]},
    "种植大户": {"输出风格": "专业化", "详细程度": "详细", "关注点": ["生产方案", "成本管控", "风险管控"]},
    "农技人员": {"输出风格": "专业化", "详细程度": "详细", "关注点": ["数据依据", "模型依据", "技术参数"]},
}

settings = Settings()


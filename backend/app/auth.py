# -*- coding: utf-8 -*-
"""魔搭（ModelScope）OIDC 账户授权核心：session cookie + 用户会话管理。

借鉴 ZhihuPath 项目的魔搭授权模式：
- 用 authlib 注册 modelscope OIDC（server_metadata_url 自动发现端点，scope=openid profile）
- 用户写入 users 表；会话用随机 UUID 写入 sessions 表 + HttpOnly Cookie（30 天）
- 因魔搭创空间跨站重定向会让浏览器拒绝 cookie，回调用「一次性 exchange token + 同源 fetch 种 cookie」绕开
"""
import hashlib
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import Request, Response

# 确保能 import config / backend（与 deps.py 一致：把 modelscope_space 根目录加入 sys.path）
_BACKEND_DIR = Path(__file__).resolve().parent
_MODELSCOPE_ROOT = _BACKEND_DIR.parent.parent
if str(_MODELSCOPE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODELSCOPE_ROOT))

from config.settings import settings, DATA_ROOT

COOKIE_NAME = "agri_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 天

AUTH_DB_PATH = DATA_ROOT / "auth.db"


def cookie_secure() -> bool:
    """Studio 一律走 HTTPS，cookie 必须带 Secure；本地 http 调试时保持可关闭。"""
    return settings.COOKIE_SECURE or bool(settings.STUDIO_HOST)


def _init_auth_db() -> None:
    """建表：users / sessions / exchange_tokens（一次性交换令牌）。"""
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                provider TEXT NOT NULL,
                ext_id TEXT,
                avatar TEXT,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS exchange_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _conn() -> sqlite3.Connection:
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------- OIDC 注册 ----------
oauth = OAuth()

if settings.OAUTH_CLIENT_ID and settings.OAUTH_CLIENT_SECRET:
    _provider = settings.OPENID_PROVIDER_URL.rstrip("/")
    oauth.register(
        name="modelscope",
        client_id=settings.OAUTH_CLIENT_ID,
        client_secret=settings.OAUTH_CLIENT_SECRET,
        server_metadata_url=f"{_provider}/.well-known/openid-configuration",
        client_kwargs={"scope": settings.OAUTH_SCOPES},
    )


def session_secret_key() -> str:
    """SessionMiddleware 签名密钥：优先用 OAuth 密钥哈希，否则用开发默认串。"""
    if settings.OAUTH_CLIENT_SECRET:
        return hashlib.sha256(settings.OAUTH_CLIENT_SECRET.encode()).hexdigest()
    return "dev-only-secret-key-change-in-production"


def get_session_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    conn = _conn()
    try:
        row = conn.execute(
            """SELECT u.id, u.nickname, u.provider, u.avatar FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.created_at >= ?""",
            (token, now_ms() - 30 * 24 * 3600 * 1000),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "nickname": row["nickname"],
        "avatar": row["avatar"],
        "provider": row["provider"],
    }


def create_session_for_user(response: Response, user_id: str) -> str:
    token = str(uuid.uuid4())
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)",
            (token, user_id, now_ms()),
        )
        conn.commit()
    finally:
        conn.close()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )
    return token


def _upsert_user(provider: str, ext_id: str, nickname: str, avatar: str | None = None) -> str:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE provider=? AND ext_id=?", (provider, ext_id)
        ).fetchone()
        if row is None:
            user_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO users(id, nickname, provider, ext_id, avatar, created_at) VALUES (?,?,?,?,?,?)",
                (user_id, nickname, provider, ext_id, avatar, now_ms()),
            )
            conn.commit()
            return user_id
        return row["id"]
    finally:
        conn.close()


def upsert_modelscope_user(ext_id: str, nickname: str, avatar: str | None = None) -> str:
    return _upsert_user("modelscope", ext_id, nickname, avatar)


def upsert_dev_user(nickname: str) -> str:
    return _upsert_user("dev", nickname, nickname)


def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        conn = _conn()
        try:
            conn.execute("DELETE FROM sessions WHERE token=?", (token,))
            conn.commit()
        finally:
            conn.close()
    response.delete_cookie(COOKIE_NAME, path="/")


def create_exchange_token(user_id: str) -> str:
    """生成一次性交换令牌（用于跨站重定向后同源设置 cookie）。"""
    token = str(uuid.uuid4())
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO exchange_tokens(token, user_id, created_at) VALUES (?,?,?)",
            (token, user_id, now_ms()),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def consume_exchange_token(token: str) -> str | None:
    """消费交换令牌，返回 user_id（60 秒有效期）。"""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM exchange_tokens WHERE token = ? AND created_at >= ?",
            (token, now_ms() - 60 * 1000),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM exchange_tokens WHERE token = ?", (token,))
        conn.commit()
        return row["user_id"]
    finally:
        conn.close()


def get_current_user(request: Request) -> dict | None:
    """FastAPI 依赖：返回当前登录用户；未登录返回 None。"""
    return get_session_user(request)


# 模块导入时确保表存在
_init_auth_db()

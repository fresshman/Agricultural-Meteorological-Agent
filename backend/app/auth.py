# -*- coding: utf-8 -*-
"""账户体系核心：昵称+密码登录，session cookie + 用户会话管理。

- 默认登录方式是本空间的昵称+密码（provider='local'），账号存在 data/auth.db；
- users / sessions / exchange_tokens 三张表，会话用随机 UUID 写入 + HttpOnly Cookie（30 天）；
- 魔搭 OIDC 那条链路（provider='modelscope'）保留：/api/auth/modelscope → /auth/callback，
  回调用「一次性 exchange token + 同源 fetch 种 cookie」绕开跨站重定向丢 cookie，前端暂不暴露入口。
"""
import hashlib
import hmac
import logging
import os
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

logger = logging.getLogger("agri-backend.auth")

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
        # 老库补列：密码登录是新加的，已有的 users 表没有 password_hash
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        conn.commit()
        # 同一 provider 下 ext_id 唯一，避免并发注册出现同名账号；
        # 老库里若已有重复行会建索引失败，跳过即可（不影响登录）
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_provider_ext "
                "ON users(provider, ext_id) WHERE ext_id IS NOT NULL"
            )
            conn.commit()
        except sqlite3.IntegrityError:
            logger.warning("users 表存在重复的 provider+ext_id，跳过唯一索引创建")
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
        # 昵称/头像以魔搭侧为准，避免改名后界面一直显示旧资料
        conn.execute(
            "UPDATE users SET nickname=?, avatar=? WHERE id=?",
            (nickname, avatar, row["id"]),
        )
        conn.commit()
        return row["id"]
    finally:
        conn.close()


def upsert_modelscope_user(ext_id: str, nickname: str, avatar: str | None = None) -> str:
    return _upsert_user("modelscope", ext_id, nickname, avatar)


# ---------- 昵称 + 密码 ----------
_PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    """pbkdf2-sha256 + 随机盐，不引入额外依赖；格式 pbkdf2_sha256$轮数$盐$摘要。"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(stored: str | None, password: str) -> bool:
    if not stored or not password:
        return False
    try:
        algo, rounds, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_local_user(nickname: str, password: str) -> str | None:
    """注册昵称+密码账号；昵称已被占用时返回 None。"""
    conn = _conn()
    try:
        if conn.execute(
            "SELECT 1 FROM users WHERE provider='local' AND ext_id=?", (nickname,)
        ).fetchone():
            return None
        user_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO users(id, nickname, provider, ext_id, avatar, created_at, password_hash)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, nickname, "local", nickname, None, now_ms(), hash_password(password)),
        )
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate_local(nickname: str, password: str) -> str | None:
    """校验昵称+密码；账号不存在或密码不对统一返回 None。"""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE provider='local' AND ext_id=?",
            (nickname,),
        ).fetchone()
    finally:
        conn.close()
    if row is None or not verify_password(row["password_hash"], password):
        return None
    return row["id"]


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

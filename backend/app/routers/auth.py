# -*- coding: utf-8 -*-
"""账户路由：昵称+密码注册/登录、当前用户、登出；魔搭 OIDC（回调、会话交换）保留备用。"""
import json
import logging
import re

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from ..auth import (
    authenticate_local,
    create_exchange_token,
    create_local_user,
    consume_exchange_token,
    create_session_for_user,
    get_session_user,
    logout,
    oauth,
    upsert_modelscope_user,
)
from config.settings import settings

logger = logging.getLogger("agri-backend.auth")

router = APIRouter(prefix="/api/auth", tags=["账户"])

PASSWORD_MIN_LEN = 6
PASSWORD_MAX_LEN = 64
NICKNAME_MIN_LEN = 2
NICKNAME_MAX_LEN = 20


class CredentialsReq(BaseModel):
    nickname: str = ""
    password: str = ""


# 只放行站内相对路径：杜绝 ?next=//evil.com 的开放重定向，也避免回到 /api、/auth 死循环
_NEXT_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/?=&%#+-]*$")


def _safe_next(raw: str | None) -> str:
    if not raw or not isinstance(raw, str) or len(raw) > 512:
        return "/dashboard"
    if not _NEXT_PATH_RE.match(raw) or raw.startswith("//") or raw.startswith(("/api/", "/auth/")):
        return "/dashboard"
    return raw


@router.get("/me")
def auth_me(request: Request):
    """返回当前登录用户（无则返回 user:null）。"""
    return {"user": get_session_user(request)}


def _check_nickname(raw: str) -> str:
    nickname = (raw or "").strip()
    if not NICKNAME_MIN_LEN <= len(nickname) <= NICKNAME_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"昵称需为 {NICKNAME_MIN_LEN}–{NICKNAME_MAX_LEN} 个字符",
        )
    return nickname


@router.post("/register")
def auth_register(req: CredentialsReq, response: Response):
    """注册并直接登录：昵称即账号，同昵称只能有一个主人。"""
    nickname = _check_nickname(req.nickname)
    password = req.password or ""
    if not PASSWORD_MIN_LEN <= len(password) <= PASSWORD_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"密码需为 {PASSWORD_MIN_LEN}–{PASSWORD_MAX_LEN} 位",
        )
    user_id = create_local_user(nickname, password)
    if not user_id:
        raise HTTPException(status_code=409, detail="该昵称已被注册，换个昵称或直接登录")
    create_session_for_user(response, user_id)
    return {"ok": True, "nickname": nickname}


@router.post("/login")
def auth_login(req: CredentialsReq, response: Response):
    """昵称+密码登录；账号不存在与密码错误返回同一提示，不透露昵称是否已注册。"""
    user_id = authenticate_local((req.nickname or "").strip(), req.password or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="昵称或密码不正确")
    create_session_for_user(response, user_id)
    return {"ok": True}


@router.post("/exchange")
def auth_exchange(payload: dict, request: Request, response: Response):
    """同源交换令牌 → 设置 session cookie（解决跨站重定向 cookie 被拒问题）。"""
    token = (payload or {}).get("token", "")
    user_id = consume_exchange_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="无效或过期的登录令牌")
    create_session_for_user(response, user_id)
    return {"ok": True}


@router.post("/logout")
def auth_logout(request: Request, response: Response):
    logout(request, response)
    return {"ok": True}


@router.get("/modelscope")
async def auth_modelscope_start(
    request: Request,
    switch: int = 0,
    next_path: str = Query("", alias="next"),
):
    """发起魔搭 OIDC 授权码流程（严格参照魔搭创空间官方文档）。

    switch=1 时带 prompt=login：魔搭授权页默认复用浏览器里已登录的魔搭账号，
    想换账号必须让它重新走一次登录。next 为授权完成后的落点（只接受站内路径）。
    """
    if not settings.OAUTH_CLIENT_ID or not getattr(oauth, "modelscope", None):
        raise HTTPException(status_code=503, detail="OAuth 未配置，请使用演示登录或配置 OAUTH_CLIENT_ID/SECRET")
    if settings.STUDIO_HOST:
        redirect_uri = f"https://{settings.STUDIO_HOST}/auth/callback"
    else:
        redirect_uri = f"{str(request.base_url).rstrip('/')}/auth/callback"
    request.session["auth_next"] = _safe_next(next_path)
    extra = {"prompt": "login"} if switch else {}
    return await oauth.modelscope.authorize_redirect(request, redirect_uri, **extra)


async def auth_callback(request: Request):
    """魔搭 OIDC 回调（注册在 /auth/callback，非 /api 前缀）。

    返回 HTML 中间页，用同源 fetch 设置 cookie（避免跨站重定向 cookie 被浏览器拒绝）。
    """
    frontend_home = _safe_next(request.session.pop("auth_next", "/dashboard"))
    # 失败必须回登录页而非 /dashboard：路由守卫会丢掉 err 参数，用户只会看到"又回到登录页"
    failure_url = "/login?err=oauth_failed"
    try:
        token = await oauth.modelscope.authorize_access_token(request)
    except Exception as e:
        logger.warning(f"魔搭授权回调失败: {e}")
        return RedirectResponse(failure_url)

    claims = dict(token.get("userinfo") or {})
    if not claims.get("sub"):
        try:
            claims.update(dict(await oauth.modelscope.userinfo(token=token) or {}))
        except Exception:
            pass

    # sub 是账号唯一标识（按 client 稳定）；缺失时宁可直接失败，
    # 也不能退化成固定值，否则所有用户会落到同一个数据目录
    sub = claims.get("sub")
    if not sub:
        logger.error("魔搭授权回调缺少 sub，无法识别账号")
        return RedirectResponse(failure_url)

    nickname = claims.get("name") or claims.get("preferred_username") or "魔搭用户"
    avatar = claims.get("picture") or claims.get("avatar_url")

    user_id = upsert_modelscope_user(str(sub), nickname, avatar)
    exchange_token = create_exchange_token(user_id)
    js_next = json.dumps(frontend_home)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>登录成功</title>
<style>
body{{font-family:system-ui,-apple-system,'PingFang SC',sans-serif;text-align:center;padding:64px 24px;color:#475569}}
.t{{font-size:15px}}.s{{font-size:12px;color:#94a3b8;margin-top:8px}}
</style></head><body>
<p class="t">登录成功，正在返回…</p>
<p class="s">若窗口没有自动关闭，可手动关闭后回到创空间。</p>
<script>
(function () {{
  var notify = function () {{
    // 创空间页面通常在 iframe 中：用 postMessage + storage 双通道通知原页面刷新登录态
    try {{
      if (window.opener && !window.opener.closed) {{
        window.opener.postMessage({{ type: 'agri:auth', ok: true }}, window.location.origin);
      }}
    }} catch (e) {{}}
    try {{ localStorage.setItem('agri:auth', String(Date.now())); }} catch (e) {{}}
  }};
  fetch('/api/auth/exchange', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ token: '{exchange_token}' }})
  }}).then(function (r) {{ return r.json(); }}).then(function (d) {{
    if (!d || !d.ok) {{ window.location.replace('/login?err=oauth_failed'); return; }}
    // 给前端的一次性通行证：本次整页加载已完成身份核验，不必再过登录闸门
    try {{ sessionStorage.setItem('agri:entry', '1'); }} catch (e) {{}}
    notify();
    try {{ window.close(); }} catch (e) {{}}
    // 非脚本打开的窗口无法 close，退化为在当前窗口进入原页面
    window.setTimeout(function () {{ window.location.replace({js_next}); }}, 400);
  }}).catch(function () {{ window.location.replace('/login?err=oauth_failed'); }});
}})();
</script></body></html>"""
    return HTMLResponse(html)

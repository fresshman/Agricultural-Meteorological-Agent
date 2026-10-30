# -*- coding: utf-8 -*-
"""账户授权路由：魔搭 OIDC 登录、回调、会话交换、当前用户、登出、演示登录。"""
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from ..auth import (
    create_exchange_token,
    consume_exchange_token,
    create_session_for_user,
    get_session_user,
    logout,
    oauth,
    upsert_dev_user,
    upsert_modelscope_user,
)
from config.settings import settings

logger = logging.getLogger("agri-backend.auth")

router = APIRouter(prefix="/api/auth", tags=["账户授权"])


class DevLoginReq(BaseModel):
    nickname: str = ""


@router.get("/me")
def auth_me(request: Request):
    """返回当前登录用户（无则返回 user:null）。前端据此判断是否已登录。"""
    return {"user": get_session_user(request)}


@router.post("/dev")
def auth_dev(req: DevLoginReq, request: Request, response: Response):
    """开发/演示登录兜底：无 OAuth 密钥时也能跑通；DEV_LOGIN_ENABLED=false 时关闭。"""
    if not settings.DEV_LOGIN_ENABLED:
        raise HTTPException(status_code=403, detail="演示登录已关闭，请使用魔搭账号登录")
    name = (req.nickname or "演示用户").strip()[:20]
    user_id = upsert_dev_user(name)
    create_session_for_user(response, user_id)
    return {"ok": True, "nickname": name}


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
async def auth_modelscope_start(request: Request):
    """发起魔搭 OIDC 授权码流程（严格参照魔搭创空间官方文档）。"""
    if not settings.OAUTH_CLIENT_ID or not getattr(oauth, "modelscope", None):
        raise HTTPException(status_code=503, detail="OAuth 未配置，请使用演示登录或配置 OAUTH_CLIENT_ID/SECRET")
    if settings.STUDIO_HOST:
        redirect_uri = f"https://{settings.STUDIO_HOST}/auth/callback"
    else:
        redirect_uri = f"{str(request.base_url).rstrip('/')}/auth/callback"
    return await oauth.modelscope.authorize_redirect(request, redirect_uri)


async def auth_callback(request: Request):
    """魔搭 OIDC 回调（注册在 /auth/callback，非 /api 前缀）。

    返回 HTML 中间页，用同源 fetch 设置 cookie（避免跨站重定向 cookie 被浏览器拒绝）。
    """
    frontend_home = "/dashboard"
    # 失败必须回登录页而非 /dashboard：路由守卫会丢掉 err 参数，用户只会看到"又回到登录页"
    failure_url = "/login?err=oauth_failed"
    try:
        token = await oauth.modelscope.authorize_access_token(request)
    except Exception as e:
        logger.warning(f"魔搭授权回调失败: {e}")
        return RedirectResponse(failure_url)

    userinfo = token.get("userinfo")
    if userinfo is None:
        try:
            userinfo = await oauth.modelscope.userinfo(token=token)
        except Exception:
            userinfo = None
    if not userinfo:
        return RedirectResponse(failure_url)

    ext_id = str(userinfo.get("sub") or "unknown")
    nickname = userinfo.get("name") or userinfo.get("preferred_username") or "魔搭用户"
    avatar = userinfo.get("picture") or userinfo.get("avatar_url")

    user_id = upsert_modelscope_user(ext_id, nickname, avatar)
    exchange_token = create_exchange_token(user_id)

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
    notify();
    try {{ window.close(); }} catch (e) {{}}
    // 非脚本打开的窗口无法 close，退化为在当前窗口进入工作台
    window.setTimeout(function () {{ window.location.replace('{frontend_home}'); }}, 400);
  }}).catch(function () {{ window.location.replace('/login?err=oauth_failed'); }});
}})();
</script></body></html>"""
    return HTMLResponse(html)

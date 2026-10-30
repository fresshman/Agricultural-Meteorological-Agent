import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

/**
 * 账户状态：当前登录用户 + 登录策略 + 本次页面加载是否已核验身份。
 * 后端用 HttpOnly Cookie（agri_session）识别身份，前端只保存用户展示信息。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  /** 是否已向后端确认过登录态（避免每次路由跳转都打 /auth/me） */
  const checked = ref(false)
  /** 后端要求每次打开都核验魔搭身份（浏览器里可能残留上一个账号的会话） */
  const verifyRequired = ref(false)
  /** 演示登录开关（创空间默认关闭，避免多人共用一个演示账号） */
  const devEnabled = ref(false)
  /** 本次页面加载是否已完成身份核验；页面刷新即失效，故不放持久化存储 */
  const verified = ref(false)

  /** 拉取当前登录用户与登录策略；失败/未登录则 user=null */
  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res?.user || null
      verifyRequired.value = Boolean(res?.verify_required)
      devEnabled.value = Boolean(res?.dev_enabled)
    } catch (err) {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  function markVerified() {
    verified.value = true
  }

  /** 演示登录：昵称即可（无 OAuth 环境） */
  async function devLogin(nickname) {
    await authApi.devLogin(nickname)
    await fetchMe()
  }

  /** 退出登录并清空本地会话缓存 */
  async function logout() {
    try {
      await authApi.logout()
    } catch (err) {
      /* 即使请求失败也强制清本地态 */
    }
    user.value = null
    checked.value = false
    verified.value = false
  }

  return { user, checked, verifyRequired, devEnabled, verified, fetchMe, markVerified, devLogin, logout }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

/**
 * 账户状态：当前登录用户 + 是否已校验过。
 * 后端用 HttpOnly Cookie（agri_session）识别身份，前端只保存用户展示信息。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  /** 是否已向后端确认过登录态（避免每次路由跳转都打 /auth/me） */
  const checked = ref(false)

  /** 拉取当前登录用户；失败/未登录则 user=null */
  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res?.user || null
    } catch (err) {
      user.value = null
    } finally {
      checked.value = true
    }
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
  }

  return { user, checked, fetchMe, devLogin, logout }
})

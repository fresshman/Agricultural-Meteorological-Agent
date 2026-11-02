import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'
import { setUserScope } from '@/utils/storage'

/**
 * 账户状态：昵称+密码登录，后端用 HttpOnly Cookie（agri_session）识别身份，
 * 前端只保存用户展示信息。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  /** 是否已向后端确认过登录态（避免每次路由跳转都打 /auth/me） */
  const checked = ref(false)
  /** 进行中的 /auth/me：路由守卫与 App 挂载可能同时要身份，合并成一次请求 */
  let pending = null

  /** 拉取当前登录用户；失败/未登录则 user=null */
  function fetchMe() {
    if (pending) return pending
    pending = (async () => {
      try {
        const res = await authApi.me()
        user.value = res?.user || null
      } catch (err) {
        user.value = null
      } finally {
        checked.value = true
        // 必须在任何 store 读本地数据之前把账号分桶切过去（守卫/App 都会等这一步）
        setUserScope(user.value?.id || null)
        pending = null
      }
    })()
    return pending
  }

  /** 登录成功后重新拉一次用户，保证 user 与 Cookie 指向同一个账号 */
  async function login(nickname, password) {
    await authApi.login(nickname, password)
    await fetchMe()
  }

  /** 注册并登录 */
  async function register(nickname, password) {
    await authApi.register(nickname, password)
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
    setUserScope(null)
  }

  return { user, checked, fetchMe, login, register, logout }
})

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 掉 @/api，只提供 auth store 用到的 authApi（不发真实请求）
vi.mock('@/api', () => ({
  authApi: {
    me: vi.fn(),
    devLogin: vi.fn(),
    logout: vi.fn()
  }
}))

import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

describe('auth store（登录态管理）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchMe 已登录：写入 user 并标记 checked', async () => {
    authApi.me.mockResolvedValue({ user: { id: 'u1', nickname: '张三' } })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toEqual({ id: 'u1', nickname: '张三' })
    expect(auth.checked).toBe(true)
  })

  it('fetchMe 未登录：user 置空但仍标记 checked', async () => {
    authApi.me.mockResolvedValue({ user: null })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(true)
  })

  it('fetchMe 请求失败：容错为未登录', async () => {
    authApi.me.mockRejectedValue(new Error('network'))
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(true)
  })

  it('devLogin：先登录再拉取当前用户', async () => {
    authApi.devLogin.mockResolvedValue({})
    authApi.me.mockResolvedValue({ user: { id: 'u2', nickname: '李四' } })
    const auth = useAuthStore()
    await auth.devLogin('李四')
    expect(authApi.devLogin).toHaveBeenCalledWith('李四')
    expect(auth.user?.id).toBe('u2')
  })

  it('logout：即使请求失败也清空本地态', async () => {
    authApi.logout.mockRejectedValue(new Error('network'))
    authApi.me.mockResolvedValue({ user: { id: 'u3', nickname: '王五' } })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).not.toBeNull()
    await auth.logout()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(false)
  })
})

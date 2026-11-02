import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 掉 @/api，只提供 auth store 用到的 authApi（不发真实请求）
vi.mock('@/api', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn()
  }
}))

import { authApi } from '@/api'
import { getUserScope } from '@/utils/storage'
import { useAuthStore } from '@/stores/auth'

describe('auth store（登录态管理）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('fetchMe 已登录：写入 user、标记 checked，并把本地存储切到该账号分桶', async () => {
    authApi.me.mockResolvedValue({ user: { id: 'u1', nickname: '张三' } })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toEqual({ id: 'u1', nickname: '张三' })
    expect(auth.checked).toBe(true)
    expect(getUserScope()).toBe('u1')
  })

  it('fetchMe 未登录：user 置空但仍标记 checked', async () => {
    authApi.me.mockResolvedValue({ user: null })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(true)
    expect(getUserScope()).toBeNull()
  })

  it('fetchMe 并发调用只打一次 /auth/me（守卫与 App 挂载共享结果）', async () => {
    authApi.me.mockResolvedValue({ user: { id: 'u1' } })
    const auth = useAuthStore()
    await Promise.all([auth.fetchMe(), auth.fetchMe()])
    expect(authApi.me).toHaveBeenCalledTimes(1)
  })

  it('fetchMe 请求失败：容错为未登录', async () => {
    authApi.me.mockRejectedValue(new Error('network'))
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(true)
  })

  it('login：先登录再拉取当前用户', async () => {
    authApi.login.mockResolvedValue({ ok: true })
    authApi.me.mockResolvedValue({ user: { id: 'u2', nickname: '李四' } })
    const auth = useAuthStore()
    await auth.login('李四', 'secret123')
    expect(authApi.login).toHaveBeenCalledWith('李四', 'secret123')
    expect(auth.user?.id).toBe('u2')
  })

  it('register：注册成功后同样拉取当前用户', async () => {
    authApi.register.mockResolvedValue({ ok: true })
    authApi.me.mockResolvedValue({ user: { id: 'u4', nickname: '赵六' } })
    const auth = useAuthStore()
    await auth.register('赵六', 'secret123')
    expect(authApi.register).toHaveBeenCalledWith('赵六', 'secret123')
    expect(auth.user?.nickname).toBe('赵六')
  })

  it('login 失败：不写入 user，错误向上抛给登录页展示', async () => {
    authApi.login.mockRejectedValue({ message: '昵称或密码不正确' })
    const auth = useAuthStore()
    await expect(auth.login('张三', 'bad')).rejects.toMatchObject({ message: '昵称或密码不正确' })
    expect(auth.user).toBeNull()
  })

  it('logout：即使请求失败也清空本地态并退出账号分桶', async () => {
    authApi.logout.mockRejectedValue(new Error('network'))
    authApi.me.mockResolvedValue({ user: { id: 'u3', nickname: '王五' } })
    const auth = useAuthStore()
    await auth.fetchMe()
    expect(auth.user).not.toBeNull()
    await auth.logout()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(false)
    expect(getUserScope()).toBeNull()
  })
})

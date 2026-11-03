import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// stub 掉懒加载视图，避免把 echarts / element-plus 拖进测试进程
// （vi.mock 工厂会被提升，故不能引用外部变量，逐字内联）
vi.mock('@/views/DashboardView.vue', () => ({ default: { name: 'DashboardView', render: () => null } }))
vi.mock('@/views/ChatView.vue', () => ({ default: { name: 'ChatView', render: () => null } }))
vi.mock('@/views/FarmView.vue', () => ({ default: { name: 'FarmView', render: () => null } }))
vi.mock('@/views/WarningView.vue', () => ({ default: { name: 'WarningView', render: () => null } }))
vi.mock('@/views/CalendarView.vue', () => ({ default: { name: 'CalendarView', render: () => null } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { name: 'LoginView', render: () => null } }))
vi.mock('@/views/NotFoundView.vue', () => ({ default: { name: 'NotFoundView', render: () => null } }))

import router from '@/router'
import { flags } from '@/config/flags'
import { useAuthStore } from '@/stores/auth'

function setAuth({ checked = true, user = null }) {
  const auth = useAuthStore()
  auth.checked = checked
  auth.user = user
}

describe('router 守卫 · 开启登录（flags.LOGIN_REQUIRED=true）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    flags.LOGIN_REQUIRED = true
  })

  afterEach(() => {
    flags.LOGIN_REQUIRED = false
  })

  it('未登录访问受保护页 → 重定向到 /login 并带上 redirect', async () => {
    setAuth({ user: null })
    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/dashboard')
  })

  it('已登录访问受保护页 → 正常放行', async () => {
    setAuth({ user: { id: 'u1', nickname: '张三' } })
    await router.push('/chat')
    expect(router.currentRoute.value.name).toBe('chat')
  })

  it('/login 为公开页，未登录也可访问', async () => {
    setAuth({ user: null })
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

describe('router 守卫 · 免登录演示形态（仓库默认）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    expect(flags.LOGIN_REQUIRED).toBe(false)
  })

  it('未登录也能直接进任意受保护页', async () => {
    setAuth({ user: null })
    await router.push('/farm')
    expect(router.currentRoute.value.name).toBe('farm')
  })

  it('不核验身份：不调 fetchMe（auth.checked 保持 false）', async () => {
    const auth = useAuthStore()
    setAuth({ checked: false, user: null })
    await router.push('/warning')
    expect(router.currentRoute.value.name).toBe('warning')
    expect(auth.checked).toBe(false)
  })

  it('登录页不再可达：/login 被送回 /dashboard', async () => {
    setAuth({ checked: false, user: null })
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })
})

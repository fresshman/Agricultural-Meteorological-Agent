import { describe, it, expect, beforeEach, vi } from 'vitest'
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
import { useAuthStore } from '@/stores/auth'

function setAuth({ checked = true, user = null }) {
  const auth = useAuthStore()
  auth.checked = checked
  auth.user = user
}

describe('router 登录守卫', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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

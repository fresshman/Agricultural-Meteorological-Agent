import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 掉 @/api：chat store 走非流式 send 路径，断言其收到的 payload
vi.mock('@/api', () => ({
  chatApi: {
    send: vi.fn(),
    stream: vi.fn(),
    submitFeedback: vi.fn(),
    feedbackStats: vi.fn()
  },
  authApi: { me: vi.fn(), devLogin: vi.fn(), logout: vi.fn() },
  locationApi: { coordinates: vi.fn(), provinces: vi.fn(), cities: vi.fn(), districts: vi.fn() }
}))

import { chatApi } from '@/api'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'

describe('chat store · 提问 payload 的用户归属（每用户数据隔离的关键）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('已登录：payload.user_id = 登录用户 id（后端据此落各自独立子库）', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'ms_user_123', nickname: '张三' }
    const chat = useChatStore()
    chat.streamEnabled = false // 走非流式 send，断言最直接
    chatApi.send.mockResolvedValue({ content: '好的', session_id: 'sess_back' })

    await chat.ask('玉米什么时候播种？')

    expect(chatApi.send).toHaveBeenCalledTimes(1)
    const payload = chatApi.send.mock.calls[0][0]
    expect(payload.user_id).toBe('ms_user_123')
    expect(payload.query).toBe('玉米什么时候播种？')
  })

  it('未登录：payload.user_id 回退为 local_user', async () => {
    const auth = useAuthStore()
    auth.user = null
    const chat = useChatStore()
    chat.streamEnabled = false
    chatApi.send.mockResolvedValue({ content: 'ok' })

    await chat.ask('测试一下')

    const payload = chatApi.send.mock.calls[0][0]
    expect(payload.user_id).toBe('local_user')
  })
})

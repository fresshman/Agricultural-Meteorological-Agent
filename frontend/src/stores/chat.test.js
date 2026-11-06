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
  authApi: { me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() },
  locationApi: { coordinates: vi.fn(), provinces: vi.fn(), cities: vi.fn(), districts: vi.fn() }
}))

import { chatApi } from '@/api'
import { useChatStore } from '@/stores/chat'

describe('chat store · 提问 payload 不再携带身份（身份只认服务端会话）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('payload 不含 user_id，避免请求体覆盖登录身份', async () => {
    const chat = useChatStore()
    chat.streamEnabled = false // 走非流式 send，断言最直接
    chatApi.send.mockResolvedValue({ content: '好的', session_id: 'sess_back' })

    await chat.ask('玉米什么时候播种？')

    expect(chatApi.send).toHaveBeenCalledTimes(1)
    const payload = chatApi.send.mock.calls[0][0]
    expect(payload).not.toHaveProperty('user_id')
    expect(payload.query).toBe('玉米什么时候播种？')
  })

  it('流式路径同样不携带 user_id', async () => {
    const chat = useChatStore()
    chat.streamEnabled = true
    chatApi.stream.mockImplementation(async (_payload, handlers) => {
      handlers.onEvent({ type: 'token', content: 'ok' })
      handlers.onEvent({ type: 'done', meta: { session_id: 's1' } })
      return { ok: true }
    })

    await chat.ask('测试一下')

    const payload = chatApi.stream.mock.calls[0][0]
    expect(payload).not.toHaveProperty('user_id')
  })
})

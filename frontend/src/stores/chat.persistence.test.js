import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 掉 @/api：ask 走非流式 send，不发真实请求
vi.mock('@/api', () => ({
  chatApi: { send: vi.fn(), stream: vi.fn(), submitFeedback: vi.fn(), feedbackStats: vi.fn() },
  authApi: { me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() },
  locationApi: { coordinates: vi.fn(), provinces: vi.fn(), cities: vi.fn(), districts: vi.fn() }
}))

import { flags as repoFlags } from '@/config/flags'

// 仓库默认形态在任何 resetModules 之前抓下来，用于校验「发布出去的就是免持久化」
const REPO_DEFAULTS = { ...repoFlags }

// chat.js 的 _hydrated 是模块级单例，同文件内多次 hydrate 只有第一次生效；
// resetModules 后 chat.js 会拿到一份全新的 flags 实例，所以开关必须通过 freshChat 传
async function freshChat({ persistChat = false } = {}) {
  vi.resetModules()
  setActivePinia(createPinia())
  const { flags } = await import('@/config/flags')
  flags.PERSIST_CHAT = persistChat
  const [chatModule, apiModule] = await Promise.all([import('@/stores/chat'), import('@/api')])
  return { chat: chatModule.useChatStore(), chatApi: apiModule.chatApi }
}

function sessionKeys() {
  return Object.keys(window.localStorage).filter((k) => k.startsWith('agri:sessions'))
}

describe('chat store · 对话持久化开关', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('仓库默认：免登录 + 对话不落盘', () => {
    expect(REPO_DEFAULTS).toMatchObject({ LOGIN_REQUIRED: false, PERSIST_CHAT: false })
  })

  it('默认形态：新建会话与发送都不碰 localStorage，会话仅活在内存里', async () => {
    const { chat, chatApi } = await freshChat()
    chatApi.send.mockResolvedValue({ content: '播种期在 4 月下旬' })
    chat.streamEnabled = false

    chat.newSession()
    await chat.ask('玉米什么时候播种？')

    expect(chat.sessions.length).toBe(1)
    expect(chat.currentSession.messages.length).toBe(2)
    expect(sessionKeys()).toEqual([])
  })

  it('默认形态：浏览器里残留的旧会话桶不会被读回来', async () => {
    window.localStorage.setItem(
      'agri:sessions',
      JSON.stringify({ v: 1, list: [{ id: 's_old', title: '旧对话', messages: [{ role: 'user', content: '旧问题' }] }], currentId: 's_old' })
    )
    const { chat } = await freshChat()
    chat.hydrate()
    expect(chat.sessions).toEqual([])
    expect(chat.currentSessionId).toBeNull()
  })

  it('默认形态：偏好（用户类型/作物）照常记忆', async () => {
    const { chat } = await freshChat()
    chat.setContext('育种专家', '水稻')
    const prefs = JSON.parse(window.localStorage.getItem('agri:prefs'))
    expect(prefs.cropType).toBe('水稻')
    expect(prefs.userType).toBe('育种专家')
    expect(sessionKeys()).toEqual([])
  })

  it('开关打开后：会话写盘并能在新 store 里恢复（代码没删，翻开关即回来）', async () => {
    const { chat } = await freshChat({ persistChat: true })
    const session = chat.newSession()
    expect(sessionKeys()).toContain('agri:sessions')
    expect(window.localStorage.getItem('agri:sessions')).toContain(session.id)

    const restored = await freshChat({ persistChat: true })
    restored.chat.hydrate()
    expect(restored.chat.sessions.map((s) => s.id)).toContain(session.id)
  })
})

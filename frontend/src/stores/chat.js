import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { chatApi } from '@/api'
import { flags } from '@/config/flags'
import { useLocationStore } from './location'
import { KEYS, readJSON, writeJSON } from '@/utils/storage'
import { makeId } from '@/utils/format'

/** 单会话消息上限，超出后淘汰最旧的消息（会话本身保留） */
export const MAX_MESSAGES = 60
/** 持久化总量软上限，超出后淘汰最旧会话 */
const MAX_STORAGE_BYTES = 4 * 1024 * 1024

function makeBackendId() {
  return `s_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`
}

/** 防止 hydrate 被多次调用导致会话被重置 */
let _hydrated = false

/**
 * @typedef {'accepted'|'rejected'|'partial'} FeedbackRating
 */

function createMessage(role, content, extra = {}) {
  return {
    id: makeId('m'),
    role,
    content: content || '',
    ts: Date.now(),
    meta: null,
    status: role === 'user' ? 'done' : 'streaming',
    errorMsg: '',
    progress: '',
    latencyMs: 0,
    feedback: null,
    ...extra
  }
}

function createSession(title = '新会话', backendSessionId = null) {
  const now = Date.now()
  return {
    id: makeId('s'),
    title,
    createdAt: now,
    updatedAt: now,
    backendSessionId: backendSessionId || makeBackendId(),
    messages: []
  }
}

export const useChatStore = defineStore('chat', () => {
  /** @type {import('vue').Ref<Array>} 全部会话（updatedAt 倒序） */
  const sessions = ref([])
  const currentSessionId = ref(null)
  /** 是否正在流式输出 */
  const streaming = ref(false)
  /** 正在流式的 assistant 消息 id */
  const streamingId = ref(null)
  /** 中止句柄：不参与持久化 */
  const abortController = ref(null)
  /** 上次因 SSE 失败而降级到非流式 */
  const fallbackMode = ref(false)
  /** 是否启用流式（写入 agri:prefs） */
  const streamEnabled = ref(true)
  /** 用户类型（后端必传，影响答案风格），记忆在 agri:prefs */
  const userType = ref('普通农户')
  /** 作物类型，同上 */
  const cropType = ref('玉米')
  const error = ref(null)
  const feedbackStats = ref({
    total: 0,
    accepted: 0,
    rejected: 0,
    partial: 0,
    acceptance_rate: 0
  })

  const currentSession = computed(
    () => sessions.value.find((s) => s.id === currentSessionId.value) || null
  )

  const messages = computed(() => currentSession.value?.messages || [])

  /** 会话总数与消息总数（会话列表头部统计用） */
  const stats = computed(() => ({
    sessions: sessions.value.length,
    messages: sessions.value.reduce((sum, s) => sum + (s.messages?.length || 0), 0)
  }))

  // ---------------------------------------------------------------- 持久化
  /** 粗略估算持久化体积（UTF-16，1 char ≈ 2 bytes） */
  function estimateSize() {
    try {
      return JSON.stringify({ v: 1, list: sessions.value }).length * 2
    } catch (err) {
      return 0
    }
  }

  /** 淘汰最旧会话直到体积达标 */
  function evictUntilFit() {
    let guard = 0
    while (estimateSize() > MAX_STORAGE_BYTES && sessions.value.length > 1 && guard < 20) {
      const sorted = [...sessions.value].sort((a, b) => a.updatedAt - b.updatedAt)
      const dropId = sorted[0]?.id
      if (!dropId) break
      sessions.value = sessions.value.filter((s) => s.id !== dropId)
      if (currentSessionId.value === dropId) currentSessionId.value = sessions.value[0]?.id || null
      guard += 1
    }
  }

  function persist() {
    // 演示形态：对话只活在当前页面进程里，关掉开关就既不读也不写
    if (!flags.PERSIST_CHAT) return true
    evictUntilFit()
    const payload = { v: 1, list: sessions.value, currentId: currentSessionId.value }
    return writeJSON(KEYS.SESSIONS, payload, {
      onQuotaError: () => {
        // 淘汰最旧会话后再试一次
        if (sessions.value.length <= 1) return false
        const sorted = [...sessions.value].sort((a, b) => a.updatedAt - b.updatedAt)
        const dropId = sorted[0]?.id
        sessions.value = sessions.value.filter((s) => s.id !== dropId)
        return true
      }
    })
  }

  function persistPrefs() {
    writeJSON(KEYS.PREFS, {
      v: 1,
      streamEnabled: streamEnabled.value,
      userType: userType.value,
      cropType: cropType.value
    })
  }

  /** 恢复会话与偏好；PERSIST_CHAT 关闭时会话永远从空白开始，只恢复偏好 */
  function hydrate() {
    if (_hydrated) return
    _hydrated = true
    const saved = flags.PERSIST_CHAT ? readJSON(KEYS.SESSIONS, null) : null
    const list = Array.isArray(saved?.list) ? saved.list : []

    if (list.length) {
      sessions.value = list.map((s) => ({
        ...createSession(s.title),
        ...s,
        messages: Array.isArray(s.messages) ? s.messages : []
      }))
      currentSessionId.value = saved.currentId || sessions.value[0]?.id || null
      if (!sessions.value.some((s) => s.id === currentSessionId.value)) {
        currentSessionId.value = sessions.value[0]?.id || null
      }
    }

    const prefs = readJSON(KEYS.PREFS, null)
    if (prefs && typeof prefs === 'object') {
      streamEnabled.value = prefs.streamEnabled !== false
      if (typeof prefs.userType === 'string') userType.value = prefs.userType
      if (typeof prefs.cropType === 'string') cropType.value = prefs.cropType
    }
  }

  // -------------------------------------------------------- 会话管理
  function newSession() {
    const draft = createSession()
    sessions.value = [draft, ...sessions.value]
    currentSessionId.value = draft.id
    fallbackMode.value = false
    error.value = null
    persist()
    // 同上：首次提问时若不取代理，新会话里的消息永远不会实时刷新
    return sessions.value.find((s) => s.id === draft.id) || draft
  }

  function switchSession(id) {
    if (currentSessionId.value === id) return
    currentSessionId.value = id
    currentSession.value.updatedAt = Date.now()
    persist()
  }

  /**
   * @param {string} id
   * @param {string} title
   */
  function renameSession(id, title) {
    const session = sessions.value.find((s) => s.id === id)
    if (!session) return
    session.title = String(title || '').trim().slice(0, 40) || '未命名会话'
    session.updatedAt = Date.now()
    persist()
  }

  /**
   * @param {string} id
   */
  function removeSession(id) {
    sessions.value = sessions.value.filter((s) => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0]?.id || null
    }
    persist()
  }

  function setContext(nextUserType, nextCropType) {
    if (nextUserType) userType.value = nextUserType
    if (nextCropType) cropType.value = nextCropType
    persistPrefs()
  }

  function setStreamEnabled(value) {
    streamEnabled.value = Boolean(value)
    persistPrefs()
  }

  function buildPayload(query, session) {
    const loc = useLocationStore()
    return {
      query,
      user_type: userType.value,
      crop_type: cropType.value,
      latitude: loc.selected.latitude,
      longitude: loc.selected.longitude,
      province: loc.selected.province,
      city: loc.selected.city,
      district: loc.selected.district,
      // 身份由服务端会话决定，前端不再传 user_id
      session_id: session.backendSessionId
    }
  }

  /** 追加消息并裁剪到上限 */
  function pushMessage(session, message) {
    session.messages.push(message)
    if (session.messages.length > MAX_MESSAGES) {
      session.messages.splice(0, session.messages.length - MAX_MESSAGES)
    }
    session.updatedAt = Date.now()
    // 必须返回数组里的响应式代理：原始对象的 mutation 不触发渲染
    return session.messages[session.messages.length - 1]
  }

  /** 会话标题取首条用户问题前 12 字 */
  function ensureTitle(session, query) {
    const isDefault = !session.title || session.title === '新会话'
    if (!isDefault) return
    session.title = String(query || '').trim().slice(0, 12) || '新会话'
  }

  /**
   * 发起一次提问（默认走 SSE 流式，失败自动降级到非流式）。
   * @param {string} query
   * @param {{ userType?: string, cropType?: string }} [ctx]
   * @returns {Promise<boolean>} 是否成功产出答案
   */
  async function ask(query, ctx = {}) {
    const text = String(query || '').trim()
    if (!text) return false
    if (streaming.value) return false

    setContext(ctx.userType, ctx.cropType)

    let session = currentSession.value
    if (!session) session = newSession()

    ensureTitle(session, text)
    pushMessage(session, createMessage('user', text))

    const answer = pushMessage(session, createMessage('assistant', '', { questionText: text }))
    return runAnswer(session, answer, text)
  }

  /** 失败后原地重试：复用出错的回答气泡，不再新增用户消息 */
  function retry(answerId) {
    const session = currentSession.value
    if (!session || streaming.value) return Promise.resolve(false)
    const answer = session.messages.find((m) => m.id === answerId && m.role === 'assistant')
    const text = String(answer?.questionText || '').trim()
    if (!answer || !text) return Promise.resolve(false)
    answer.content = ''
    answer.meta = null
    answer.errorMsg = ''
    answer.status = 'streaming'
    // 点重试即「再试一次流式」：否则一次降级会把本会话永久钉在非流式上
    fallbackMode.value = false
    return runAnswer(session, answer, text)
  }

  /** 流式被看门狗掐掉时的分档说明 */
  function timeoutMessage(kind) {
    if (kind === 'first-frame') return '后端 45 秒内没有任何响应，可能是模型正在冷启动'
    if (kind === 'total') return '本次回答超过 3 分钟仍未结束，已中止'
    return '回答中断：60 秒没有新内容'
  }

  /** 跑一次流式问答并落状态；ask 与 retry 共用同一条 assistant 消息 */
  async function runAnswer(session, answer, text) {
    answer.progress = ''
    streamingId.value = answer.id
    streaming.value = true
    error.value = null

    const startedAt = Date.now()
    const controller = new AbortController()
    abortController.value = controller

    let gotDone = false
    let gotAnyToken = false

    const finalize = (status, latencyMs = 0) => {
      answer.status = status
      answer.progress = ''
      if (latencyMs) answer.latencyMs = latencyMs
      streaming.value = false
      streamingId.value = null
      abortController.value = null
      persist()
    }

    try {
      if (streamEnabled.value && !fallbackMode.value) {
        const result = await chatApi.stream(buildPayload(text, session), {
          signal: controller.signal,
          onEvent: (evt) => {
            if (!evt?.type) return
            if (evt.type === 'token') {
              gotAnyToken = true
              answer.content += evt.content || ''
            } else if (evt.type === 'status') {
              answer.progress = evt.content || ''
            } else if (evt.type === 'nowcast') {
              answer.meta = { ...(answer.meta || {}), nowcast_alert: evt.content || '' }
            } else if (evt.type === 'done') {
              gotDone = true
              // done.meta.content 后端刻意置空，必须用前端累积的文本回填
              answer.meta = { ...(evt.meta || {}), ...(answer.meta || {}), content: answer.content }
              if (evt.meta?.session_id) session.backendSessionId = evt.meta.session_id
            } else if (evt.type === 'error') {
              error.value = evt.message || '流式回答失败'
            }
          }
        })

        if (result.timeoutKind) {
          answer.errorMsg = timeoutMessage(result.timeoutKind)
          finalize('error', Date.now() - startedAt)
          error.value = answer.errorMsg
          return false
        }

        if (result.status === 503) {
          answer.errorMsg = '智能体正在加载（首次启动约需 1 分钟），稍后点重试'
          finalize('error', Date.now() - startedAt)
          error.value = answer.errorMsg
          return false
        }

        if (result.aborted) {
          finalize(answer.content ? 'aborted' : 'error', Date.now() - startedAt)
          if (!answer.content) answer.errorMsg = '已停止生成'
          persist()
          return false
        }

        if (gotDone || (result.ok && gotAnyToken)) {
          finalize('done', Date.now() - startedAt)
          return true
        }

        // 流式连接异常：降级到非流式
        fallbackMode.value = true
      }
      return await askFallback(session, answer, text, finalize, startedAt)
    } catch (err) {
      answer.errorMsg = err?.message || '请求失败'
      finalize('error', Date.now() - startedAt)
      error.value = answer.errorMsg
      return false
    }
  }

  /** 降级路径：POST /api/chat 一次性拿完整答案 */
  async function askFallback(session, answer, text, finalize, startedAt) {
    try {
      const res = await chatApi.send(buildPayload(text, session))
      const content = res?.content ?? ''
      answer.content = content
      answer.meta = {
        ...(res || {}),
        ...(answer.meta || {}),
        content
      }
      if (res?.session_id) session.backendSessionId = res.session_id
      finalize('done', Date.now() - startedAt)
      return true
    } catch (err) {
      answer.errorMsg = err?.message || '请求失败'
      finalize('error', Date.now() - startedAt)
      error.value = answer.errorMsg
      return false
    }
  }

  /** 停止生成 */
  function stopStream() {
    if (!streaming.value) return
    abortController.value?.abort()
  }

  /**
   * 重新生成某条答案：删除该答案及其之后的消息，用原问题重问。
   * @param {string} msgId
   */
  async function regenerate(msgId) {
    const session = currentSession.value
    if (!session) return false
    const idx = session.messages.findIndex((m) => m.id === msgId)
    if (idx < 0) return false

    const target = session.messages[idx]
    let query = ''
    for (let i = idx - 1; i >= 0; i -= 1) {
      if (session.messages[i].role === 'user') {
        query = session.messages[i].content
        break
      }
    }
    if (!query) return false

    session.messages.splice(idx, session.messages.length - idx)
    target.content = ''
    streaming.value = false
    streamingId.value = null
    return ask(query)
  }

  /**
   * 提交采纳反馈；失败时回滚按钮态并抛出错误由调用方 Toast。
   * @param {string} msgId
   * @param {FeedbackRating} rating
   * @param {string} [reason]
   */
  async function submitFeedback(msgId, rating, reason = '') {
    const session = currentSession.value
    if (!session) throw new Error('会话不存在')
    const message = session.messages.find((m) => m.id === msgId)
    if (!message) throw new Error('消息不存在')

    const previous = message.feedback
    message.feedback = rating
    persist()

    try {
      await chatApi.submitFeedback({
        message_id: msgId,
        session_id: session.backendSessionId,
        rating,
        reason
      })
      loadFeedbackStats()
      return true
    } catch (err) {
      message.feedback = previous
      persist()
      throw err
    }
  }

  /** 拉取采纳率统计 */
  async function loadFeedbackStats() {
    try {
      const res = await chatApi.feedbackStats()
      feedbackStats.value = {
        total: Number(res?.total) || 0,
        accepted: Number(res?.accepted) || 0,
        rejected: Number(res?.rejected) || 0,
        partial: Number(res?.partial) || 0,
        acceptance_rate: Number(res?.acceptance_rate) || 0
      }
    } catch (err) {
      feedbackStats.value = { total: 0, accepted: 0, rejected: 0, partial: 0, acceptance_rate: 0 }
    }
    return feedbackStats.value
  }

  /** 清空当前会话的消息（保留会话） */
  function clearMessages() {
    const session = currentSession.value
    if (!session) return
    session.messages = []
    persist()
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    streaming,
    streamingId,
    abortController,
    fallbackMode,
    streamEnabled,
    error,
    feedbackStats,
    stats,
    userType,
    cropType,
    hydrate,
    persist,
    newSession,
    switchSession,
    renameSession,
    removeSession,
    setContext,
    setStreamEnabled,
    ask,
    retry,
    stopStream,
    regenerate,
    submitFeedback,
    loadFeedbackStats,
    clearMessages,
    MAX_MESSAGES
  }
})

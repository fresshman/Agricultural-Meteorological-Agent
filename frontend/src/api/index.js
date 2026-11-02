import axios from 'axios'
import { readSSE } from '@/utils/sse'

const http = axios.create({ baseURL: '/api', timeout: 60000, withCredentials: true })

/**
 * 把 axios 错误归一化为统一结构，供 store 决定如何展示。
 * @param {any} err
 * @returns {{ message: string, code: number, isTimeout: boolean, isNetwork: boolean, raw?: any }}
 */
export function normalizeError(err) {
  const isTimeout = err?.code === 'ECONNABORTED' || /timeout/i.test(String(err?.message || ''))
  const isNetwork = !err?.response && Boolean(err?.request)
  let message = '网络异常，请检查连接后重试'

  if (isTimeout) {
    message = '请求超时，请稍后重试'
  } else if (err?.response) {
    const data = err.response.data
    message = data?.message || data?.detail || `请求失败（${err.response.status}）`
  } else if (err?.message) {
    message = err.message
  }

  return {
    message,
    code: Number(err?.response?.status || 0),
    isTimeout,
    isNetwork,
    raw: err
  }
}

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const normalized = normalizeError(err)
    if (import.meta.env?.DEV) console.error('[api]', normalized)
    return Promise.reject(normalized)
  }
)

/** 流式问答的 SSE 地址 */
const STREAM_URL = '/api/chat/stream'

export const chatApi = {
  /** @returns {Promise<any>} 后端 ChatResponse（content / evidence / confidence / ...） */
  send: (data) => http.post('/chat', data),

  /**
   * SSE 流式问答（全站唯一流式出口）。
   *
   * 使用 fetch + ReadableStream 而非 EventSource：需要 POST 且需要可中止。
   * 返回的 Promise **不会因为服务端 error 事件而 reject**，
   * 事件一律通过 onEvent 透传；只有连接层失败才返回 ok:false。
   *
   * @param {Object} payload 同 chatApi.send
   * @param {Object} opts
   * @param {AbortSignal} [opts.signal] 外部 AbortController.signal
   * @param {(evt: { type: string, content?: string, meta?: Object, message?: string }) => void} [opts.onEvent]
   * @returns {Promise<{ ok: boolean, aborted: boolean, reason?: string }>}
   */
  async stream(payload, opts = {}) {
    const { signal, onEvent } = opts
    const controller = new AbortController()
    const onAbort = () => controller.abort()

    if (signal) {
      if (signal.aborted) controller.abort()
      else signal.addEventListener('abort', onAbort, { once: true })
    }

    let reader = null
    try {
      const resp = await fetch(STREAM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(payload),
        signal: controller.signal
      })

      if (!resp.ok) throw new Error(`流式接口返回 ${resp.status}`)
      if (!resp.body) throw new Error('当前浏览器不支持流式读取')

      reader = resp.body.getReader()
      const result = await readSSE(reader, (frame) => {
        if (typeof onEvent === 'function') onEvent(frame)
      }, { signal: controller.signal })

      if (result.aborted) return { ok: false, aborted: true, reason: 'aborted' }
      if (!result.ok) return { ok: false, aborted: false, reason: result.reason || 'stream-error' }
      return { ok: true, aborted: false }
    } catch (err) {
      if (err?.name === 'AbortError' || controller.signal.aborted || signal?.aborted) {
        // 主动中止：不上抛、不 Toast
        return { ok: false, aborted: true, reason: 'aborted' }
      }
      return { ok: false, aborted: false, reason: err?.message || String(err) }
    } finally {
      try {
        if (reader) await reader.cancel()
      } catch (err) {
        /* cancel 失败可忽略 */
      }
      if (signal) signal.removeEventListener('abort', onAbort)
    }
  },

  submitFeedback: (data) => http.post('/chat/feedback', data),
  feedbackStats: () => http.get('/chat/feedback/stats')
}

export const weatherApi = {
  get: (params) => http.get('/weather', { params })
}

export const locationApi = {
  coordinates: (data) => http.post('/location/coordinates', data),
  provinces: () => http.get('/location/provinces'),
  cities: (province) => http.get('/location/cities', { params: { province } }),
  districts: (province, city) => http.get('/location/districts', { params: { province, city } })
}

export const farmApi = {
  listFields: () => http.get('/farm/fields'),
  createField: (data) => http.post('/farm/fields', data),
  getField: (id) => http.get(`/farm/fields/${id}`),
  deleteField: (id) => http.delete(`/farm/fields/${id}`),
  water: (id) => http.post(`/farm/fields/${id}/water`),
  fertilize: (id) => http.post(`/farm/fields/${id}/fertilize`),
  harvest: (id) => http.post(`/farm/fields/${id}/harvest`),
  alerts: (params) => http.get('/farm/alerts', { params })
}

export const warningApi = {
  disaster: (data) => http.post('/warning/disaster', data),
  pest: (data) => http.post('/warning/pest', data),
  suitability: (data) => http.post('/warning/suitability', data)
}

export const healthApi = {
  check: () => http.get('/health')
}

/** 账户相关接口 */
export const authApi = {
  /** 获取当前登录用户；未登录返回 { user: null } */
  me: () => http.get('/auth/me'),
  /** 昵称+密码登录（成功后由后端种 HttpOnly Cookie） */
  login: (nickname, password) => http.post('/auth/login', { nickname, password }),
  /** 注册并登录；昵称重复返回 409 */
  register: (nickname, password) => http.post('/auth/register', { nickname, password }),
  /** 退出登录 */
  logout: () => http.post('/auth/logout')
}

export default http

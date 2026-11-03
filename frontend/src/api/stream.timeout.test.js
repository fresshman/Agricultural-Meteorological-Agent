import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { chatApi, STREAM_TIMEOUTS } from '@/api'

const enc = new TextEncoder()

function abortError() {
  const err = new Error('The user aborted a request.')
  err.name = 'AbortError'
  return err
}

/**
 * 造一个可控的 SSE 响应体：frames 按 intervalMs 间隔投喂；
 * end=true 时喂完就正常关闭（模拟服务端发完 done），
 * 否则一直悬着直到 signal 被 abort（模拟后端卡死 / 心跳停止）。
 */
function makeBody(signal, frames = [], intervalMs = 0, end = false) {
  const queued = []
  const waiting = []
  frames.forEach((text, i) => {
    setTimeout(() => {
      const chunk = { done: false, value: enc.encode(text) }
      if (waiting.length) waiting.shift().resolve(chunk)
      else queued.push(chunk)
      if (end && i === frames.length - 1) {
        const closer = { done: true, value: undefined }
        if (waiting.length) waiting.shift().resolve(closer)
        else queued.push(closer)
      }
    }, intervalMs * (i + 1))
  })
  signal.addEventListener('abort', () => {
    while (waiting.length) waiting.shift().reject(abortError())
  })
  return {
    getReader: () => ({
      read: () => {
        if (queued.length) return Promise.resolve(queued.shift())
        return new Promise((resolve, reject) => waiting.push({ resolve, reject }))
      },
      cancel: () => Promise.resolve()
    })
  }
}

/** 替换全局 fetch */
function stubFetch({ status = 200, frames = [], intervalMs = 0, end = false } = {}) {
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    if (status !== 200) return { ok: false, status, body: null }
    return { ok: true, status: 200, body: makeBody(init.signal, frames, intervalMs, end) }
  }))
}

const frame = (obj) => `data: ${JSON.stringify(obj)}\n\n`

describe('chatApi.stream 看门狗', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('阈值是首帧 45s、静默 60s、总时长 180s', () => {
    expect(STREAM_TIMEOUTS).toEqual({ firstFrameMs: 45000, silenceMs: 60000, totalMs: 180000 })
  })

  it('开流后一帧都没有 → first-frame 超时，且不算用户中止', async () => {
    stubFetch({ frames: [] })
    const pending = chatApi.stream({ query: 'x' })
    await vi.advanceTimersByTimeAsync(STREAM_TIMEOUTS.firstFrameMs + 5)
    const result = await pending
    expect(result.ok).toBe(false)
    expect(result.timeoutKind).toBe('first-frame')
    expect(result.reason).toBe('timeout:first-frame')
    expect(result.aborted).toBe(false)
  })

  it('收到过帧之后再无内容 → idle 超时', async () => {
    stubFetch({ frames: [frame({ type: 'status', content: '准备中' })] })
    const pending = chatApi.stream({ query: 'x' })
    await vi.advanceTimersByTimeAsync(2000)
    await vi.advanceTimersByTimeAsync(STREAM_TIMEOUTS.silenceMs + 5)
    const result = await pending
    expect(result.timeoutKind).toBe('idle')
  })

  it('心跳一直有但答案永不完 → total 硬上限掐断', async () => {
    const status = frame({ type: 'status', content: '仍在准备' })
    stubFetch({ frames: new Array(12).fill(status), intervalMs: 20 })
    const pending = chatApi.stream({ query: 'x' }, { timeouts: { firstFrameMs: 500, silenceMs: 500, totalMs: 100 } })
    await vi.advanceTimersByTimeAsync(160)
    const result = await pending
    expect(result.timeoutKind).toBe('total')
  })

  it('后端 503（智能体加载中）带出 status，供上层提示冷启动', async () => {
    stubFetch({ status: 503 })
    const result = await chatApi.stream({ query: 'x' })
    expect(result.ok).toBe(false)
    expect(result.status).toBe(503)
    expect(result.timeoutKind).toBeUndefined()
  })

  it('用户手动停止不算超时', async () => {
    stubFetch({ frames: [] })
    const controller = new AbortController()
    const pending = chatApi.stream({ query: 'x' }, { signal: controller.signal })
    await vi.advanceTimersByTimeAsync(10)
    controller.abort()
    const result = await pending
    expect(result.aborted).toBe(true)
    expect(result.timeoutKind).toBeUndefined()
  })

  it('正常流：status / token / done 逐帧透传且判成功', async () => {
    stubFetch({ end: true, frames: [
      frame({ type: 'status', content: '正在识别意图…' }),
      frame({ type: 'token', content: '可以' }),
      frame({ type: 'done', meta: { session_id: 's_1' } })
    ] })
    const seen = []
    const pending = chatApi.stream({ query: 'x' }, { onEvent: (e) => seen.push(e) })
    await vi.advanceTimersByTimeAsync(50)
    const result = await pending
    expect(result.ok).toBe(true)
    expect(seen.map((e) => e.type)).toEqual(['status', 'token', 'done'])
  })
})

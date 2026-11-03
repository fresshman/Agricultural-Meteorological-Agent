import { describe, it, expect, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick, watch } from 'vue'

/** 每次都要 resetModules：store 里有 _hydrated 等模块级单例状态 */
async function freshChat() {
  vi.resetModules()
  setActivePinia(createPinia())
  const [chatModule, apiModule] = await Promise.all([import('@/stores/chat'), import('@/api')])
  return { chat: chatModule.useChatStore(), chatApi: apiModule.chatApi }
}

const lastAnswer = (chat) => chat.messages[chat.messages.length - 1]

describe('问答进度与失败重试', () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it('status 事件实时写进 progress，收尾后清空', async () => {
    const { chat, chatApi } = await freshChat()
    let seenProgress = ''
    chatApi.stream = async (payload, opts) => {
      opts.onEvent({ type: 'status', content: '正在识别意图、获取气象、检索知识库…' })
      seenProgress = lastAnswer(chat).progress
      opts.onEvent({ type: 'token', content: '可以打药' })
      opts.onEvent({ type: 'done', meta: { session_id: 's_1' } })
      return { ok: true, aborted: false }
    }

    const ok = await chat.ask('今天能打药吗')
    const answer = lastAnswer(chat)
    expect(ok).toBe(true)
    expect(seenProgress).toBe('正在识别意图、获取气象、检索知识库…')
    expect(answer.content).toBe('可以打药')
    expect(answer.progress).toBe('')
    expect(answer.status).toBe('done')
  })

  it('回答必须逐帧走响应式代理：进度和 token 都能触发渲染', async () => {
    const { chat, chatApi } = await freshChat()
    const frames = []
    const stop = watch(
      () => chat.messages,
      () => {
        const answer = lastAnswer(chat)
        frames.push(`${answer.progress}|${answer.content}`)
      },
      { deep: true }
    )

    chatApi.stream = async (payload, opts) => {
      opts.onEvent({ type: 'status', content: '上下文准备中（已 2 秒）…' })
      await nextTick()
      opts.onEvent({ type: 'token', content: '今天' })
      await nextTick()
      opts.onEvent({ type: 'token', content: '能打药' })
      await nextTick()
      opts.onEvent({ type: 'done', meta: { session_id: 's_1' } })
      return { ok: true, aborted: false }
    }

    const ok = await chat.ask('今天能打药吗')
    stop()
    expect(ok).toBe(true)
    // store 内部若改的是原始对象，这几帧一次都不会触发渲染
    expect(frames).toContain('上下文准备中（已 2 秒）…|')
    expect(frames).toContain('上下文准备中（已 2 秒）…|今天')
    expect(frames).toContain('上下文准备中（已 2 秒）…|今天能打药')
  })

  it('首帧超时：解锁输入框并说明可能是冷启动', async () => {
    const { chat, chatApi } = await freshChat()
    chatApi.stream = async () => ({
      ok: false, aborted: false, reason: 'timeout:first-frame', timeoutKind: 'first-frame'
    })
    const ok = await chat.ask('问个问题')
    expect(ok).toBe(false)
    expect(chat.streaming).toBe(false)
    expect(lastAnswer(chat).status).toBe('error')
    expect(lastAnswer(chat).errorMsg).toContain('冷启动')
  })

  it('回答中断（idle）与总时长超限（total）给不同文案', async () => {
    const { chat, chatApi } = await freshChat()
    chatApi.stream = async () => ({ ok: false, aborted: false, timeoutKind: 'idle' })
    await chat.ask('一')
    expect(lastAnswer(chat).errorMsg).toContain('60 秒没有新内容')

    chatApi.stream = async () => ({ ok: false, aborted: false, timeoutKind: 'total' })
    await chat.ask('二')
    expect(lastAnswer(chat).errorMsg).toContain('3 分钟')
  })

  it('后端 503 时报「智能体正在加载」，不误报成网络故障', async () => {
    const { chat, chatApi } = await freshChat()
    chatApi.stream = async () => ({ ok: false, aborted: false, status: 503, reason: '流式接口返回 503' })
    await chat.ask('问个问题')
    expect(lastAnswer(chat).errorMsg).toContain('正在加载')
  })

  it('重试原地复用气泡：不新增用户消息，也不丢原问题', async () => {
    const { chat, chatApi } = await freshChat()
    let calls = 0
    chatApi.stream = async (payload, opts) => {
      calls += 1
      if (calls === 1) {
        return { ok: false, aborted: false, timeoutKind: 'first-frame', reason: 'timeout:first-frame' }
      }
      opts.onEvent({ type: 'token', content: `第${calls}次回答` })
      opts.onEvent({ type: 'done', meta: {} })
      return { ok: true, aborted: false }
    }

    await chat.ask('今天能打药吗')
    const answer = lastAnswer(chat)
    expect(answer.status).toBe('error')
    expect(answer.questionText).toBe('今天能打药吗')

    const ok = await chat.retry(answer.id)
    expect(ok).toBe(true)
    expect(chat.messages.length).toBe(2)               // 一问一答，没有重复气泡
    expect(chat.messages[0].content).toBe('今天能打药吗')
    expect(lastAnswer(chat).content).toBe('第2次回答')
    expect(lastAnswer(chat).status).toBe('done')
    expect(lastAnswer(chat).errorMsg).toBe('')
  })

  it('降级过一次后，重试仍先试流式而不是被钉死在非流式', async () => {
    const { chat, chatApi } = await freshChat()
    let streamCalls = 0
    chatApi.stream = async (payload, opts) => {
      streamCalls += 1
      if (streamCalls === 1) return { ok: false, aborted: false, reason: '连接被重置' }
      opts.onEvent({ type: 'status', content: '上下文准备中（已 2 秒）…' })
      opts.onEvent({ type: 'token', content: '流式回答' })
      opts.onEvent({ type: 'done', meta: {} })
      return { ok: true, aborted: false }
    }
    chatApi.send = async () => {
      throw { message: '请求失败（500）', code: 500, isTimeout: false, isNetwork: false }
    }

    await chat.ask('今天能打药吗')
    expect(chat.fallbackMode).toBe(true)
    expect(lastAnswer(chat).status).toBe('error')

    const ok = await chat.retry(lastAnswer(chat).id)
    expect(ok).toBe(true)
    expect(streamCalls).toBe(2)
    expect(lastAnswer(chat).content).toBe('流式回答')
    expect(chat.fallbackMode).toBe(false)
  })

  it('重试只对带原问题的失败回答生效，别乱点', async () => {
    const { chat, chatApi } = await freshChat()
    chatApi.stream = async (payload, opts) => {
      opts.onEvent({ type: 'token', content: '正常答案' })
      opts.onEvent({ type: 'done', meta: {} })
      return { ok: true, aborted: false }
    }
    await chat.ask('问个问题')
    const done = lastAnswer(chat)
    expect(await chat.retry('m_不存在')).toBe(false)
    expect(done.status).toBe('done')
  })
})

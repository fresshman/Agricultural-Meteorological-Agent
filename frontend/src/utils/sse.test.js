import { describe, it, expect } from 'vitest'
import { parseSSELine, readSSE } from './sse.js'

const encoder = new TextEncoder()

/** 把若干 chunk（字符串或 Uint8Array）组装成 ReadableStream */
function streamOf(chunks) {
  let i = 0
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(typeof chunks[i] === 'string' ? encoder.encode(chunks[i]) : chunks[i])
        i += 1
      } else {
        controller.close()
      }
    }
  })
}

async function collect(chunks, opts = {}) {
  const reader = streamOf(chunks).getReader()
  const frames = []
  const result = await readSSE(reader, (f) => frames.push(f), opts)
  return { frames, result }
}

describe('utils/sse · parseSSELine 单帧解析', () => {
  it('token 帧', () => {
    expect(parseSSELine('data: {"type":"token","content":"你好"}')).toEqual({ type: 'token', content: '你好' })
  })

  it('done 帧（冒号后无空格也兼容）', () => {
    expect(parseSSELine('data:{"type":"done"}')).toEqual({ type: 'done' })
  })

  it('error 帧带 message', () => {
    expect(parseSSELine('data: {"type":"error","message":"服务异常"}')).toEqual({ type: 'error', message: '服务异常' })
  })

  it('meta 透传', () => {
    expect(parseSSELine('data: {"type":"done","meta":{"session_id":"s1"}}')).toEqual({ type: 'done', meta: { session_id: 's1' } })
  })

  it('type 强制转字符串', () => {
    expect(parseSSELine('data: {"type":123}')).toEqual({ type: '123' })
  })

  it('注释 / 心跳 / event: 行返回 null', () => {
    expect(parseSSELine(': heartbeat')).toBeNull()
    expect(parseSSELine(':ping')).toBeNull()
    expect(parseSSELine('event: message')).toBeNull()
  })

  it('非法 JSON / 非对象 JSON / 空行返回 null', () => {
    expect(parseSSELine('data: not-json')).toBeNull()
    expect(parseSSELine('data: 42')).toBeNull()
    expect(parseSSELine('data: "str"')).toBeNull()
    expect(parseSSELine('data: null')).toBeNull()
    expect(parseSSELine('data:')).toBeNull()
    expect(parseSSELine('')).toBeNull()
    expect(parseSSELine('   ')).toBeNull()
  })

  it('非字符串入参返回 null', () => {
    expect(parseSSELine(123)).toBeNull()
    expect(parseSSELine(null)).toBeNull()
    expect(parseSSELine(undefined)).toBeNull()
  })
})

describe('utils/sse · readSSE 流式读取', () => {
  it('单 chunk 多帧', async () => {
    const { frames, result } = await collect([
      'data: {"type":"token","content":"a"}\ndata: {"type":"token","content":"b"}\ndata: {"type":"done"}\n'
    ])
    expect(frames.map((f) => f.type)).toEqual(['token', 'token', 'done'])
    expect(frames.map((f) => f.content)).toEqual(['a', 'b', undefined])
    expect(result).toEqual({ ok: true, aborted: false })
  })

  it('跨 chunk 半包：一行被拆到多个 chunk 也能正确拼帧', async () => {
    const { frames, result } = await collect([
      'data: {"type":"tok',
      'en","content":"你',
      '好"}\ndata: {"type":"done"}\n'
    ])
    expect(frames).toEqual([{ type: 'token', content: '你好' }, { type: 'done' }])
    expect(result.ok).toBe(true)
  })

  it('\\r\\n 行尾兼容', async () => {
    const { frames } = await collect([
      'data: {"type":"token","content":"x"}\r\ndata: {"type":"done"}\r\n'
    ])
    expect(frames.map((f) => f.type)).toEqual(['token', 'done'])
  })

  it('服务端未以换行结尾：收尾 flush 消费最后一行', async () => {
    const { frames } = await collect([
      'data: {"type":"token","content":"hi"}\ndata: {"type":"done"}'
    ])
    expect(frames.map((f) => f.type)).toEqual(['token', 'done'])
  })

  it('值中间被拆包：半行留在缓冲，拼完整后才出帧', async () => {
    const { frames } = await collect([
      'data: {"type":"token","content":"part',
      'ial"}\ndata: {"type":"done"}\n'
    ])
    expect(frames).toEqual([{ type: 'token', content: 'partial' }, { type: 'done' }])
  })

  it('多字节 UTF-8 字符跨 chunk 拆分（TextDecoder 流式模式不乱码）', async () => {
    const prefix = encoder.encode('data: {"type":"token","content":"')
    const tail = encoder.encode('"}\n')
    const hello = encoder.encode('你好') // 6 字节
    const mid = 2 // 切在「你」的第 3 字节与「好」之间
    const { frames } = await collect([
      new Uint8Array([...prefix, ...hello.slice(0, mid)]),
      new Uint8Array([...hello.slice(mid), ...tail])
    ])
    expect(frames).toEqual([{ type: 'token', content: '你好' }])
  })

  it('非法 JSON 帧被忽略，不中断整条流', async () => {
    const { frames, result } = await collect([
      'data: not-json\ndata: {"type":"token","content":"ok"}\ndata: {"type":"done"}\n'
    ])
    expect(frames.map((f) => f.type)).toEqual(['token', 'done'])
    expect(result.ok).toBe(true)
  })

  it('AbortError 归一化为 { ok:false, aborted:true }，不上抛', async () => {
    const reader = {
      read: () => Promise.reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))
    }
    const result = await readSSE(reader, () => {})
    expect(result).toEqual({ ok: false, aborted: true, reason: 'aborted' })
  })

  it('signal 已中止时同样归一化为 aborted', async () => {
    const reader = { read: () => Promise.reject(new Error('boom')) }
    const result = await readSSE(reader, () => {}, { signal: { aborted: true } })
    expect(result).toEqual({ ok: false, aborted: true, reason: 'aborted' })
  })

  it('其他读取错误：返回 reason，不当作中止', async () => {
    const reader = { read: () => Promise.reject(new Error('network down')) }
    const result = await readSSE(reader, () => {})
    expect(result).toEqual({ ok: false, aborted: false, reason: 'network down' })
  })
})

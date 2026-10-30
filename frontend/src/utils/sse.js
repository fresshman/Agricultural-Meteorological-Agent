/**
 * SSE（Server-Sent Events）流式解析工具 —— 纯解析，不含任何业务逻辑
 * --------------------------------------------------------------------------
 * 之所以不用原生 EventSource：需要 POST 且需要可中止（AbortController）。
 * 关键能力：
 * 1. 跨 chunk 半包：内部维护行缓冲，只消费完整行，未完成的留到下一块；
 * 2. 兼容 \n / \r\n / 行尾裸 \r；
 * 3. JSON 解析异常返回 null 并忽略该帧，不中断整条流；
 * 4. AbortError 归一化返回 { ok:false, aborted:true }，不上抛、不 Toast。
 */

/**
 * 把一行 `data: {...}` 解析成帧对象。
 * @param {string} line 单行文本（可带 `data:` 前缀）
 * @returns {{ type: string, content?: string, meta?: object, message?: string }|null} 非法 JSON 返回 null
 */
export function parseSSELine(line) {
  if (typeof line !== 'string') return null
  let text = line.trim()
  if (!text) return null
  if (text.startsWith(':')) return null // 注释 / 心跳
  if (text.startsWith('data:')) text = text.slice(5).trim()
  else if (text.startsWith('event:')) return null
  if (!text) return null

  let payload = null
  try {
    payload = JSON.parse(text)
  } catch (err) {
    return null
  }
  if (!payload || typeof payload !== 'object') return null

  /** @type {{ type: string, content?: string, meta?: object, message?: string }} */
  const frame = { type: String(payload.type || '') }
  if (payload.content !== undefined) frame.content = payload.content
  if (payload.meta !== undefined) frame.meta = payload.meta
  if (payload.message !== undefined) frame.message = payload.message
  return frame
}

/**
 * 从 ReadableStream reader 中逐块读取并按帧回调。
 * @param {ReadableStreamDefaultReader<Uint8Array>} reader
 * @param {(frame: { type: string, content?: string, meta?: object, message?: string }) => void} onFrame
 * @param {{ signal?: AbortSignal }} [opts]
 * @returns {Promise<{ ok: boolean, aborted: boolean, reason?: string }>}
 */
export async function readSSE(reader, onFrame, opts = {}) {
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  /** 消费一行完整文本 */
  const consume = (line) => {
    const frame = parseSSELine(line)
    if (frame && typeof onFrame === 'function') onFrame(frame)
  }

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let idx = buffer.indexOf('\n')
      while (idx !== -1) {
        let line = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 1)
        if (line.endsWith('\r')) line = line.slice(0, -1)
        consume(line)
        idx = buffer.indexOf('\n')
      }
    }
    // 收尾：flush 解码器 + 处理最后一行（服务端未以换行结尾的情况）
    buffer += decoder.decode()
    if (buffer.trim()) consume(buffer.trim())
    return { ok: true, aborted: false }
  } catch (err) {
    if (err && (err.name === 'AbortError' || opts.signal?.aborted)) {
      return { ok: false, aborted: true, reason: 'aborted' }
    }
    return { ok: false, aborted: false, reason: err?.message || String(err) }
  }
}

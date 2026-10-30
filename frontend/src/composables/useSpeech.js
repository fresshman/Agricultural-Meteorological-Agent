import { computed, onBeforeUnmount, ref } from 'vue'

/**
 * Web Speech API 状态机（P1-06）
 * --------------------------------------------------------------------------
 * 状态：unsupported（浏览器不支持） / idle / listening / error
 * 不支持时按钮置灰并由调用方展示降级提示，绝不静默失败。
 *
 * @param {{ lang?: string, continuous?: boolean, interimResults?: boolean, onResult?: (text: string) => void }} [options]
 */
export function useSpeech(options = {}) {
  const {
    lang = 'zh-CN',
    continuous = false,
    interimResults = true,
    onResult = null
  } = options

  const SpeechRecognition =
    typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null

  /** 浏览器是否支持语音识别（Chrome / 新版 Edge 支持，Safari 部分支持） */
  const supported = computed(() => Boolean(SpeechRecognition))
  /** @type {import('vue').Ref<'unsupported'|'idle'|'listening'|'error'>} */
  const status = ref(supported.value ? 'idle' : 'unsupported')
  /** 最终识别结果 */
  const transcript = ref('')
  /** 中间结果（实时回显） */
  const interim = ref('')
  /** 最近一次错误说明 */
  const errorMsg = ref('')

  const listening = computed(() => status.value === 'listening')

  let recognition = null

  function destroy() {
    if (!recognition) return
    recognition.onresult = null
    recognition.onerror = null
    recognition.onend = null
    try {
      recognition.abort()
    } catch (err) {
      /* 已停止时忽略 */
    }
    recognition = null
  }

  function ensureRecognition() {
    if (!SpeechRecognition) return null
    if (recognition) return recognition

    recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.continuous = continuous
    recognition.interimResults = interimResults

    recognition.onresult = (event) => {
      let finalText = ''
      let interimText = ''
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i]
        const text = result[0]?.transcript || ''
        if (result.isFinal) finalText += text
        else interimText += text
      }
      if (finalText) transcript.value = finalText
      interim.value = interimText
      status.value = 'idle'
      if (finalText && typeof onResult === 'function') onResult(finalText)
    }

    recognition.onerror = (event) => {
      const code = event?.error || 'unknown'
      errorMsg.value =
        code === 'not-allowed'
          ? '麦克风权限被拒绝，请在浏览器设置中允许后重试'
          : code === 'no-speech'
            ? '没有听到声音，请再说一次'
            : code === 'network'
              ? '语音识别服务不可用，请检查网络'
              : '语音识别失败，请改为手动输入'
      status.value = 'error'
    }

    recognition.onend = () => {
      if (status.value === 'listening') status.value = 'idle'
    }

    return recognition
  }

  /** 开始录音 */
  function start() {
    if (!supported.value) {
      errorMsg.value = '当前浏览器不支持语音，请使用 Chrome 或手动输入'
      status.value = 'unsupported'
      return false
    }
    const engine = ensureRecognition()
    if (!engine) return false
    transcript.value = ''
    interim.value = ''
    errorMsg.value = ''
    try {
      engine.start()
      status.value = 'listening'
      return true
    } catch (err) {
      // 已在录音时 start 会抛 InvalidStateError，视为无操作
      status.value = 'idle'
      return false
    }
  }

  /** 停止录音 */
  function stop() {
    if (!recognition) return
    try {
      recognition.stop()
    } catch (err) {
      /* 忽略 */
    }
    status.value = 'idle'
  }

  function toggle() {
    return listening.value ? (stop(), false) : start()
  }

  onBeforeUnmount(() => {
    destroy()
  })

  return { supported, status, listening, transcript, interim, errorMsg, start, stop, toggle }
}

export default useSpeech

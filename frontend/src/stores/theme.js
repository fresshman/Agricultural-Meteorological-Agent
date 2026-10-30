import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { KEYS, readJSON, writeJSON } from '@/utils/storage'

/**
 * 主题模式：`light` 浅色 / `dark` 深色 / `auto` 跟随系统。
 * @typedef {'light'|'dark'|'auto'} ThemeMode
 */

const VALID_MODES = ['light', 'dark', 'auto']
const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)'

/** @returns {boolean} 系统是否处于深色偏好 */
function getSystemDark() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia(DARK_MEDIA_QUERY).matches
}

export const useThemeStore = defineStore('theme', () => {
  /** @type {import('vue').Ref<ThemeMode>} */
  const mode = ref('auto')
  /** 系统偏好（仅 auto 模式生效） */
  const systemDark = ref(false)

  /** 实际是否深色 */
  const isDark = computed(() => {
    if (mode.value === 'dark') return true
    if (mode.value === 'light') return false
    return systemDark.value
  })

  /** 媒体查询句柄，卸载监听时使用 */
  let media = null

  function handleSystemChange(evt) {
    systemDark.value = evt.matches
  }

  /** 同步 `html.dark` 类与地址栏主题色 */
  function apply() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.classList.toggle('dark', isDark.value)
    root.style.colorScheme = isDark.value ? 'dark' : 'light'
    const meta = document.querySelector('meta[name="theme-color"]:not([media])')
    if (meta) meta.setAttribute('content', isDark.value ? '#0E1A14' : '#F6F8F7')
  }

  /**
   * 初始化：恢复偏好 → 应用 class → 注册系统主题监听。
   * 必须在 `app.mount()` 之前调用。
   */
  function init() {
    const saved = readJSON(KEYS.THEME, null)
    const savedMode = saved && typeof saved.mode === 'string' ? saved.mode : 'auto'
    mode.value = VALID_MODES.includes(savedMode) ? savedMode : 'auto'
    systemDark.value = getSystemDark()
    apply()

    if (typeof window !== 'undefined' && window.matchMedia) {
      media = window.matchMedia(DARK_MEDIA_QUERY)
      if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', handleSystemChange)
      } else if (typeof media.addListener === 'function') {
        media.addListener(handleSystemChange) // Safari < 14 兼容
      }
    }
  }

  /**
   * 显式设置主题模式并持久化。
   * @param {ThemeMode} next
   */
  function setMode(next) {
    const target = VALID_MODES.includes(next) ? next : 'auto'
    mode.value = target
    writeJSON(KEYS.THEME, { v: 1, mode: target })
  }

  /** 三态循环：auto → light → dark → auto */
  function toggle() {
    const order = ['auto', 'light', 'dark']
    const idx = order.indexOf(mode.value)
    setMode(order[(idx + 1) % order.length])
  }

  watch(isDark, apply)

  return { mode, systemDark, isDark, init, setMode, toggle }
})

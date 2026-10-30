import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * 自动刷新调度（P1 预警中心）。
 * --------------------------------------------------------------------------
 * - 刷新间隔禁止 < 60s（调用方传入的最小档即为 1min）。
 * - 页面不可见（visibilitychange）时暂停轮询，恢复后立刻校准。
 * - 通过 `now` 每秒自增驱动倒计时文本，无需外部驱动。
 *
 * @param {{ enabled: import('vue').Ref<boolean>, intervalMs: import('vue').Ref<number>, onRefresh: () => void, lastUpdated: import('vue').Ref<Date|null> }} opts
 */
export function useAutoRefresh({ enabled, intervalMs, onRefresh, lastUpdated }) {
  const now = ref(Date.now())
  const paused = ref(false)
  let timer = null
  let tickTimer = null

  function schedule() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    if (!enabled.value) return
    timer = setInterval(() => {
      if (paused.value) return
      onRefresh()
    }, intervalMs.value)
  }

  const countdownText = computed(() => {
    if (!enabled.value || !lastUpdated.value) return ''
    const elapsed = now.value - new Date(lastUpdated.value).getTime()
    const remain = Math.max(0, Math.ceil((intervalMs.value - elapsed) / 1000))
    const m = Math.floor(remain / 60)
    const s = remain % 60
    const p = (n) => String(n).padStart(2, '0')
    return `${p(m)}:${p(s)}`
  })

  function onVisibility() {
    paused.value = document.hidden
    if (!document.hidden) {
      now.value = Date.now()
      // 恢复可见后若已超过间隔，立即校准一次
      if (lastUpdated.value && now.value - new Date(lastUpdated.value).getTime() >= intervalMs.value) {
        onRefresh()
      }
    }
  }

  onMounted(() => {
    tickTimer = setInterval(() => {
      now.value = Date.now()
    }, 1000)
    schedule()
    document.addEventListener('visibilitychange', onVisibility)
  })

  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    if (tickTimer) clearInterval(tickTimer)
    document.removeEventListener('visibilitychange', onVisibility)
  })

  watch(enabled, schedule)
  watch(intervalMs, schedule)

  return { paused, countdownText }
}

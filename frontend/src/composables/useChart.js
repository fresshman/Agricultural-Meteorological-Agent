import * as echarts from 'echarts/core'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  DataZoomComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, shallowRef, watchEffect } from 'vue'
import { useThemeStore } from '@/stores/theme'

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  DataZoomComponent,
  CanvasRenderer
])

/** 读取 CSS 变量当前计算值（主题切换后需重新读取） */
function cssVar(name, fallback = '') {
  if (typeof window === 'undefined' || !window.getComputedStyle) return fallback
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

/**
 * 图表调色板：统一从 CSS 变量实时取值，禁止在 option 里硬编码颜色。
 * @returns {Record<string, string>}
 */
export function palette() {
  return {
    brand: cssVar('--brand-500', '#2E8B5B'),
    brand200: cssVar('--brand-200', '#A9D6BF'),
    brand100: cssVar('--brand-100', '#D9EBE0'),
    sky: cssVar('--sky-500', '#3E8FD6'),
    gold: cssVar('--gold-500', '#E0A438'),
    purple: cssVar('--state-purple', '#7A6BBF'),
    success: cssVar('--state-success', '#3FA372'),
    info: cssVar('--state-info', '#3E8FD6'),
    warning: cssVar('--state-warning', '#E0A438'),
    orange: cssVar('--state-orange', '#E8722C'),
    danger: cssVar('--state-danger', '#D64545'),
    text: cssVar('--text-body', '#3A4A42'),
    textTitle: cssVar('--text-title', '#16261D'),
    textSecondary: cssVar('--text-secondary', '#6B7C73'),
    textDisabled: cssVar('--text-disabled', '#A6B3AC'),
    border: cssVar('--border-light', '#E6ECE8'),
    borderStrong: cssVar('--border-strong', '#D2DDD6'),
    card: cssVar('--bg-card', '#FFFFFF'),
    subtle: cssVar('--bg-subtle', '#F0F4F1')
  }
}

/**
 * 统一的 tooltip / 图例 / 坐标轴外观（深浅两套共用同一份来源）。
 * @param {Record<string, string>} p palette() 的返回值
 * @returns {object}
 */
export function baseOption(p) {
  return {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 320,
    animationEasing: 'cubicOut',
    textStyle: { fontFamily: 'inherit', color: p.text },
    tooltip: {
      backgroundColor: p.card,
      borderColor: p.borderStrong,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: p.text, fontSize: 12 },
      extraCssText: 'box-shadow: 0 8px 24px rgba(22,38,29,.10); border-radius: 10px;'
    },
    legend: {
      itemWidth: 14,
      itemHeight: 8,
      itemGap: 16,
      icon: 'roundRect',
      textStyle: { color: p.textSecondary, fontSize: 12 }
    }
  }
}

/**
 * ECharts 生命周期管理：主题感知重建 + 响应式 resize。
 *
 * 深色模式采用 `dispose() → init()` 而非仅 setOption —— 因为 ECharts 内部
 * 部分样式（背景、tooltip）在 setOption 合并时不会完全覆盖，容易残留白底。
 *
 * @param {import('vue').Ref<HTMLElement|null>} elRef 图表容器
 * @param {() => object} buildOption 返回 ECharts option 的函数（内部读取响应式数据以建立依赖）
 * @returns {{ chart: import('vue').ShallowRef<object|null>, refresh: () => void, resize: () => void }}
 */
export function useChart(elRef, buildOption) {
  const themeStore = useThemeStore()
  const chart = shallowRef(null)
  let observer = null
  let rafId = 0

  function render() {
    const el = elRef?.value
    if (!el) return
    if (!chart.value) {
      chart.value = echarts.init(el, undefined, { renderer: 'canvas' })
    }
    const option = typeof buildOption === 'function' ? buildOption() : {}
    chart.value.setOption(option || {}, true)
  }

  /** 彻底重建：主题切换时调用，避免残留白底 */
  function rebuild() {
    if (chart.value) {
      chart.value.dispose()
      chart.value = null
    }
    render()
  }

  function resize() {
    if (rafId) cancelAnimationFrame(rafId)
    rafId = requestAnimationFrame(() => {
      rafId = 0
      chart.value?.resize()
    })
  }

  onMounted(() => {
    if (typeof ResizeObserver !== 'undefined' && elRef?.value) {
      observer = new ResizeObserver(resize)
      observer.observe(elRef.value)
    }
    window.addEventListener('resize', resize)
  })

  // 依赖主题与 buildOption 内部读取的所有响应式数据；flush:'post' 保证 DOM 已挂载
  watchEffect(
    () => {
      void themeStore.isDark
      rebuild()
    },
    { flush: 'post' }
  )

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
    window.removeEventListener('resize', resize)
    if (rafId) cancelAnimationFrame(rafId)
    if (chart.value) {
      chart.value.dispose()
      chart.value = null
    }
  })

  return { chart, refresh: rebuild, resize }
}

export { echarts }

<template>
  <div class="forecast-chart">
    <!-- 宽屏：ECharts 温线 + 降水柱 + 风险色带 -->
    <div v-show="!isNarrow" ref="elRef" class="forecast-chart__canvas" :style="{ height: typeof height === 'number' ? `${height}px` : height }"></div>

    <!-- 窄屏降级：横向滚动的逐日卡片组 -->
    <div v-if="isNarrow" class="forecast-chart__cards">
      <div v-for="day in days" :key="day.label" class="forecast-day card">
        <div class="forecast-day__date">{{ day.shortLabel || day.label }}</div>
        <div class="forecast-day__temp num">{{ tempText(day) }}</div>
        <div class="forecast-day__precip num">{{ precipText(day) }}</div>
        <RiskBadge v-if="dayRisk(day)" :level="dayRisk(day).level" :label="dayRisk(day).label" size="sm" />
        <span v-else class="forecast-day__na num">--</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useChart, baseOption, palette } from '@/composables/useChart'
import { OPERATIONS, scoreDay } from '@/utils/suitability'
import { suitabilityMeta } from '@/utils/risk'
import RiskBadge from '@/components/RiskBadge.vue'

const props = defineProps({
  /** 按日聚合后的气象（来自 weather.daily7） */
  days: { type: Array, default: () => [] },
  /** 图表高度 */
  height: { type: [Number, String], default: 280 },
  /** 是否展示图例 */
  showLegend: { type: Boolean, default: true }
})

const elRef = ref(null)
const isNarrow = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)

/** 某天在 7 类操作下的最弱适宜度（短板决定风险） */
function dayRisk(day) {
  let min = Infinity
  for (const op of OPERATIONS) {
    const r = scoreDay(op, day)
    if (r.score !== null && Number.isFinite(r.score) && r.score < min) min = r.score
  }
  if (!Number.isFinite(min)) return null
  return suitabilityMeta(min)
}

function tempText(day) {
  const v = Number(day?.tempAvg)
  return Number.isFinite(v) ? `${v.toFixed(0)}℃` : '--'
}
function precipText(day) {
  const v = Number(day?.precipSum)
  return Number.isFinite(v) ? `${v.toFixed(1)}mm` : '--'
}

function buildOption() {
  const p = palette()
  const list = Array.isArray(props.days) ? props.days : []
  const labels = list.map((d) => d.shortLabel || d.label || '')
  const temps = list.map((d) => (Number.isFinite(Number(d?.tempAvg)) ? Number(d.tempAvg) : null))
  const rains = list.map((d) => (Number.isFinite(Number(d?.precipSum)) ? Number(d.precipSum) : null))
  const levelKey = { good: 'success', ok: 'info', care: 'orange', bad: 'danger' }
  const riskBars = list.map((d) => {
    const m = dayRisk(d)
    const color = m ? p[levelKey[m.level]] || p.success : p.textDisabled
    return { value: 1, itemStyle: { color, borderRadius: [2, 2, 0, 0] } }
  })

  return {
    ...baseOption(p),
    grid: [
      { left: 8, right: 8, top: 44, bottom: '30%', containLabel: true },
      { left: 8, right: 8, top: '74%', height: 16, containLabel: false }
    ],
    tooltip: {
      ...baseOption(p).tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,0.08)' } },
      formatter: (params) => {
        const idx = params[0]?.dataIndex ?? 0
        const day = list[idx]
        const risk = dayRisk(day)
        const parts = [`<b>${labels[idx] || ''}</b>`]
        parts.push(`均温：${tempText(day)}`)
        parts.push(`降水：${precipText(day)}`)
        if (risk) parts.push(`适宜度：${risk.label}（${risk.percent}）`)
        else parts.push('适宜度：数据不足')
        return parts.join('<br/>')
      }
    },
    legend: {
      ...baseOption(p).legend,
      show: props.showLegend,
      top: 0,
      data: ['日均温 (℃)', '降水 (mm)']
    },
    xAxis: [
      {
        type: 'category',
        gridIndex: 0,
        data: labels,
        boundaryGap: true,
        axisLine: { lineStyle: { color: p.border } },
        axisTick: { show: false },
        axisLabel: { color: p.textDisabled, fontSize: 12 }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: labels,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        name: '℃',
        nameTextStyle: { color: p.textDisabled, fontSize: 12, padding: [0, 0, 0, 4] },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: p.textDisabled, fontSize: 12 },
        splitLine: { lineStyle: { color: p.border, type: 'dashed' } }
      },
      {
        type: 'value',
        gridIndex: 0,
        name: 'mm',
        position: 'right',
        nameTextStyle: { color: p.textDisabled, fontSize: 12 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: p.textDisabled, fontSize: 12 },
        splitLine: { show: false }
      },
      { type: 'value', gridIndex: 1, min: 0, max: 1, show: false }
    ],
    series: [
      {
        name: '日均温 (℃)',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: temps,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        connectNulls: true,
        lineStyle: { color: p.orange, width: 2.4 },
        itemStyle: { color: p.orange },
        areaStyle: { color: p.orange, opacity: 0.07 },
        z: 3
      },
      {
        name: '降水 (mm)',
        type: 'bar',
        xAxisIndex: 0,
        yAxisIndex: 1,
        data: rains,
        barMaxWidth: 18,
        itemStyle: { color: p.sky, borderRadius: [3, 3, 0, 0], opacity: 0.85 },
        z: 2
      },
      {
        name: '适宜度色带',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: riskBars,
        barWidth: '64%',
        silent: true,
        z: 5
      }
    ]
  }
}

const { refresh } = useChart(elRef, buildOption)

function onResize() {
  const narrow = window.innerWidth < 768
  if (narrow !== isNarrow.value) {
    isNarrow.value = narrow
    if (!narrow) refresh()
  }
}
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

defineExpose({ refresh })
</script>

<style scoped>
.forecast-chart {
  width: 100%;
}
.forecast-chart__canvas {
  width: 100%;
  min-height: 200px;
}
.forecast-chart__cards {
  display: flex;
  gap: var(--sp-2);
  overflow-x: auto;
  padding-bottom: var(--sp-2);
  scroll-snap-type: x mandatory;
}
.forecast-day {
  flex: 0 0 auto;
  width: 96px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-3);
  text-align: center;
}
.forecast-day__date {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
  font-weight: 600;
}
.forecast-day__temp {
  font-size: var(--fs-h3);
  font-weight: 700;
  color: var(--text-title);
}
.forecast-day__precip {
  font-size: var(--fs-caption);
  color: var(--state-info);
}
.forecast-day__na {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}
</style>

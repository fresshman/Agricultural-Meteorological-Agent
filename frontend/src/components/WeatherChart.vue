<template>
  <div ref="elRef" class="weather-chart" :style="{ height: typeof height === 'number' ? `${height}px` : height }"></div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useChart, baseOption, palette } from '@/composables/useChart'
import { useWeatherStore } from '@/stores/weather'

const props = defineProps({
  /** 逐时气象序列；不传时回退到 weather store（兼容旧调用方） */
  points: { type: Array, default: null },
  /** 图表高度，数字按 px 处理 */
  height: { type: [Number, String], default: 300 },
  /** 是否展示图例 */
  showLegend: { type: Boolean, default: true }
})

const weather = useWeatherStore()

/** 实际使用的数据源 */
const dataPoints = computed(() => {
  if (Array.isArray(props.points) && props.points.length) return props.points
  return weather.hourly || []
})

const elRef = ref(null)

function labelOf(ts) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts ?? '--')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  return `${mm}-${dd} ${hh}时`
}

function buildOption() {
  const p = palette()
  const list = dataPoints.value
  const times = list.map((d) => labelOf(d?.timestamp))
  const temps = list.map((d) => (Number.isFinite(Number(d?.temperature)) ? Number(d.temperature) : null))
  const rains = list.map((d) => (Number.isFinite(Number(d?.precipitation)) ? Number(d.precipitation) : null))
  const hums = list.map((d) => (Number.isFinite(Number(d?.humidity)) ? Number(d.humidity) : null))

  return {
    ...baseOption(p),
    grid: { left: 8, right: 8, top: 40, bottom: 8, containLabel: true },
    tooltip: {
      ...baseOption(p).tooltip,
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: p.borderStrong, type: 'dashed' } }
    },
    legend: {
      ...baseOption(p).legend,
      show: props.showLegend,
      top: 0,
      data: ['温度 (℃)', '降水 (mm)', '相对湿度 (%)']
    },
    xAxis: {
      type: 'category',
      data: times,
      boundaryGap: list.length <= 8,
      axisLine: { lineStyle: { color: p.border } },
      axisTick: { show: false },
      axisLabel: {
        color: p.textDisabled,
        fontSize: 12,
        hideOverlap: true,
        interval: Math.max(0, Math.ceil(list.length / 8) - 1)
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '℃ / mm',
        nameTextStyle: { color: p.textDisabled, fontSize: 12, padding: [0, 0, 0, 8] },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: p.textDisabled, fontSize: 12 },
        splitLine: { lineStyle: { color: p.border, type: 'dashed' } }
      },
      {
        type: 'value',
        name: '%',
        min: 0,
        max: 100,
        nameTextStyle: { color: p.textDisabled, fontSize: 12 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: p.textDisabled, fontSize: 12 },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '温度 (℃)',
        type: 'line',
        data: temps,
        smooth: true,
        symbol: 'none',
        connectNulls: true,
        lineStyle: { color: p.orange, width: 2 },
        areaStyle: { color: p.orange, opacity: 0.06 },
        z: 3
      },
      {
        name: '降水 (mm)',
        type: 'bar',
        data: rains,
        barMaxWidth: 12,
        itemStyle: { color: p.sky, borderRadius: [3, 3, 0, 0], opacity: 0.85 },
        z: 2
      },
      {
        name: '相对湿度 (%)',
        type: 'line',
        yAxisIndex: 1,
        data: hums,
        smooth: true,
        symbol: 'none',
        connectNulls: true,
        lineStyle: { color: p.brand200, width: 1.5, type: 'dashed' },
        z: 1
      }
    ]
  }
}

const { refresh } = useChart(elRef, buildOption)

defineExpose({ refresh })
</script>

<style scoped>
.weather-chart {
  width: 100%;
  min-height: 200px;
}
</style>

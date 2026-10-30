<template>
  <div class="growth-curve">
    <div v-if="!model" class="growth-curve__empty">暂无可用的作物生长模型</div>
    <template v-else>
      <div ref="el" class="growth-curve__canvas" :style="{ height: height + 'px' }"></div>
      <p v-if="!model.hasWeather" class="growth-curve__note">
        气象数据不足，仅展示理论发育曲线；实际长势将在气象恢复后推算。
      </p>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useChart, palette, baseOption } from '@/composables/useChart'
import { formatMonthDay } from '@/utils/format'

const props = defineProps({
  /** buildGrowthModel 的返回值 */
  model: { type: Object, default: null },
  height: { type: Number, default: 240 }
})

const el = ref(null)

function buildOption() {
  const p = palette()
  const m = props.model
  if (!m) return {}

  const dates = m.points.map((pt) => formatMonthDay(pt.date))
  const theo = m.points.map((pt) => pt.theo)
  const actual = m.points.map((pt) => (pt.actual === null ? null : pt.actual))

  const option = {
    ...baseOption(p),
    grid: { left: 38, right: 14, top: 28, bottom: 26 },
    tooltip: {
      ...baseOption(p).tooltip,
      trigger: 'axis',
      valueFormatter: (v) => (v == null ? '—' : v + ' 分')
    },
    legend: {
      ...baseOption(p).legend,
      top: 0,
      right: 0,
      data: m.hasWeather ? ['理论生长', '实际生长'] : ['理论生长']
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: p.borderStrong } },
      axisLabel: { color: p.textSecondary, fontSize: 11, interval: Math.floor(dates.length / 6) },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      name: '长势指数',
      nameTextStyle: { color: p.textDisabled, fontSize: 11, align: 'left' },
      nameGap: 8,
      axisLabel: { color: p.textSecondary, fontSize: 11, formatter: '{value}' },
      splitLine: { lineStyle: { color: p.border, type: 'dashed' } }
    },
    series: [
      {
        name: '理论生长',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: theo,
        lineStyle: { color: p.textDisabled, width: 2, type: 'dashed' },
        itemStyle: { color: p.textDisabled },
        z: 1
      },
      {
        name: '实际生长',
        type: 'line',
        smooth: true,
        showSymbol: false,
        connectNulls: false,
        data: actual,
        lineStyle: { color: p.brand, width: 2.6 },
        itemStyle: { color: p.brand },
        areaStyle: { color: p.brand, opacity: 0.1 },
        z: 2,
        markLine: {
          silent: true,
          symbol: 'none',
          label: { show: true, formatter: '今天', color: p.brand, fontSize: 11, position: 'insideEndTop' },
          lineStyle: { color: p.brand, type: 'solid', width: 1.4 },
          data: [{ xAxis: m.todayIndex }]
        }
      }
    ]
  }
  return option
}

const { refresh } = useChart(el, buildOption)

// 数据（如气象加载完成）或属性变化后重绘
watch(
  () => [props.model, props.model?.hasWeather, props.model?.todayIndex],
  () => refresh(),
  { deep: false }
)
</script>

<style scoped>
.growth-curve {
  width: 100%;
}
.growth-curve__canvas {
  width: 100%;
}
.growth-curve__empty {
  padding: var(--sp-6);
  text-align: center;
  color: var(--text-disabled);
  font-size: var(--fs-sm);
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
}
.growth-curve__note {
  margin: var(--sp-2) 0 0;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
  line-height: var(--lh-caption);
}
</style>

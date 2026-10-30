<template>
  <section class="weather-panel card">
    <header class="weather-panel__head">
      <div class="weather-panel__title">
        <el-icon :size="18"><MostlyCloudy /></el-icon>
        <span>实时气象</span>
      </div>
      <span class="weather-panel__addr truncate">{{ loc.summary }}</span>
      <el-button
        class="weather-panel__refresh"
        size="small"
        text
        :loading="weather.loading"
        aria-label="刷新气象"
        @click="weather.refresh()"
      >
        <el-icon><Refresh /></el-icon>
      </el-button>
    </header>

    <!-- 加载中：骨架屏 -->
    <div v-if="weather.loading && !weather.available" class="weather-panel__grid">
      <SkeletonCard v-for="i in 4" :key="`sk${i}`" variant="card" :rows="1" />
    </div>

    <!-- 有数据：4 个指标卡 -->
    <div v-else class="weather-panel__grid">
      <MetricCard
        icon="Sunny"
        label="气温"
        :value="temperature"
        unit="℃"
        :digits="1"
        :hint="tempHint"
        :trend="tempTrend"
        tone="orange"
        :loading="!weather.available"
      />
      <MetricCard
        icon="Drizzling"
        label="相对湿度"
        :value="humidity"
        unit="%"
        :digits="0"
        :hint="humidityHint"
        tone="sky"
        :loading="!weather.available"
      />
      <MetricCard
        icon="Pouring"
        label="未来 12h 降水"
        :value="precipitation"
        unit="mm"
        :digits="1"
        :hint="precipHint"
        tone="info"
        :loading="!weather.available"
      />
      <MetricCard
        icon="WindPower"
        label="风速风向"
        :value="windSpeed"
        unit="m/s"
        :digits="1"
        :hint="windHint"
        tone="brand"
        :loading="!weather.available"
      />
    </div>

    <footer class="weather-panel__foot">
      <span class="weather-panel__dot" :class="weather.available ? 'is-ok' : 'is-warn'" aria-hidden="true"></span>
      <span class="weather-panel__summary truncate">
        {{ weather.available ? weather.summary || '数据源：实时气象接口' : weather.error || '气象数据暂不可用' }}
      </span>
      <el-button v-if="!weather.available && weather.error" size="small" text type="primary" @click="weather.refresh()">
        重试
      </el-button>
      <span v-if="weather.lastUpdated" class="weather-panel__time num">
        {{ formatTime(weather.lastUpdated) }} 更新
      </span>
    </footer>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import MetricCard from '@/components/MetricCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import { useWeatherStore } from '@/stores/weather'
import { useLocationStore } from '@/stores/location'
import { formatTime, beaufortLevel, normalizeWindDirection } from '@/utils/format'

const weather = useWeatherStore()
const loc = useLocationStore()

onMounted(() => {
  if (!weather.available && !weather.loading) weather.loadWeather(168)
})

/** 取当前样本字段，无数据时返回 null（由 MetricCard 显示 '--'） */
function pick(key) {
  if (!weather.available) return null
  const v = Number(weather.current?.[key])
  return Number.isFinite(v) ? v : null
}

const temperature = computed(() => pick('temperature'))
const humidity = computed(() => pick('humidity'))
const windSpeed = computed(() => pick('wind_speed'))
const precipitation = computed(() => {
  if (!weather.available) return null
  const v = Number(weather.precipNext12)
  return Number.isFinite(v) ? v : null
})

/** 与 24h 前同一样本比较得到升降趋势 */
const tempTrend = computed(() => {
  const list = weather.hourly
  if (list.length < 25) return 'flat'
  const now = Number(list[0]?.temperature)
  const before = Number(list[24]?.temperature)
  if (!Number.isFinite(now) || !Number.isFinite(before)) return 'flat'
  const diff = now - before
  if (diff > 0.5) return 'up'
  if (diff < -0.5) return 'down'
  return 'flat'
})

const tempHint = computed(() => {
  const t = temperature.value
  const h = humidity.value
  if (t === null) return '--'
  if (t >= 35) return '高温预警，注意防暑降温'
  if (t >= 30 && Number(h) >= 70) return '闷热，病害风险上升'
  if (t <= 5) return '低温，注意防冻'
  return `体感接近 ${t.toFixed(0)}℃，适宜田间作业`
})

const humidityHint = computed(() => {
  const h = humidity.value
  if (h === null) return '--'
  if (h >= 85) return '偏湿 · 注意病害'
  if (h >= 60) return '湿度适中'
  if (h >= 40) return '略干，注意补水'
  return '干燥 · 需灌溉'
})

const precipHint = computed(() => {
  const p = precipitation.value
  if (p === null) return '--'
  if (p <= 0) return '未来 12h 无降水'
  if (p < 2) return '小雨，可安排喷药'
  if (p < 10) return '有降水，推迟户外作业'
  return '降水偏多，注意排涝'
})

/** m/s → 蒲福风级（统一走 utils/format，避免各页面各写一份） */
const windHint = computed(() => {
  const w = windSpeed.value
  if (w === null) return '--'
  const dir = normalizeWindDirection(weather.current?.wind_direction || weather.current?.windDir)
  const level = beaufortLevel(w)
  const spraying = w <= 3.3 ? '适宜喷药' : w <= 5.4 ? '谨慎喷药' : '不宜喷药'
  return `${dir ? `${dir} · ` : ''}${level} 级 · ${spraying}`
})
</script>

<style scoped>
.weather-panel {
  padding: var(--sp-5);
}

.weather-panel__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: var(--sp-4);
}

.weather-panel__title {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}

.weather-panel__addr {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

.weather-panel__refresh {
  flex: 0 0 auto;
}

.weather-panel__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--gutter);
}

.weather-panel__foot {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-top: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px dashed var(--border-light);
}

.weather-panel__dot {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: var(--radius-full);
}

.weather-panel__dot.is-ok {
  background: var(--state-success);
}

.weather-panel__dot.is-warn {
  background: var(--state-warning);
}

.weather-panel__summary {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.weather-panel__time {
  flex: 0 0 auto;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

@media (max-width: 1199px) {
  .weather-panel__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .weather-panel {
    padding: var(--sp-4);
  }

  .weather-panel__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--gutter-mobile);
  }
}
</style>

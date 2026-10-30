<template>
  <div class="warn-view">
    <PageHeader title="预警中心" subtitle="基于实时气象的灾害与病虫害风险推演，进入页面自动分析">
      <template #actions>
        <el-select v-model="crop" size="small" class="warn-view__crop" @change="onCropChange">
          <el-option v-for="c in CROPS" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button :icon="Refresh" :loading="warning.loading" @click="warning.analyze()">重新分析</el-button>
      </template>
    </PageHeader>

    <!-- 控制条 -->
    <div class="warn-view__bar card">
      <el-radio-group v-model="dateDim" size="small">
        <el-radio-button value="today">今天</el-radio-button>
        <el-radio-button value="tomorrow">明天</el-radio-button>
        <el-radio-button value="week">未来 7 天</el-radio-button>
      </el-radio-group>

      <div class="warn-view__refresh">
        <span class="warn-view__updated" v-if="warning.lastUpdated">
          上次更新 {{ formatTime(warning.lastUpdated) }}
          <span v-if="enabled && countdown" class="warn-view__cd num">· {{ countdown }} 后刷新</span>
        </span>
        <el-switch
          v-model="enabled"
          class="warn-view__switch"
          active-text="自动刷新"
          inline-prompt
          @change="onEnableChange"
        />
        <el-select v-model="intervalMs" size="small" class="warn-view__interval" :disabled="!enabled">
          <el-option label="每 1 分钟" :value="60000" />
          <el-option label="每 5 分钟" :value="300000" />
          <el-option label="每 15 分钟" :value="900000" />
        </el-select>
      </div>
    </div>

    <!-- 结果区 -->
    <div v-if="warning.loading && !warning.analyzed" class="warn-view__list">
      <SkeletonCard v-for="i in 3" :key="i" variant="card" :rows="3" />
    </div>

    <EmptyState
      v-else-if="!visibleItems.length"
      icon="CircleCheck"
      :title="warning.error ? '分析暂不可用' : '当前时段无显著风险'"
      :description="warning.error || '所选时段内未发现高价值灾害或病虫害预警，可切换到「未来 7 天」查看'"
      size="lg"
    />

    <div v-else class="warn-view__list">
      <article
        v-for="item in visibleItems"
        :key="item._id"
        class="warn-card card-hover"
        :class="`warn-card--${item.category}`"
      >
        <header class="warn-card__head">
          <RiskBadge :level="item.risk_level" :label="item.risk_level" size="md" />
          <div class="warn-card__title">
            <span class="warn-card__type">{{ item.type }}</span>
            <span class="warn-card__cat">{{ item.category === 'pest' ? '病虫害' : '气象灾害' }}</span>
          </div>
        </header>

        <dl class="warn-card__detail">
          <div v-if="item.details.occur_time" class="warn-card__row">
            <dt>发生时间</dt><dd>{{ item.details.occur_time }}</dd>
          </div>
          <div v-if="item.details.intensity" class="warn-card__row">
            <dt>强度</dt><dd>{{ item.details.intensity }}</dd>
          </div>
          <div v-if="item.details.duration" class="warn-card__row">
            <dt>持续时间</dt><dd>{{ item.details.duration }}</dd>
          </div>
          <div v-if="item.details.occur_probability != null" class="warn-card__row">
            <dt>发生概率</dt><dd class="num">{{ item.details.occur_probability }}</dd>
          </div>
          <div v-if="measures(item).length" class="warn-card__row warn-card__row--block">
            <dt>{{ item.category === 'pest' ? '防控建议' : '防御措施' }}</dt>
            <dd>
              <ul class="warn-card__measures">
                <li v-for="(m, i) in measures(item)" :key="i">{{ m }}</li>
              </ul>
            </dd>
          </div>
        </dl>
      </article>
    </div>

    <!-- 7 天趋势 -->
    <section class="warn-view__forecast card">
      <header class="warn-view__forecast-head">
        <h2 class="warn-view__forecast-title">未来 7 天气象与农事适宜度</h2>
      </header>
      <ForecastChart :days="weather.daily7" :height="320" />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import RiskBadge from '@/components/RiskBadge.vue'
import ForecastChart from '@/components/ForecastChart.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useWarningStore } from '@/stores/warning'
import { useWeatherStore } from '@/stores/weather'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import { formatTime } from '@/utils/format'
import { CROP_TYPES as CROPS } from '@/utils/crops'

const warning = useWarningStore()
const weather = useWeatherStore()

const dateDim = ref('week')
const crop = ref(warning.cropType || '玉米')

// 自动刷新
const enabled = ref(false)
const intervalMs = ref(300000)
const { countdown } = useAutoRefresh({
  enabled,
  intervalMs,
  lastUpdated: computed(() => warning.lastUpdated),
  onRefresh: () => warning.analyze()
})

const visibleItems = computed(() => warning.filterByDimension(warning.all, dateDim.value))

function measures(item) {
  const d = item.details || {}
  const list = []
  if (Array.isArray(d.defense_measures)) list.push(...d.defense_measures)
  if (Array.isArray(d.emergency_actions)) list.push(...d.emergency_actions)
  if (Array.isArray(d.prevention_measures)) list.push(...d.prevention_measures)
  if (Array.isArray(d.control_measures)) list.push(...d.control_measures)
  return list.filter(Boolean).slice(0, 5)
}

function onEnableChange(val) {
  if (val) warning.analyze()
}
function onCropChange(val) {
  warning.setCrop(val)
  warning.analyze()
}

onMounted(() => {
  warning.analyze()
  if (!weather.available && !weather.loading) weather.loadWeather(168)
})
</script>

<style scoped>
.warn-view {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1200px;
  margin: 0 auto;
}

.warn-view__crop {
  width: 110px;
}

.warn-view__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  flex-wrap: wrap;
}

.warn-view__refresh {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.warn-view__updated {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.warn-view__cd {
  color: var(--brand-600);
}

.warn-view__interval {
  width: 120px;
}

.warn-view__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--sp-4);
}

.warn-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-5);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-1);
}

.warn-card__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.warn-card__title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.warn-card__type {
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}

.warn-card__cat {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.warn-card__detail {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.warn-card__row {
  display: flex;
  gap: var(--sp-3);
  font-size: var(--fs-sm);
}

.warn-card__row dt {
  flex: 0 0 72px;
  color: var(--text-disabled);
}

.warn-card__row dd {
  margin: 0;
  color: var(--text-body);
}

.warn-card__row--block dd {
  flex: 1 1 auto;
}

.warn-card__measures {
  margin: 0;
  padding-left: 1.2em;
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--text-body);
}

.warn-view__forecast {
  padding: var(--sp-5);
}

.warn-view__forecast-title {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}

@media (max-width: 767px) {
  .warn-view__bar {
    flex-direction: column;
    align-items: stretch;
  }
  .warn-view__refresh {
    justify-content: space-between;
  }
  .warn-view__list {
    grid-template-columns: 1fr;
  }
}
</style>

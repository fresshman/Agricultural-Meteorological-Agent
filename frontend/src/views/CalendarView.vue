<template>
  <div class="calendar">
    <PageHeader title="农事日历" subtitle="7 类农事 × 未来 7 天适宜度矩阵，点击单元格查看气象依据与方案建议">
      <template #actions>
        <el-select v-model="crop" size="small" class="calendar__crop" @change="onCropChange">
          <el-option v-for="c in CROPS" :key="c" :label="c" :value="c" />
        </el-select>
      </template>
    </PageHeader>

    <section class="calendar__matrix card">
      <SkeletonCard v-if="weather.loading && !weather.available" variant="chart" />
      <SuitabilityMatrix
        v-else
        :rows="matrix.rows"
        :days="matrix.days"
        :unavailable="!weather.available"
        @cell="openCell"
        @retry="weather.loadWeather(168)"
      />
    </section>

    <!-- 单元格详情抽屉 -->
    <el-drawer
      :model-value="!!active"
      :size="drawerSize"
      :with-header="false"
      direction="rtl"
      @update:model-value="(v) => !v && closeDrawer()"
    >
      <div v-if="active" class="cal-drawer">
        <header class="cal-drawer__head">
          <div>
            <h2 class="cal-drawer__title">{{ active.day.label }} · {{ active.op }}</h2>
            <p class="cal-drawer__sub">
              <RiskBadge :level="active.cell.level === 'unknown' ? 'info' : active.levelLabel" :label="active.levelLabel" size="sm" />
              <span v-if="active.cell.score !== null" class="cal-drawer__score num">综合评分 {{ active.cell.score }}</span>
              <span v-else class="cal-drawer__score">气象不足</span>
            </p>
          </div>
          <button type="button" class="cal-drawer__close" aria-label="关闭" @click="closeDrawer()">
            <el-icon :size="18"><Close /></el-icon>
          </button>
        </header>

        <div class="cal-drawer__body">
          <!-- 当日气象明细 -->
          <section class="cal-drawer__sec">
            <h3 class="cal-drawer__h">当日气象明细</h3>
            <div class="cal-drawer__facts">
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">日均温</span>
                <span class="cal-drawer__fv num">{{ num(active.day.tempAvg) }}℃</span>
              </div>
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">最高 / 最低</span>
                <span class="cal-drawer__fv num">{{ num(active.day.tempMax) }} / {{ num(active.day.tempMin) }}℃</span>
              </div>
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">累计降水</span>
                <span class="cal-drawer__fv num">{{ num(active.day.precipSum) }}mm</span>
              </div>
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">平均湿度</span>
                <span class="cal-drawer__fv num">{{ num(active.day.humidityAvg) }}%</span>
              </div>
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">最大风速</span>
                <span class="cal-drawer__fv num">{{ num(active.day.windMax) }}m/s</span>
              </div>
              <div class="cal-drawer__fact">
                <span class="cal-drawer__fk">样本数</span>
                <span class="cal-drawer__fv num">{{ active.day.hours ?? '--' }}</span>
              </div>
            </div>
          </section>

          <!-- 前端按日推演 -->
          <section class="cal-drawer__sec">
            <h3 class="cal-drawer__h">前端按日推演依据</h3>
            <ul v-if="active.cell.reasons.length" class="cal-drawer__reasons">
              <li v-for="(r, i) in active.cell.reasons" :key="i">{{ r }}</li>
            </ul>
            <p v-else class="cal-drawer__na">气象样本不足或规则未命中，暂无推演依据</p>
          </section>

          <!-- 后端 72h 综合评估（懒加载 + 30min 缓存） -->
          <section class="cal-drawer__sec">
            <h3 class="cal-drawer__h">
              后端 72h 综合评估
              <span class="cal-drawer__cache">· 结果缓存 30 分钟</span>
            </h3>
            <div v-if="backend.loading" class="cal-drawer__backend-loading">
              <el-icon class="is-loading"><Loading /></el-icon> 正在评估…
            </div>
            <template v-else-if="backend.data">
              <RiskBadge :level="backendLevel" :label="backendLevel" size="sm" />
              <ul v-if="backendReasons.length" class="cal-drawer__reasons">
                <li v-for="(r, i) in backendReasons" :key="i">{{ r }}</li>
              </ul>
            </template>
            <p v-else class="cal-drawer__na">暂无数据（{{ backend.error || '评估服务未返回' }}）</p>
          </section>
        </div>

        <footer class="cal-drawer__foot">
          <el-button type="primary" :icon="Promotion" @click="generatePlan">一键生成方案</el-button>
        </footer>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Close, Loading, Promotion } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import SuitabilityMatrix from '@/components/SuitabilityMatrix.vue'
import RiskBadge from '@/components/RiskBadge.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import { useWeatherStore } from '@/stores/weather'
import { useLocationStore } from '@/stores/location'
import { useChatStore } from '@/stores/chat'
import { buildWeekMatrix, OPERATIONS } from '@/utils/suitability'
import { suitabilityMeta } from '@/utils/risk'
import { warningApi } from '@/api'
import { formatNumber } from '@/utils/format'
import { CROP_TYPES as CROPS } from '@/utils/crops'

const router = useRouter()
const weather = useWeatherStore()
const location = useLocationStore()
const chat = useChatStore()

const crop = ref(chat.cropType || '玉米')

const matrix = computed(() => buildWeekMatrix(weather.daily7, OPERATIONS))

const drawerSize = computed(() => {
  const w = typeof window !== 'undefined' ? window.innerWidth : 768
  return Math.min(w - 24, 460) + 'px'
})

// 抽屉状态
const active = ref(null)
const backend = ref({ loading: false, data: null, error: '' })

// 后端评估结果缓存（op -> {ts, data, error}），30 分钟有效
const backendCache = new Map()

const levelLabel = computed(() => {
  if (!active.value || active.value.cell.score === null) return '暂无数据'
  return suitabilityMeta(active.value.cell.score).label
})

const backendLevel = computed(() => {
  const lvl = backend.value?.data?.warnings?.[0]?.risk_level
  return lvl || 'info'
})
const backendReasons = computed(() => {
  const d = backend.value?.data?.warnings?.[0]?.details
  if (!d) return []
  const out = []
  if (d.occur_probability != null) out.push(`发生概率：${d.occur_probability}`)
  for (const k of ['defense_measures', 'prevention_measures', 'control_measures', 'emergency_actions']) {
    if (Array.isArray(d[k])) out.push(...d[k])
  }
  return out.filter(Boolean).slice(0, 5)
})

function num(v) {
  return formatNumber(v, 1)
}

function openCell(payload) {
  active.value = payload
  backend.value = { loading: false, data: null, error: '' }
  loadBackend(payload.op)
}

function closeDrawer() {
  active.value = null
}

async function loadBackend(op) {
  const cached = backendCache.get(op)
  if (cached && Date.now() - cached.ts < 30 * 60 * 1000) {
    backend.value = { loading: false, data: cached.data, error: cached.error }
    return
  }
  backend.value = { loading: true, data: null, error: '' }
  try {
    const res = await warningApi.suitability({
      operation_type: op,
      crop_type: crop.value,
      latitude: location.selected.latitude,
      longitude: location.selected.longitude,
      province: location.selected.province,
      city: location.selected.city
    })
    backendCache.set(op, { ts: Date.now(), data: res, error: '' })
    backend.value = { loading: false, data: res, error: '' }
  } catch (err) {
    const msg = err?.message || '评估失败'
    backendCache.set(op, { ts: Date.now(), data: null, error: msg })
    backend.value = { loading: false, data: null, error: msg }
  }
}

function generatePlan() {
  if (!active.value) return
  const lvl = active.value.cell.score === null ? '数据不足' : levelLabel.value
  const q = `${active.value.day.label} ${active.value.op}适宜度为「${lvl}」，给我一份农事方案建议`
  router.push({ path: '/chat', query: { q } })
}

function onCropChange(val) {
  chat.setContext(null, val)
  if (active.value) loadBackend(active.value.op)
}

onMounted(() => {
  if (!weather.available && !weather.loading) weather.loadWeather(168)
})
</script>

<style scoped>
.calendar {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1200px;
  margin: 0 auto;
}

.calendar__crop {
  width: 110px;
}

.calendar__matrix {
  padding: var(--sp-4);
}

.cal-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.cal-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5) var(--sp-5) var(--sp-3);
  border-bottom: 1px solid var(--border-light);
}
.cal-drawer__title {
  margin: 0;
  font-size: var(--fs-h2);
  font-weight: 700;
  color: var(--text-title);
}
.cal-drawer__sub {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin: var(--sp-2) 0 0;
  font-size: var(--fs-sm);
}
.cal-drawer__score {
  color: var(--text-secondary);
}
.cal-drawer__close {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
}
.cal-drawer__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
}
.cal-drawer__sec {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}
.cal-drawer__h {
  margin: 0;
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}
.cal-drawer__cache {
  font-size: var(--fs-caption);
  font-weight: 400;
  color: var(--text-disabled);
}
.cal-drawer__facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}
.cal-drawer__fact {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-3);
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
}
.cal-drawer__fk {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}
.cal-drawer__fv {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-title);
}
.cal-drawer__reasons {
  margin: 0;
  padding-left: 1.2em;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  font-size: var(--fs-sm);
  color: var(--text-body);
}
.cal-drawer__na {
  margin: 0;
  font-size: var(--fs-sm);
  color: var(--text-disabled);
}
.cal-drawer__backend-loading {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
.cal-drawer__foot {
  padding: var(--sp-4) var(--sp-5);
  border-top: 1px solid var(--border-light);
}
.cal-drawer__foot .el-button {
  width: 100%;
}
.is-loading {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

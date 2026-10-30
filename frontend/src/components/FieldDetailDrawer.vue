<template>
  <el-drawer
    :model-value="modelValue"
    :size="drawerSize"
    :with-header="false"
    direction="rtl"
    class="field-drawer"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div v-if="field" class="drawer">
      <header class="drawer__head">
        <div>
          <h2 class="drawer__title truncate">{{ field.name || '未命名地块' }}</h2>
          <p class="drawer__sub">
            <span>{{ field.crop || '作物未设' }}</span>
            <span class="drawer__dot">·</span>
            <span>{{ field.stage || '阶段未设' }}</span>
            <span class="drawer__dot">·</span>
            <span class="num">{{ formatNumber(field.area, 1) }} 亩</span>
          </p>
        </div>
        <button type="button" class="drawer__close" aria-label="关闭" @click="emit('update:modelValue', false)">
          <el-icon :size="18"><Close /></el-icon>
        </button>
      </header>

      <div class="drawer__body">
        <!-- 基本信息 -->
        <section class="drawer__section">
          <div class="drawer__hero">
            <div class="drawer__hero-glyph">
              <CropGlyph :crop="field.crop" :size="44" />
            </div>
            <div class="drawer__hero-info">
              <div class="drawer__facts drawer__facts--inline">
                <div class="drawer__fact">
                  <span class="drawer__fact-k">作物</span>
                  <span class="drawer__fact-v">{{ field.crop || '--' }}</span>
                </div>
                <div class="drawer__fact">
                  <span class="drawer__fact-k">生育阶段</span>
                  <span class="drawer__fact-v">{{ field.stage || '--' }}</span>
                </div>
                <div class="drawer__fact">
                  <span class="drawer__fact-k">面积</span>
                  <span class="drawer__fact-v num">{{ formatNumber(field.area, 1) }} 亩</span>
                </div>
                <div class="drawer__fact">
                  <span class="drawer__fact-k">创建时间</span>
                  <span class="drawer__fact-v num">{{ formatDate(field.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 作物生长曲线（理论 vs 实际） -->
        <section v-if="growth" class="drawer__section">
          <h3 class="drawer__h">
            作物生长曲线
            <span class="drawer__h-note">{{ growth.cropLabel }} · 理论 vs 实际长势</span>
          </h3>
          <div class="drawer__growth-stats">
            <div class="drawer__gstat">
              <span class="drawer__gstat-k">当前阶段</span>
              <span class="drawer__gstat-v">{{ growth.currentStage }}</span>
            </div>
            <div class="drawer__gstat">
              <span class="drawer__gstat-k">理论长势</span>
              <span class="drawer__gstat-v num">{{ growth.currentTheo }} 分</span>
            </div>
            <div class="drawer__gstat">
              <span class="drawer__gstat-k">实际长势</span>
              <span class="drawer__gstat-v num" :class="{ 'is-empty': growth.currentActual === null }">
                {{ growth.currentActual === null ? '待气象' : growth.currentActual + ' 分' }}
              </span>
            </div>
            <div class="drawer__gstat">
              <span class="drawer__gstat-k">{{ growth.harvested ? '状态' : '预计收获' }}</span>
              <span class="drawer__gstat-v num">{{ growth.harvested ? '已收获' : growth.harvestEtaDays + ' 天后' }}</span>
            </div>
          </div>
          <GrowthCurve :model="growth" :height="230" />
          <p class="drawer__growth-basis">{{ growth.basis }}</p>
        </section>

        <!-- 7 类农事适宜度（基于今日气象推演） -->
        <section class="drawer__section">
          <h3 class="drawer__h">
            今日农事适宜度
            <span class="drawer__h-note">依据 {{ location.summary }} 实时气象</span>
          </h3>
          <div class="drawer__suit">
            <SuitabilityBar
              v-for="op in ops"
              :key="op.op"
              :label="op.op"
              :value="op.score"
              icon="Sunny"
              :hint="op.reasons[0] || ''"
            />
          </div>
        </section>

        <!-- 72h 气象趋势 -->
        <section class="drawer__section">
          <h3 class="drawer__h">近 72 小时气象趋势</h3>
          <WeatherChart :points="weather.hourly.slice(0, 72)" :height="220" :show-legend="false" />
        </section>

        <!-- 农事记录时间线 -->
        <section class="drawer__section">
          <h3 class="drawer__h">农事记录</h3>
          <el-timeline v-if="timeline.length" class="drawer__timeline">
            <el-timeline-item
              v-for="(item, i) in timeline"
              :key="i"
              :timestamp="formatDateTime(item.time)"
              placement="top"
              :type="item.type"
            >
              {{ item.text }}
            </el-timeline-item>
          </el-timeline>
          <EmptyState v-else icon="DocumentDelete" title="暂无农事记录" description="灌溉、施肥、收获等操作会记录在这里" size="sm" />
        </section>
      </div>

      <!-- 底部固定操作 -->
      <footer class="drawer__foot">
        <el-button :icon="Pouring" :loading="acting === 'water'" @click="onAction('water')">灌溉</el-button>
        <el-button :icon="MagicStick" :loading="acting === 'fertilize'" @click="onAction('fertilize')">施肥</el-button>
        <el-button :icon="Crop" :loading="acting === 'harvest'" @click="onAction('harvest')">收获</el-button>
      </footer>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Pouring, MagicStick, Crop } from '@element-plus/icons-vue'
import SuitabilityBar from '@/components/SuitabilityBar.vue'
import WeatherChart from '@/components/WeatherChart.vue'
import EmptyState from '@/components/EmptyState.vue'
import CropGlyph from '@/components/CropGlyph.vue'
import GrowthCurve from '@/components/GrowthCurve.vue'
import { useWeatherStore } from '@/stores/weather'
import { useLocationStore } from '@/stores/location'
import { OPERATIONS, scoreDay } from '@/utils/suitability'
import { buildGrowthModel } from '@/utils/growth'
import { formatNumber, formatDate, formatDateTime } from '@/utils/format'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 经过 farm.fieldsWithMetrics 处理后的地块视图模型 */
  field: { type: Object, default: null }
})
const emit = defineEmits(['update:modelValue', 'action'])

const weather = useWeatherStore()
const location = useLocationStore()
const acting = ref('')

// 窄视口（含创空间预览 iframe）下也不铺满全屏，避免遮挡其余界面
const drawerSize = computed(() =>
  typeof window !== 'undefined' && window.innerWidth < 768
    ? Math.min(window.innerWidth - 24, 480) + 'px'
    : '480px'
)

const ops = computed(() => {
  const today = weather.daily7[0] || null
  return OPERATIONS.map((op) => {
    const r = scoreDay(op, today)
    return { op, score: r.score, reasons: r.reasons || [] }
  })
})

/** 作物生长曲线模型：理论发育 vs 实际长势（基于近 72h 气象推演） */
const growth = computed(() => (props.field ? buildGrowthModel(props.field, weather) : null))

const timeline = computed(() => {
  const actions = Array.isArray(props.field?.actions) ? props.field.actions : []
  return actions
    .slice()
    .sort((a, b) => new Date(b.time || 0) - new Date(a.time || 0))
    .slice(0, 20)
    .map((a) => ({
      time: a.time,
      text: a.action || a.text || '农事操作',
      type: /灌溉|水/.test(a.action || '') ? 'primary' : /肥/.test(a.action || '') ? 'warning' : 'success'
    }))
})

function onAction(type) {
  if (!props.field) return
  emit('action', type, props.field)
}
</script>

<style scoped>
.drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-5) var(--sp-5) var(--sp-3);
  border-bottom: 1px solid var(--border-light);
}
.drawer__title {
  margin: 0;
  font-size: var(--fs-h2);
  font-weight: 700;
  color: var(--text-title);
}
.drawer__sub {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: var(--sp-1) 0 0;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
.drawer__dot {
  color: var(--text-disabled);
}
.drawer__close {
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
.drawer__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
}
.drawer__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}
.drawer__h {
  margin: 0;
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  flex-wrap: wrap;
}
.drawer__h-note {
  font-size: var(--fs-caption);
  font-weight: 400;
  color: var(--text-disabled);
}
.drawer__hero {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}
.drawer__hero-glyph {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  background: var(--brand-50);
  color: var(--brand-600);
}
html.dark .drawer__hero-glyph {
  background: color-mix(in srgb, var(--brand-500) 16%, transparent);
}
.drawer__hero-info {
  flex: 1 1 auto;
  min-width: 0;
}
.drawer__facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}
.drawer__facts--inline {
  grid-template-columns: 1fr 1fr;
}
.drawer__growth-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--sp-2);
}
.drawer__gstat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-2) var(--sp-3);
  background: var(--bg-subtle);
  border-radius: var(--radius-sm);
}
.drawer__gstat-k {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}
.drawer__gstat-v {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--text-title);
}
.drawer__gstat-v.is-empty {
  color: var(--text-disabled);
}
.drawer__growth-basis {
  margin: var(--sp-2) 0 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-disabled);
}
.drawer__fact {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-3);
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
}
.drawer__fact-k {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}
.drawer__fact-v {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-title);
}
.drawer__suit {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}
.drawer__timeline {
  padding-left: var(--sp-2);
}
.drawer__foot {
  display: flex;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-5);
  border-top: 1px solid var(--border-light);
  background: var(--bg-card);
}
.drawer__foot .el-button {
  flex: 1 1 0;
}
</style>

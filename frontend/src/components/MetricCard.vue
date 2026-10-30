<template>
  <div class="metric-card card-hover" :class="{ 'metric-card--loading': loading }">
    <div class="metric-card__head">
      <span class="metric-card__icon" :style="{ color: toneColor, background: toneSoft }" aria-hidden="true">
        <el-icon :size="18"><component :is="icon" /></el-icon>
      </span>
      <span class="metric-card__label">{{ label }}</span>
    </div>

    <div class="metric-card__value">
      <template v-if="loading">
        <span class="metric-card__placeholder">--</span>
      </template>
      <template v-else>
        <span class="metric-card__number num">{{ displayValue }}</span>
        <span v-if="unit" class="metric-card__unit">{{ unit }}</span>
        <span v-if="trend && trend !== 'flat'" class="metric-card__trend" :class="`is-${trend}`" :aria-label="trendLabel">
          <el-icon :size="12">
            <component :is="trend === 'up' ? 'Top' : 'Bottom'" />
          </el-icon>
        </span>
      </template>
    </div>

    <p class="metric-card__hint">
      <template v-if="loading">加载中…</template>
      <template v-else>{{ hint || '--' }}</template>
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Element Plus 图标组件名 */
  icon: { type: String, default: 'Sunny' },
  /** 指标名 */
  label: { type: String, required: true },
  /** 主数值；null / undefined / 非数字时显示 '--' */
  value: { type: [Number, String], default: null },
  /** 单位 */
  unit: { type: String, default: '' },
  /** 数值保留小数位 */
  digits: { type: Number, default: 1 },
  /** 副描述 */
  hint: { type: String, default: '' },
  /** up | down | flat */
  trend: { type: String, default: 'flat' },
  /** brand | sky | gold | success | info | warning | orange | danger */
  tone: { type: String, default: 'brand' },
  /** 加载中：显示 '--' 与占位文案，绝不显示假数 */
  loading: { type: Boolean, default: false }
})

const TONE_VAR = {
  brand: '--brand-500',
  sky: '--sky-500',
  gold: '--gold-500',
  success: '--state-success',
  info: '--state-info',
  warning: '--state-warning',
  orange: '--state-orange',
  danger: '--state-danger'
}

const toneColor = computed(() => `var(${TONE_VAR[props.tone] || TONE_VAR.brand})`)

/** 同色 12% 底，直接用 color-mix 保持与主题同步（现代浏览器均支持） */
const toneSoft = computed(() => `color-mix(in srgb, ${toneColor.value} 12%, transparent)`)

const displayValue = computed(() => {
  const raw = props.value
  if (raw === null || raw === undefined || raw === '') return '--'
  const n = Number(raw)
  if (!Number.isFinite(n)) return String(raw)
  return n.toFixed(props.digits)
})

const trendLabel = computed(() => ({ up: '较昨日上升', down: '较昨日下降' }[props.trend] || ''))
</script>

<style scoped>
.metric-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-5);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-1);
}

.metric-card__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
}

.metric-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  border-radius: var(--radius-icon);
}

.metric-card__label {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-card__value {
  display: flex;
  align-items: baseline;
  gap: var(--sp-1);
  min-height: 40px;
}

.metric-card__number {
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
  font-size: var(--fs-display);
  line-height: var(--lh-display);
  font-weight: 700;
  color: var(--text-title);
  letter-spacing: -0.5px;
}

.metric-card__placeholder {
  font-family: var(--font-num);
  font-size: var(--fs-display);
  line-height: var(--lh-display);
  font-weight: 700;
  color: var(--text-disabled);
}

.metric-card__unit {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.metric-card__trend {
  display: inline-flex;
  align-items: center;
  margin-left: var(--sp-1);
  padding: 2px;
  border-radius: var(--radius-xs);
}

.metric-card__trend.is-up {
  color: var(--state-danger);
}

.metric-card__trend.is-down {
  color: var(--state-info);
}

.metric-card__hint {
  margin: 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .metric-card {
    padding: var(--sp-4);
  }

  .metric-card__number,
  .metric-card__placeholder {
    font-size: var(--fs-h1);
    line-height: var(--lh-h1);
  }
}
</style>

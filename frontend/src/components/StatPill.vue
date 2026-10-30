<template>
  <span class="stat-pill" :class="[`stat-pill--${size}`, { 'stat-pill--solid': solid }]" :style="pillStyle">
    <el-icon v-if="icon" :size="iconSize" class="stat-pill__icon"><component :is="icon" /></el-icon>
    <slot>{{ text }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 文本 */
  text: { type: String, default: '' },
  /** Element Plus 图标组件名 */
  icon: { type: String, default: '' },
  /** brand | sky | gold | success | info | warning | orange | danger | neutral */
  tone: { type: String, default: 'neutral' },
  /** sm | md */
  size: { type: String, default: 'sm' },
  /** 实心（深底反白） */
  solid: { type: Boolean, default: false }
})

const TONE_VAR = {
  brand: '--brand-500',
  sky: '--sky-500',
  gold: '--gold-500',
  success: '--state-success',
  info: '--state-info',
  warning: '--state-warning',
  orange: '--state-orange',
  danger: '--state-danger',
  neutral: '--text-secondary'
}

const iconSize = computed(() => (props.size === 'sm' ? 12 : 14))

const pillStyle = computed(() => {
  const color = `var(${TONE_VAR[props.tone] || TONE_VAR.neutral})`
  if (props.solid) {
    return { background: color, borderColor: color, color: 'var(--text-inverse)' }
  }
  return {
    color,
    background: `color-mix(in srgb, ${color} 12%, transparent)`,
    borderColor: `color-mix(in srgb, ${color} 30%, transparent)`
  }
})
</script>

<style scoped>
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  vertical-align: middle;
}

.stat-pill--sm {
  padding: 4px var(--sp-2);
  font-size: var(--fs-caption);
}

.stat-pill--md {
  padding: 6px var(--sp-3);
  font-size: var(--fs-sm);
}

.stat-pill__icon {
  flex: 0 0 auto;
}
</style>

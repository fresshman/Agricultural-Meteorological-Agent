<template>
  <span
    class="risk-badge"
    :class="[`risk-badge--${size}`, { 'risk-badge--plain': plain }]"
    :style="badgeStyle"
    :title="meta.label"
  >
    <el-icon v-if="showIcon" :size="iconSize" class="risk-badge__icon"><component :is="meta.icon" /></el-icon>
    <span>{{ label || meta.label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { riskBadgeStyle, riskMeta } from '@/utils/risk'

const props = defineProps({
  /** 风险等级：'高风险' / '橙色预警' / 'danger' 等，统一过 utils/risk.js */
  level: { type: String, default: '' },
  /** 自定义文案；缺省时用风险等级的标准中文名 */
  label: { type: String, default: '' },
  /** sm | md */
  size: { type: String, default: 'sm' },
  /** 是否展示图标（色卡不能仅靠颜色区分，建议开启） */
  showIcon: { type: Boolean, default: true },
  /** 无底色模式（仅文字着色，用于密集列表） */
  plain: { type: Boolean, default: false }
})

// 唯一来源：所有色值 / 图标 / 排序都来自 utils/risk.js，本组件不写任何色值分支
const meta = computed(() => riskMeta(props.level))

const iconSize = computed(() => (props.size === 'sm' ? 12 : 14))

const badgeStyle = computed(() => {
  if (props.plain) return { background: 'transparent', border: '1px solid transparent', color: meta.value.color }
  return riskBadgeStyle(props.level)
})
</script>

<style scoped>
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  border-radius: var(--radius-xs);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  vertical-align: middle;
}

.risk-badge--sm {
  padding: 4px var(--sp-2);
  font-size: var(--fs-caption);
}

.risk-badge--md {
  padding: 6px var(--sp-3);
  font-size: var(--fs-sm);
}

.risk-badge__icon {
  flex: 0 0 auto;
}
</style>

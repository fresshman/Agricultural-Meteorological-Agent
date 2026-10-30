<template>
  <div class="suit-bar" :class="{ 'suit-bar--compact': compact }">
    <div class="suit-bar__head">
      <span class="suit-bar__label">
        <el-icon v-if="icon" :size="14" class="suit-bar__icon"><component :is="icon" /></el-icon>
        {{ label }}
      </span>
      <span v-if="computable" class="suit-bar__value num" :style="{ color: meta.color }">
        {{ displayValue }}<span v-if="suffix" class="suit-bar__suffix">{{ suffix }}</span>
      </span>
      <span v-else class="suit-bar__na num">--</span>
    </div>
    <div class="suit-bar__track">
      <div
        class="suit-bar__fill"
        :class="{ 'suit-bar__fill--na': !computable }"
        :style="fillStyle"
      ></div>
    </div>
    <p v-if="hint && computable" class="suit-bar__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { suitabilityMeta } from '@/utils/risk'

const props = defineProps({
  label: { type: String, required: true },
  /** 0~100 的分值；null 表示不可算 */
  value: { type: Number, default: null },
  suffix: { type: String, default: '' },
  icon: { type: String, default: '' },
  /** 副描述（可解释性） */
  hint: { type: String, default: '' },
  /** 紧凑模式（用于抽屉内密集列表） */
  compact: { type: Boolean, default: false }
})

const computable = computed(() => Number.isFinite(Number(props.value)))
const meta = computed(() => suitabilityMeta(props.value))
const displayValue = computed(() => (computable.value ? Math.round(Number(props.value)) : '--'))

const fillStyle = computed(() => {
  if (!computable.value) return { width: '0%' }
  return { width: `${Math.max(4, Math.min(100, Number(props.value)))}%`, background: meta.value.color }
})
</script>

<style scoped>
.suit-bar {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.suit-bar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
}

.suit-bar__label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

.suit-bar__icon {
  color: var(--text-disabled);
}

.suit-bar__value {
  font-size: var(--fs-body);
  font-weight: 700;
}

.suit-bar__suffix {
  font-size: var(--fs-caption);
  font-weight: 500;
  margin-left: 1px;
}

.suit-bar__na {
  font-size: var(--fs-body);
  font-weight: 700;
  color: var(--text-disabled);
}

.suit-bar__track {
  position: relative;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  overflow: hidden;
}

.suit-bar__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: var(--radius-full);
  transition: width 0.4s var(--ease);
}

.suit-bar__fill--na {
  background: var(--border-light);
}

.suit-bar__hint {
  margin: 0;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

.suit-bar--compact .suit-bar__track {
  height: 6px;
}
</style>

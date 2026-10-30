<template>
  <div class="feedback-bar">
    <div class="feedback-bar__group" role="group" aria-label="答案反馈">
      <button
        v-for="item in ratings"
        :key="item.value"
        type="button"
        class="feedback-btn"
        :class="{ 'is-active': value === item.value }"
        :disabled="locked"
        :aria-label="item.label"
        :aria-pressed="value === item.value"
        @click="onPick(item.value)"
      >
        <el-icon :size="14"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </div>

    <div class="feedback-bar__actions">
      <span v-if="showAcceptance" class="feedback-bar__rate num" :title="`共 ${stats.total} 次反馈`">
        采纳率 {{ acceptanceText }}
      </span>
      <button type="button" class="feedback-btn feedback-btn--ghost" aria-label="复制答案" @click="emit('copy')">
        <el-icon :size="14"><CopyDocument /></el-icon>
        <span>复制</span>
      </button>
      <button
        type="button"
        class="feedback-btn feedback-btn--ghost"
        :disabled="disabledRegenerate"
        aria-label="重新生成答案"
        @click="emit('regenerate')"
      >
        <el-icon :size="14"><Refresh /></el-icon>
        <span>重新生成</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 当前已提交的反馈；null 表示未反馈 */
  value: { type: String, default: null },
  /** 流式中禁用交互 */
  streaming: { type: Boolean, default: false },
  /** 采纳率统计 */
  stats: { type: Object, default: () => ({}) },
  /** 是否展示采纳率（顶栏已有时可关掉） */
  showAcceptance: { type: Boolean, default: true }
})

const emit = defineEmits(['feedback', 'copy', 'regenerate'])

const ratings = [
  { value: 'accepted', label: '采纳', icon: 'CircleCheck' },
  { value: 'partial', label: '半采纳', icon: 'SemiSelect' },
  { value: 'rejected', label: '不采纳', icon: 'CircleClose' }
]

/** 已反馈或流式中锁定按钮态 */
const locked = computed(() => props.streaming || Boolean(props.value))

const disabledRegenerate = computed(() => props.streaming)

const acceptanceText = computed(() => {
  const rate = Number(props.stats?.acceptance_rate)
  if (!Number.isFinite(rate) || !props.stats?.total) return '--'
  return `${Math.round(rate > 1 ? rate : rate * 100)}%`
})

function onPick(rating) {
  if (locked.value) return
  emit('feedback', rating)
}
</script>

<style scoped>
.feedback-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
  margin-top: var(--sp-3);
  padding-top: var(--sp-3);
  border-top: 1px dashed var(--border-light);
}

.feedback-bar__group,
.feedback-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.feedback-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: var(--fs-caption);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.feedback-btn:hover:not(:disabled) {
  color: var(--brand-600);
  border-color: var(--brand-300);
  background: var(--brand-50);
}

.feedback-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.feedback-btn.is-active {
  color: var(--brand-600);
  border-color: var(--brand-500);
  background: var(--brand-50);
  font-weight: 600;
}

.feedback-btn--ghost {
  border-color: transparent;
  background: transparent;
}

.feedback-btn--ghost:hover:not(:disabled) {
  background: var(--bg-subtle);
  border-color: var(--border-light);
}

.feedback-bar__rate {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
  margin-right: var(--sp-1);
}

@media (max-width: 767px) {
  .feedback-bar {
    gap: var(--sp-2);
  }

  .feedback-bar__rate {
    width: 100%;
  }
}
</style>

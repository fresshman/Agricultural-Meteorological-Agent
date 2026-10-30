<template>
  <transition name="fade">
    <div v-if="isVisible" class="nowcast-banner" role="alert" aria-live="assertive">
      <span class="nowcast-banner__icon" aria-hidden="true">
        <el-icon :size="16"><Lightning /></el-icon>
      </span>
      <span class="nowcast-banner__label">临近突发</span>
      <span class="nowcast-banner__text">{{ text }}</span>
      <button
        v-if="closable"
        type="button"
        class="nowcast-banner__close"
        aria-label="关闭临近突发提示"
        @click="onClose"
      >
        <el-icon :size="14"><Close /></el-icon>
      </button>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  /** SSE nowcast 事件内容 */
  text: { type: String, default: '' },
  closable: { type: Boolean, default: false }
})

const emit = defineEmits(['close'])

/** 记录被关闭的内容；内容变化时重新出现 */
const dismissed = ref('')

const isVisible = computed(() => Boolean(props.text) && dismissed.value !== props.text)

watch(
  () => props.text,
  (next) => {
    if (next !== dismissed.value) dismissed.value = ''
  }
)

function onClose() {
  dismissed.value = props.text
  emit('close')
}
</script>

<style scoped>
.nowcast-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--state-warning) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--state-warning) 30%, transparent);
  color: var(--gold-700);
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
}

html.dark .nowcast-banner {
  color: var(--gold-500);
}

.nowcast-banner__icon {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  color: var(--state-warning);
}

.nowcast-banner__label {
  flex: 0 0 auto;
  font-weight: 600;
}

.nowcast-banner__text {
  flex: 1 1 auto;
  min-width: 0;
  color: var(--text-body);
}

.nowcast-banner__close {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
}

.nowcast-banner__close:hover {
  background: color-mix(in srgb, var(--text-disabled) 20%, transparent);
}
</style>

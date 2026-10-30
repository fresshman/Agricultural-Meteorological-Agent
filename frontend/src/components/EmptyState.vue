<template>
  <div class="empty-state" :class="`empty-state--${size}`" role="status" aria-live="polite">
    <div class="empty-state__icon" :style="{ '--icon-size': `${iconSize}px` }" aria-hidden="true">
      <el-icon :size="iconSize"><component :is="icon" /></el-icon>
    </div>
    <p class="empty-state__title">{{ title }}</p>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <div v-if="actionText || $slots.default" class="empty-state__actions">
      <el-button v-if="actionText" type="primary" :size="size === 'lg' ? 'default' : 'small'" @click="emit('action')">
        {{ actionText }}
      </el-button>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Element Plus 图标组件名 */
  icon: { type: String, default: 'Document' },
  /** 主文案 */
  title: { type: String, default: '暂无数据' },
  /** 副文案 */
  description: { type: String, default: '' },
  /** CTA 按钮文案；为空则不渲染按钮 */
  actionText: { type: String, default: '' },
  /** sm | md | lg：分别用于列表内、区块、整页 */
  size: { type: String, default: 'md' }
})

const emit = defineEmits(['action'])

const iconSize = computed(() => ({ sm: 28, md: 48, lg: 96 }[props.size] ?? 48))
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state--sm {
  padding: var(--sp-5) var(--sp-4);
  gap: var(--sp-2);
}

.empty-state--md {
  padding: var(--sp-8) var(--sp-5);
  gap: var(--sp-3);
}

.empty-state--lg {
  padding: var(--sp-10) var(--sp-6);
  gap: var(--sp-4);
}

.empty-state__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: calc(var(--icon-size, 48px) * 1.6);
  height: calc(var(--icon-size, 48px) * 1.6);
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  color: var(--text-disabled);
}

.empty-state__title {
  margin: 0;
  font-size: var(--fs-body-lg);
  font-weight: 500;
  color: var(--text-body);
}

.empty-state--lg .empty-state__title {
  font-size: var(--fs-h3);
  color: var(--text-title);
}

.empty-state__desc {
  margin: 0;
  max-width: 380px;
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
  color: var(--text-secondary);
}

.empty-state__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
}
</style>

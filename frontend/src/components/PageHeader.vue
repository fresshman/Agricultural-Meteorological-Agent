<template>
  <header class="page-header">
    <div class="page-header__main">
      <div v-if="icon" class="page-header__icon" aria-hidden="true">
        <el-icon :size="20"><component :is="icon" /></el-icon>
      </div>
      <div class="page-header__text">
        <h1 class="page-header__title">
          {{ title }}
          <slot name="badge" />
        </h1>
        <p v-if="subtitle || $slots.subtitle" class="page-header__subtitle">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup>
defineProps({
  /** 页面标题 */
  title: { type: String, required: true },
  /** 副描述 */
  subtitle: { type: String, default: '' },
  /** Element Plus 图标组件名 */
  icon: { type: String, default: '' }
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
  margin-bottom: var(--sp-6);
}

.page-header__main {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  min-width: 0;
}

.page-header__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  border-radius: var(--radius-icon);
  background: var(--brand-50);
  color: var(--brand-500);
}

.page-header__text {
  min-width: 0;
}

.page-header__title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0;
  font-size: var(--fs-h1);
  line-height: var(--lh-h1);
  font-weight: 600;
  color: var(--text-title);
}

.page-header__subtitle {
  margin: var(--sp-1) 0 0;
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
  color: var(--text-secondary);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

@media (max-width: 767px) {
  .page-header {
    margin-bottom: var(--sp-5);
  }

  .page-header__title {
    font-size: var(--fs-h2);
    line-height: var(--lh-h2);
  }

  .page-header__actions {
    width: 100%;
  }
}
</style>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="ltr"
    size="280px"
    :with-header="true"
    class="nav-drawer"
    @update:model-value="onUpdate"
  >
    <template #header>
      <div class="nav-drawer__brand">
        <span class="nav-drawer__mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path
              d="M12 3c3.6 2.4 5.4 5.2 5.4 8.1 0 3.3-2.4 5.9-5.4 5.9s-5.4-2.6-5.4-5.9C6.6 8.2 8.4 5.4 12 3Z"
              fill="currentColor"
              opacity="0.18"
            />
            <path d="M12 21V9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <span class="nav-drawer__title">农业气象智能体</span>
      </div>
    </template>

    <nav class="nav-drawer__list" aria-label="移动导航">
      <router-link
        v-for="item in NAV_ITEMS"
        :key="item.path"
        :to="item.path"
        class="nav-drawer__item"
        :class="{ 'is-active': isActive(item.path) }"
        @click="onUpdate(false)"
      >
        <el-icon :size="18"><component :is="item.icon" /></el-icon>
        <span>{{ item.title }}</span>
        <el-icon v-if="isActive(item.path)" :size="14" class="nav-drawer__check"><Check /></el-icon>
      </router-link>
    </nav>

    <template #footer>
      <div class="nav-drawer__footer">
        <span class="nav-drawer__hint">深色模式</span>
        <ThemeToggle />
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { NAV_ITEMS } from '@/router'
import ThemeToggle from '@/components/ThemeToggle.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const route = useRoute()

function onUpdate(value) {
  emit('update:modelValue', Boolean(value))
}

function isActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<style scoped>
.nav-drawer__brand {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.nav-drawer__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-icon);
  background: var(--brand-50);
  color: var(--brand-500);
}

.nav-drawer__title {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--text-title);
}

.nav-drawer__list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.nav-drawer__item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3);
  border-radius: var(--radius-md);
  font-size: var(--fs-body-lg);
  font-weight: 500;
  color: var(--text-body);
  transition: all var(--dur-fast) var(--ease);
}

.nav-drawer__item:hover {
  background: var(--bg-subtle);
}

.nav-drawer__item.is-active {
  background: var(--brand-50);
  color: var(--brand-600);
  font-weight: 600;
}

html.dark .nav-drawer__item.is-active {
  background: color-mix(in srgb, var(--brand-500) 14%, transparent);
}

.nav-drawer__check {
  margin-left: auto;
}

.nav-drawer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-drawer__hint {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
</style>

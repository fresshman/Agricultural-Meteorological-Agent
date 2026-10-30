<template>
  <nav class="tab-bar" aria-label="底部导航">
    <router-link
      v-for="item in NAV_ITEMS"
      :key="item.path"
      :to="item.path"
      class="tab-bar__item"
      :class="{ 'is-active': isActive(item.path) }"
    >
      <span class="tab-bar__icon">
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
      </span>
      <span class="tab-bar__label">{{ item.title }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { NAV_ITEMS } from '@/router'

const route = useRoute()

function isActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<style scoped>
.tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 90;
  display: none;
  align-items: stretch;
  height: var(--tabbar-h);
  padding-bottom: env(safe-area-inset-bottom, 0);
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-light);
}

.tab-bar__item {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--text-disabled);
  font-size: var(--fs-caption);
  transition: color var(--dur-fast) var(--ease);
}

.tab-bar__item.is-active {
  color: var(--brand-500);
}

.tab-bar__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
}

.tab-bar__label {
  font-weight: 500;
  line-height: 1;
}

/* 仅 <768px 展示底部 TabBar */
@media (max-width: 767px) {
  .tab-bar {
    display: flex;
  }
}
</style>

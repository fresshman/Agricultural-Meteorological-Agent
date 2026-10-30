<template>
  <div class="skeleton-card" :class="`skeleton-card--${variant}`" aria-busy="true" aria-live="polite">
    <!-- 卡片形态：标题 + 若干行文本 -->
    <template v-if="variant === 'card'">
      <div class="skeleton-line skeleton-line--title" :style="{ width: '42%' }"></div>
      <div v-for="i in rows" :key="`r${i}`" class="skeleton-line" :style="{ width: i === rows ? '62%' : '100%' }"></div>
    </template>

    <!-- 列表形态：头像 + 两行 -->
    <template v-else-if="variant === 'list'">
      <div v-for="i in rows" :key="`l${i}`" class="skeleton-row">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-row__body">
          <div class="skeleton-line skeleton-line--sm" style="width: 58%"></div>
          <div class="skeleton-line skeleton-line--sm" style="width: 34%"></div>
        </div>
      </div>
    </template>

    <!-- 图表形态：大块占位 -->
    <template v-else>
      <div class="skeleton-line skeleton-line--title" style="width: 30%"></div>
      <div class="skeleton-chart" :style="{ height: typeof height === 'number' ? `${height}px` : height }"></div>
    </template>
    <span class="skeleton-card__sr">加载中</span>
  </div>
</template>

<script setup>
defineProps({
  /** card | list | chart */
  variant: { type: String, default: 'card' },
  /** card/list 形态的行数 */
  rows: { type: Number, default: 3 },
  /** chart 形态高度，数字按 px 处理 */
  height: { type: [Number, String], default: 280 }
})
</script>

<style scoped>
.skeleton-card {
  width: 100%;
}

.skeleton-card--card,
.skeleton-card--chart {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-6);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-1);
}

.skeleton-card--list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.skeleton-line {
  height: 14px;
  border-radius: var(--radius-xs);
  background: linear-gradient(90deg, var(--bg-subtle) 25%, var(--border-light) 37%, var(--bg-subtle) 63%);
  background-size: 400% 100%;
  animation: skeleton-shimmer 1.4s ease infinite;
}

.skeleton-line--title {
  height: 20px;
}

.skeleton-line--sm {
  height: 12px;
}

.skeleton-avatar {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-icon);
  background: linear-gradient(90deg, var(--bg-subtle) 25%, var(--border-light) 37%, var(--bg-subtle) 63%);
  background-size: 400% 100%;
  animation: skeleton-shimmer 1.4s ease infinite;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.skeleton-row__body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.skeleton-chart {
  width: 100%;
  min-height: 160px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--bg-subtle) 25%, var(--border-light) 37%, var(--bg-subtle) 63%);
  background-size: 400% 100%;
  animation: skeleton-shimmer 1.4s ease infinite;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}

/* 供读屏软件识别，视觉上隐藏 */
.skeleton-card__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-line,
  .skeleton-avatar,
  .skeleton-chart {
    animation: none;
  }
}
</style>

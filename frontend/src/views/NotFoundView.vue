<template>
  <div class="page-container not-found">
    <div class="card not-found__card">
      <div class="not-found__art" aria-hidden="true">
        <span class="not-found__num num">404</span>
        <span class="not-found__leaf">
          <el-icon :size="34"><Grape /></el-icon>
        </span>
      </div>
      <h1 class="not-found__title">这片地里没有你要找的页面</h1>
      <p class="not-found__desc">
        地址可能已变更或输入有误。你可以回到总览，或直接去问问智能体今天的农事安排。
      </p>
      <div class="not-found__actions">
        <el-button type="primary" size="large" @click="router.push('/dashboard')">
          <el-icon><Odometer /></el-icon>
          <span>回到总览</span>
        </el-button>
        <el-button size="large" @click="router.push('/chat')">
          <el-icon><ChatDotRound /></el-icon>
          <span>去提问</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100dvh - var(--header-h) - var(--sp-10));
}

.not-found__card {
  width: 100%;
  max-width: 520px;
  padding: var(--sp-9) var(--sp-7);
  text-align: center;
}

.not-found__art {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 128px;
  height: 128px;
  margin-bottom: var(--sp-4);
  border-radius: var(--radius-full);
  background: var(--brand-50);
  color: var(--brand-500);
}

.not-found__num {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -1px;
}

.not-found__leaf {
  position: absolute;
  right: -6px;
  bottom: -6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-2);
  color: var(--brand-500);
}

.not-found__title {
  margin: 0 0 var(--sp-2);
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  font-weight: 600;
  color: var(--text-title);
}

.not-found__desc {
  margin: 0 auto var(--sp-6);
  max-width: 380px;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--text-secondary);
}

.not-found__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

@media (max-width: 767px) {
  .not-found__card {
    padding: var(--sp-7) var(--sp-5);
  }
}
</style>

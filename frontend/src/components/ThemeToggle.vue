<template>
  <el-dropdown trigger="click" placement="bottom-end" @command="onCommand">
    <button class="theme-toggle" :aria-label="`主题模式：${current.label}，点击切换`" type="button">
      <el-icon :size="18"><component :is="current.icon" /></el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in options"
          :key="item.value"
          :command="item.value"
          :disabled="item.value === theme.mode"
        >
          <span class="theme-option">
            <el-icon :size="16"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
            <el-icon v-if="item.value === theme.mode" :size="14" class="theme-option__check">
              <Check />
            </el-icon>
          </span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

const options = [
  { value: 'light', label: '浅色', icon: 'Sunny' },
  { value: 'dark', label: '深色', icon: 'Moon' },
  { value: 'auto', label: '跟随系统', icon: 'Monitor' }
]

const current = computed(() => options.find((o) => o.value === theme.mode) || options[2])

function onCommand(value) {
  theme.setMode(value)
}
</script>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.theme-toggle:hover {
  color: var(--brand-500);
  border-color: var(--brand-300);
  background: var(--brand-50);
}

.theme-option {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 104px;
}

.theme-option__check {
  margin-left: auto;
  color: var(--brand-500);
}
</style>

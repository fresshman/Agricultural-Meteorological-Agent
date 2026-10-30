<template>
  <div class="matrix">
    <div class="matrix__scroll" :class="{ 'matrix__scroll--unavailable': unavailable }">
      <table class="matrix__table">
        <thead>
          <tr>
            <th class="matrix__corner">农事操作</th>
            <th v-for="(day, i) in days" :key="`h${i}`" class="matrix__day">
              <span class="matrix__day-label">{{ day.shortLabel || day.label }}</span>
              <span class="matrix__day-rel">{{ day.label }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.op">
            <th class="matrix__op" scope="row">
              <el-icon class="matrix__op-icon"><component :is="row.icon" /></el-icon>
              <span class="matrix__op-name">{{ row.op }}</span>
            </th>
            <td
              v-for="(cell, i) in row.cells"
              :key="`c${i}`"
              class="matrix__cell"
              :style="cellStyle(cell)"
              :class="{ 'is-na': cell.score === null }"
              role="button"
              tabindex="0"
              @click="emit('cell', { op: row.op, dayIndex: i, day: days[i], cell })"
              @keydown.enter="emit('cell', { op: row.op, dayIndex: i, day: days[i], cell })"
            >
              <span v-if="cell.score !== null" class="matrix__score num">{{ cell.score }}</span>
              <span v-else class="matrix__na num">--</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="unavailable" class="matrix__empty">
        <el-icon :size="20"><WarningFilled /></el-icon>
        <span>气象数据不可用，无法推演适宜度</span>
        <el-button size="small" type="primary" plain @click="emit('retry')">重试</el-button>
      </div>
    </div>

    <!-- 图例 -->
    <div class="matrix__legend">
      <span v-for="item in legend" :key="item.level" class="matrix__legend-item">
        <i class="matrix__legend-dot" :style="{ background: item.color }"></i>
        {{ item.label }}（{{ item.range }}）
      </span>
      <span class="matrix__legend-note">分值由前端依据气象规则推演，仅供参考</span>
    </div>
  </div>
</template>

<script setup>
import { suitabilityMeta, suitabilityLegend } from '@/utils/risk'

const props = defineProps({
  /** buildWeekMatrix 返回的 rows */
  rows: { type: Array, default: () => [] },
  /** 按日聚合后的气象 */
  days: { type: Array, default: () => [] },
  /** 气象不可用 */
  unavailable: { type: Boolean, default: false },
  /** 加载中 */
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['cell', 'retry'])

const legend = suitabilityLegend()

function cellStyle(cell) {
  if (cell.score === null) {
    return { background: 'var(--bg-subtle)', color: 'var(--text-disabled)', borderColor: 'var(--border-light)' }
  }
  const meta = suitabilityMeta(cell.score)
  return {
    background: `color-mix(in srgb, ${meta.color} 16%, transparent)`,
    borderColor: `color-mix(in srgb, ${meta.color} 42%, transparent)`,
    color: meta.color
  }
}
</script>

<style scoped>
.matrix__scroll {
  overflow-x: auto;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.matrix__table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
  min-width: 560px;
  table-layout: fixed;
}

.matrix__corner,
.matrix__op {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--bg-subtle);
  text-align: left;
  font-weight: 600;
  color: var(--text-title);
  min-width: 96px;
  width: 96px;
}

.matrix__corner {
  top: 0;
  z-index: 3;
}

.matrix__day {
  padding: var(--sp-2);
  text-align: center;
  font-size: var(--fs-caption);
  color: var(--text-secondary);
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border-light);
}

.matrix__day-label {
  display: block;
  font-weight: 600;
  color: var(--text-title);
}

.matrix__day-rel {
  display: block;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

.matrix__op {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-3);
  border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}

.matrix__op-icon {
  color: var(--brand-500);
}

.matrix__cell {
  height: 52px;
  text-align: center;
  vertical-align: middle;
  border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: transform var(--dur-fast) var(--ease);
}

.matrix__cell:hover {
  transform: scale(1.04);
  box-shadow: inset 0 0 0 2px var(--brand-300);
}

.matrix__score {
  font-size: var(--fs-h3);
  font-weight: 700;
}

.matrix__na {
  font-size: var(--fs-body);
  color: var(--text-disabled);
}

.matrix__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  padding: var(--sp-8);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.matrix__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-4);
  margin-top: var(--sp-3);
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.matrix__legend-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
}

.matrix__legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

.matrix__legend-note {
  margin-left: auto;
  color: var(--text-disabled);
}
</style>

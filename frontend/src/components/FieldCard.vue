<template>
  <article class="field-card card-hover">
    <header class="field-card__head">
      <div class="field-card__id">
        <div class="field-card__crop-glyph">
          <CropGlyph :crop="field.crop" :size="38" />
        </div>
        <div class="field-card__title-wrap">
          <h3 class="field-card__name truncate">{{ field.name || '未命名地块' }}</h3>
          <p class="field-card__meta">
            <span class="field-card__crop">{{ field.crop || '作物未设' }}</span>
            <span class="field-card__dot">·</span>
            <span>{{ field.stage || '阶段未设' }}</span>
            <span class="field-card__dot">·</span>
            <span class="num">{{ formatNumber(field.area, 1) }} 亩</span>
          </p>
        </div>
      </div>

      <div class="field-card__head-right">
        <RiskBadge :level="statusLabel.level" :label="statusLabel.label" size="sm" />
        <!-- ⓘ 算法与数据依据 -->
        <el-popover placement="top" :width="280" trigger="hover" :show-after="120">
          <template #reference>
            <button type="button" class="field-card__info" aria-label="查看指标计算依据">
              <el-icon :size="15"><InfoFilled /></el-icon>
            </button>
          </template>
          <div class="field-card__pop">
            <p class="field-card__pop-title">指标计算依据</p>
            <p class="field-card__pop-text">
              健康 / 水分 / 生长三项指标由 <b>近 72 小时真实气象</b>（累计降水、日均温、相对湿度、高温≥32℃ 与高湿≥85% 时数）结合
              <b>最近灌溉时间</b>联动推演，<b>非后端写死值</b>。
            </p>
            <p class="field-card__pop-basis">
              {{ field.metrics?.basis || '气象数据不足，暂无法推演。' }}
            </p>
          </div>
        </el-popover>
      </div>
    </header>

    <div class="field-card__metrics">
      <SuitabilityBar label="健康" :value="field.metrics?.health" icon="FirstAidKit" hint="综合高温/高湿胁迫" />
      <SuitabilityBar label="水分" :value="field.metrics?.water" icon="Pouring" hint="失墒与灌溉补给平衡" />
      <SuitabilityBar label="生长" :value="field.metrics?.growth" icon="Sunny" hint="积温与水分协同" />
    </div>

    <p class="field-card__advice" :class="{ 'is-empty': !field.advice }">
      <el-icon class="field-card__advice-icon"><ChatLineSquare /></el-icon>
      <span>{{ field.advice || '气象数据不足，暂无法给出建议' }}</span>
    </p>

    <footer class="field-card__actions">
      <el-button size="small" :icon="Pouring" @click="emit('action', 'water', field)">灌溉</el-button>
      <el-button size="small" :icon="MagicStick" @click="emit('action', 'fertilize', field)">施肥</el-button>
      <el-button size="small" :icon="Crop" @click="emit('action', 'harvest', field)">收获</el-button>
      <span class="field-card__spacer"></span>
      <el-button size="small" text :icon="View" @click="emit('action', 'detail', field)">详情</el-button>
      <el-button size="small" text type="danger" :icon="Delete" @click="emit('action', 'remove', field)">删除</el-button>
    </footer>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { Pouring, MagicStick, Crop, View, Delete, FirstAidKit } from '@element-plus/icons-vue'
import SuitabilityBar from '@/components/SuitabilityBar.vue'
import RiskBadge from '@/components/RiskBadge.vue'
import CropGlyph from '@/components/CropGlyph.vue'
import { formatNumber } from '@/utils/format'

const props = defineProps({
  /** 经过 farm.fieldsWithMetrics 处理后的地块视图模型 */
  field: { type: Object, required: true },
  /** 状态等级：good / warn / risk / unknown */
  status: { type: String, default: 'unknown' }
})
const emit = defineEmits(['action'])

const STATUS_MAP = {
  good: { level: 'success', label: '状态良好' },
  warn: { level: 'warning', label: '需关注' },
  risk: { level: 'danger', label: '风险' },
  unknown: { level: 'info', label: '暂无数据' }
}
const statusLabel = computed(() => STATUS_MAP[props.status] || STATUS_MAP.unknown)
</script>

<style scoped>
.field-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-5);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-1);
}

.field-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-2);
}

.field-card__id {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}

.field-card__crop-glyph {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-md);
  background: var(--brand-50);
  color: var(--brand-600);
}

html.dark .field-card__crop-glyph {
  background: color-mix(in srgb, var(--brand-500) 16%, transparent);
}

.field-card__title-wrap {
  min-width: 0;
}

.field-card__name {
  margin: 0;
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}

.field-card__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: var(--sp-1) 0 0;
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.field-card__crop {
  color: var(--brand-600);
  font-weight: 500;
}

.field-card__dot {
  color: var(--text-disabled);
}

.field-card__head-right {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 0 0 auto;
}

.field-card__info {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.field-card__info:hover {
  color: var(--brand-600);
  border-color: var(--brand-300);
  background: var(--brand-50);
}

.field-card__metrics {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.field-card__advice {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
  color: var(--text-body);
}

.field-card__advice.is-empty {
  color: var(--text-disabled);
}

.field-card__advice-icon {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--brand-500);
}

.field-card__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.field-card__spacer {
  flex: 1 1 auto;
}

.field-card__pop-title {
  margin: 0 0 var(--sp-2);
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-title);
}

.field-card__pop-text {
  margin: 0 0 var(--sp-2);
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-body);
}

.field-card__pop-basis {
  margin: 0;
  padding-top: var(--sp-2);
  border-top: 1px dashed var(--border-light);
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-secondary);
}
</style>

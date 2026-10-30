<template>
  <div v-if="hasAny" class="meta-panel">
    <el-collapse v-model="activeNames" class="meta-panel__collapse">
      <!-- 依据 -->
      <el-collapse-item v-if="evidenceList.length" name="evidence">
        <template #title>
          <span class="meta-panel__title">
            <el-icon :size="14"><Files /></el-icon>
            <span>依据（{{ evidenceList.length }}）</span>
          </span>
        </template>
        <ol class="meta-panel__evidence">
          <li v-for="(item, idx) in evidenceList" :key="`ev${idx}`">{{ item }}</li>
        </ol>
      </el-collapse-item>

      <!-- 置信度 -->
      <el-collapse-item v-if="hasConfidence" name="confidence">
        <template #title>
          <span class="meta-panel__title">
            <el-icon :size="14"><DataLine /></el-icon>
            <span>置信度</span>
            <span class="meta-panel__value num">{{ confidencePercent }}%</span>
            <span class="meta-panel__tag" :style="{ color: confidenceColor }">{{ confidenceLabel }}</span>
          </span>
        </template>
        <div class="meta-panel__progress">
          <el-progress
            :percentage="confidencePercent"
            :stroke-width="8"
            :color="confidenceColor"
            :show-text="false"
          />
          <p class="meta-panel__note">
            置信度由模型依据气象数据完整性与知识库命中情况综合给出，仅供参考。
          </p>
        </div>
      </el-collapse-item>

      <!-- 合规提示 -->
      <el-collapse-item v-if="compliance" name="compliance">
        <template #title>
          <span class="meta-panel__title">
            <el-icon :size="14"><WarningFilled /></el-icon>
            <span>合规提示</span>
            <span v-if="compliance.advice_level" class="meta-panel__tag">{{ compliance.advice_level }}</span>
          </span>
        </template>
        <div class="meta-panel__compliance">
          <p v-if="compliance.disclaimer" class="meta-panel__note">{{ compliance.disclaimer }}</p>
          <ul v-if="regulatoryNotes.length" class="meta-panel__notes">
            <li v-for="(note, idx) in regulatoryNotes" :key="`rn${idx}`">{{ note }}</li>
          </ul>
          <p v-if="compliance.requires_local_consultation" class="meta-panel__alert">
            需向当地农技推广部门咨询确认后执行。
          </p>
        </div>
      </el-collapse-item>

      <!-- 不确定性 -->
      <el-collapse-item v-if="uncertainty" name="uncertainty">
        <template #title>
          <span class="meta-panel__title">
            <el-icon :size="14"><QuestionFilled /></el-icon>
            <span>不确定性</span>
            <span v-if="uncertainty.level" class="meta-panel__tag">{{ uncertainty.level }}</span>
          </span>
        </template>
        <p class="meta-panel__note">
          {{ uncertaintyText }}
        </p>
      </el-collapse-item>

      <!-- 风险提示（灾害 / 病虫害） -->
      <el-collapse-item v-if="risks.length" name="risks">
        <template #title>
          <span class="meta-panel__title">
            <el-icon :size="14"><WarnTriangleFilled /></el-icon>
            <span>风险提示（{{ risks.length }}）</span>
          </span>
        </template>
        <div class="meta-panel__risks">
          <div v-for="(risk, idx) in risks" :key="`rk${idx}`" class="meta-panel__risk">
            <RiskBadge :level="risk.level" :label="risk.level" size="sm" />
            <span class="meta-panel__risk-name">{{ risk.name }}</span>
            <span v-if="risk.detail" class="meta-panel__risk-detail">{{ risk.detail }}</span>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import RiskBadge from '@/components/RiskBadge.vue'
import { suitabilityMeta } from '@/utils/risk'

const props = defineProps({
  /** 后端 AnswerMeta（done 事件携带） */
  meta: { type: Object, default: null },
  /** 是否默认展开（桌面端可开启） */
  defaultOpen: { type: Boolean, default: false }
})

// 默认折叠：仅在有内容时渲染对应区块
const activeNames = ref(props.defaultOpen ? ['confidence'] : [])

watch(
  () => props.defaultOpen,
  (open) => {
    activeNames.value = open ? ['confidence'] : []
  }
)

const evidenceList = computed(() => {
  const raw = props.meta?.evidence
  if (!raw) return []
  const text = typeof raw === 'string' ? raw : String(raw)
  return text
    .split(/\r?\n+/)
    .map((line) => line.replace(/^\s*(?:\d+[.、)]|[•·\-*])\s*/, '').trim())
    .filter(Boolean)
    .slice(0, 12)
})

const confidence = computed(() => {
  const v = Number(props.meta?.confidence)
  return Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : null
})

const confidencePercent = computed(() => Math.round((confidence.value ?? 0) * 100))

/** 置信度沿用唯一的适宜度分档口径：≥75 高 / ≥50 中 / ≥25 低 / 否则 很低 */
const confidenceMeta = computed(() => suitabilityMeta(confidencePercent.value))

const confidenceColor = computed(() => confidenceMeta.value.color)

const confidenceLabel = computed(() => {
  const p = confidencePercent.value
  if (p >= 75) return '高'
  if (p >= 50) return '中'
  if (p >= 25) return '偏低'
  return '低'
})

const compliance = computed(() => {
  const c = props.meta?.compliance
  if (!c || typeof c !== 'object') return null
  if (!c.advice_level && !c.disclaimer && !c.regulatory_notes?.length && !c.requires_local_consultation) {
    return null
  }
  return c
})

const regulatoryNotes = computed(() => {
  const notes = compliance.value?.regulatory_notes
  return Array.isArray(notes) ? notes.filter(Boolean) : []
})

const uncertainty = computed(() => {
  const u = props.meta?.uncertainty
  if (!u || typeof u !== 'object') return null
  if (!u.level && !Number.isFinite(Number(u.confidence_score))) return null
  return u
})

const uncertaintyText = computed(() => {
  const u = uncertainty.value
  const parts = []
  if (u?.level) parts.push(`不确定性等级：${u.level}`)
  if (Number.isFinite(Number(u?.confidence_score))) {
    parts.push(`评估得分 ${Number(u.confidence_score).toFixed(2)}`)
  }
  parts.push('气象预报随时效衰减，临近执行前请复核最新预警。')
  return parts.join('；')
})

const risks = computed(() => {
  const out = []
  const disasters = Array.isArray(props.meta?.disaster_warnings) ? props.meta.disaster_warnings : []
  const diseases = Array.isArray(props.meta?.disease_risks) ? props.meta.disease_risks : []
  for (const item of disasters) {
    out.push({
      name: item?.disaster_type || '气象灾害',
      level: item?.risk_level || '低风险',
      detail: item?.time_window || item?.description || ''
    })
  }
  for (const item of diseases) {
    out.push({
      name: item?.disease_name || '病虫害风险',
      level: item?.risk_level || '低风险',
      detail: item?.time_window || item?.description || ''
    })
  }
  return out
})

const hasConfidence = computed(() => confidence.value !== null)

const hasAny = computed(
  () =>
    evidenceList.value.length > 0 ||
    hasConfidence.value ||
    Boolean(compliance.value) ||
    Boolean(uncertainty.value) ||
    risks.value.length > 0
)
</script>

<style scoped>
.meta-panel {
  margin-top: var(--sp-3);
  border-top: 1px solid var(--border-light);
}

.meta-panel__collapse {
  border: 0;
}

.meta-panel__collapse :deep(.el-collapse-item__header) {
  height: 40px;
  line-height: 40px;
  font-size: var(--fs-sm);
}

.meta-panel__title {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  color: var(--text-body);
}

.meta-panel__value {
  font-weight: 600;
  color: var(--text-title);
}

.meta-panel__tag {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.meta-panel__evidence {
  margin: 0;
  padding-left: 1.4em;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
  color: var(--text-secondary);
}

.meta-panel__progress {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.meta-panel__note {
  margin: 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-secondary);
}

.meta-panel__compliance {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.meta-panel__notes {
  margin: 0;
  padding-left: 1.4em;
  font-size: var(--fs-caption);
  line-height: var(--lh-caption);
  color: var(--text-secondary);
}

.meta-panel__alert {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-md);
  font-size: var(--fs-caption);
  background: color-mix(in srgb, var(--state-warning) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--state-warning) 30%, transparent);
  color: var(--state-warning);
}

.meta-panel__risks {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.meta-panel__risk {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
  font-size: var(--fs-sm);
}

.meta-panel__risk-name {
  font-weight: 500;
  color: var(--text-title);
}

.meta-panel__risk-detail {
  color: var(--text-secondary);
  font-size: var(--fs-caption);
}
</style>

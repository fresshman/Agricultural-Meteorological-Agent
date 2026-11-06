<template>
  <div class="farm">
    <PageHeader title="我的农场" subtitle="地块指标由近 72 小时气象实时推演，无数据时显示「--」而非估算值">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建地块</el-button>
      </template>
    </PageHeader>

    <!-- 筛选与排序 -->
    <div class="farm__filters card">
      <el-select v-model="cropFilter" placeholder="全部作物" clearable size="default" class="farm__filter">
        <el-option v-for="c in cropOptions" :key="c" :label="c" :value="c" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="全部状态" clearable size="default" class="farm__filter">
        <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="sortKey" size="default" class="farm__filter">
        <el-option label="默认排序" value="default" />
        <el-option label="健康度 ↑" value="health" />
        <el-option label="健康度 ↓" value="health-desc" />
      </el-select>
      <span class="farm__count num">{{ filtered.length }} 块地块</span>
    </div>

    <!-- 加载骨架 -->
    <div v-if="farm.loading && !farm.fields.length" class="farm__grid farm__grid--skeleton">
      <SkeletonCard v-for="i in 4" :key="i" variant="card" :rows="3" />
    </div>

    <!-- 空列表 -->
    <EmptyState
      v-else-if="!filtered.length"
      icon="Grape"
      :title="farm.fields.length ? '没有符合条件的地块' : '还没有地块'"
      :description="farm.fields.length ? '试着调整筛选条件' : '点击下方「新建地块」开始管理你的农田'"
      size="lg"
    >
      <template v-if="!farm.fields.length" #extra>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建第一块地</el-button>
      </template>
    </EmptyState>

    <!-- 卡片网格 -->
    <el-row v-else :gutter="16" class="farm__grid">
      <el-col v-for="f in filtered" :key="f.field_id" :xs="24" :sm="12" :md="12" :lg="8">
        <FieldCard
          class="farm__cell"
          :field="f"
          :status="farm.fieldStatus(f)"
          :harvest="burstId === f.field_id"
          @action="onAction"
        />
      </el-col>
    </el-row>

    <!-- 详情抽屉 -->
    <FieldDetailDrawer
      v-model="drawerOpen"
      :field="activeField"
      :harvesting="burstId === activeField?.field_id"
      @action="onAction"
    />

    <!-- 新建地块弹窗 -->
    <el-dialog v-model="createOpen" title="新建地块" width="420px" align-center>
      <el-form :model="form" label-width="80px">
        <el-form-item label="地块名称" required>
          <el-input v-model="form.name" placeholder="如：东区一号田" maxlength="20" />
        </el-form-item>
        <el-form-item label="作物">
          <el-select v-model="form.crop" class="farm__full" @change="onCropChange">
            <el-option v-for="c in CROP_TYPES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="生育阶段">
          <el-select v-model="form.stage" class="farm__full">
            <el-option v-for="s in stageOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="播种日期">
          <el-date-picker
            v-model="form.planted_at"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="isFutureDate"
            :clearable="false"
            placeholder="默认今天"
            class="farm__full"
            @change="onPlantedChange"
          />
        </el-form-item>
        <el-form-item label="面积(亩)">
          <el-input-number v-model="form.area" :min="0.1" :step="0.5" :precision="1" class="farm__full" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import FieldCard from '@/components/FieldCard.vue'
import FieldDetailDrawer from '@/components/FieldDetailDrawer.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useFarmStore } from '@/stores/farm'
import { useWeatherStore } from '@/stores/weather'
import { CROP_TYPES, getCropStages } from '@/utils/crops'
import { stageForDate } from '@/utils/growth'

const router = useRouter()
const farm = useFarmStore()
const weather = useWeatherStore()

const STATUS_OPTIONS = [
  { value: 'good', label: '状态良好' },
  { value: 'warn', label: '需关注' },
  { value: 'risk', label: '风险' },
  { value: 'unknown', label: '暂无数据' }
]

const cropFilter = ref('')
const statusFilter = ref('')
const sortKey = ref('default')

const cropOptions = computed(() => {
  const set = new Set(farm.fields.map((f) => f.crop).filter(Boolean))
  return [...set]
})

const filtered = computed(() => {
  let list = farm.fieldsWithMetrics.slice()
  if (cropFilter.value) list = list.filter((f) => f.crop === cropFilter.value)
  if (statusFilter.value) list = list.filter((f) => farm.fieldStatus(f) === statusFilter.value)
  if (sortKey.value === 'health') {
    list = list.slice().sort((a, b) => (a.metrics?.health ?? -1) - (b.metrics?.health ?? -1))
  } else if (sortKey.value === 'health-desc') {
    list = list.slice().sort((a, b) => (b.metrics?.health ?? -1) - (a.metrics?.health ?? -1))
  }
  return list
})

// ---------------------------------------------------------------- 详情抽屉
const drawerOpen = ref(false)
const activeField = ref(null)

function openDetail(field) {
  activeField.value = field
  drawerOpen.value = true
}

// ---------------------------------------------------------------- 操作
/** 收获成功的迸发动画：只点亮对应地块 1 秒，之后复位，重复操作还能再触发 */
const burstId = ref('')
let burstTimer = null
let burstStart = null
function triggerBurst(fieldId) {
  // 先清空再下一拍赋值：连点同一地块时 watch 仍能收到 false→true；
  // 不用 requestAnimationFrame——后台/隐藏标签页里 rAF 会被挂起，动画就永远不触发
  burstId.value = ''
  clearTimeout(burstTimer)
  clearTimeout(burstStart)
  burstStart = setTimeout(() => {
    burstId.value = fieldId
  }, 0)
  burstTimer = setTimeout(() => {
    burstId.value = ''
  }, 1100)
}

async function onAction(type, field) {
  if (type === 'detail') {
    openDetail(field)
    return
  }
  if (type === 'remove') {
    try {
      await ElMessageBox.confirm(`确定删除地块「${field.name || '未命名'}」？`, '删除地块', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      })
    } catch (err) {
      return
    }
    await farm.deleteField(field.field_id)
    ElMessage.success('地块已删除')
    return
  }
  // water / fertilize / harvest
  const map = { water: '灌溉', fertilize: '施肥', harvest: '收获' }
  try {
    await farm.doAction(field.field_id, type)
    ElMessage.success(`${map[type] || '操作'}成功`)
    if (type === 'harvest') triggerBurst(field.field_id)
    if (activeField.value?.field_id === field.field_id) {
      activeField.value = farm.fieldsWithMetrics.find((f) => f.field_id === field.field_id) || null
    }
  } catch (err) {
    ElMessage.error(err?.message || '操作失败')
  }
}

// ---------------------------------------------------------------- 新建
const createOpen = ref(false)
const creating = ref(false)
const form = ref({ name: '', crop: '玉米', stage: '播种期', area: 1.0, planted_at: todayStr() })
/** 阶段选项随作物变化（与后端 CROP_CONFIG 的阶段序列一致） */
const stageOptions = computed(() => getCropStages(form.value.crop))

/** 本地日期 YYYY-MM-DD（不用 toISOString，避免时区把日期推到前一天） */
function todayStr() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function isFutureDate(d) {
  const end = new Date()
  end.setHours(23, 59, 59, 999)
  return d.getTime() > end.getTime()
}

/** 换作物后旧阶段可能不存在，按播种日期重新对齐一次 */
function onCropChange() {
  onPlantedChange(form.value.planted_at)
}
/** 播种日期变化 → 阶段跟着走，避免日期与阶段互相矛盾 */
function onPlantedChange(value) {
  const s = stageForDate(form.value.crop, value)
  if (s) form.value.stage = s
}

function openCreate() {
  form.value = { name: '', crop: '玉米', stage: '播种期', area: 1.0, planted_at: todayStr() }
  createOpen.value = true
}
async function submitCreate() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请填写地块名称')
    return
  }
  if (!stageOptions.value.includes(form.value.stage)) {
    ElMessage.warning('请选择该作物对应的生育阶段')
    return
  }
  creating.value = true
  try {
    await farm.createField({
      name: form.value.name.trim(),
      crop: form.value.crop,
      stage: form.value.stage,
      area: Number(form.value.area) || 1.0,
      planted_at: form.value.planted_at || todayStr()
    })
    ElMessage.success('地块创建成功')
    createOpen.value = false
  } catch (err) {
    ElMessage.error(err?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  if (!farm.fields.length) {
    try {
      await farm.loadFields()
    } catch (err) {
      ElMessage.error(err?.message || '地块加载失败，请稍后重试')
    }
  }
  if (!weather.available && !weather.loading) weather.loadWeather(168)
})

onBeforeUnmount(() => {
  clearTimeout(burstTimer)
  clearTimeout(burstStart)
})
</script>

<style scoped>
.farm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--sp-5) var(--sp-6);
}

.farm__filters {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  flex-wrap: wrap;
}

.farm__filter {
  width: 150px;
}

.farm__count {
  margin-left: auto;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

.farm__grid--skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--sp-4);
}

.farm__cell {
  width: 100%;
  height: 100%;
}

.farm__full {
  width: 100%;
}

@media (max-width: 767px) {
  .farm {
    padding: var(--sp-4) var(--gutter-mobile);
  }
  .farm__filter {
    flex: 1 1 100%;
    width: 100%;
  }
  .farm__count {
    margin-left: 0;
  }
}
</style>

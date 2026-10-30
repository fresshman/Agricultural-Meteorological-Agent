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
    <div v-if="farm.loading && !farm.fields.length" class="farm__grid">
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
      <el-col v-for="f in filtered" :key="f.field_id" :xs="24" :sm="12" :md="8" :lg="6">
        <FieldCard
          class="farm__cell"
          :field="f"
          :status="farm.fieldStatus(f)"
          @action="onAction"
        />
      </el-col>
    </el-row>

    <!-- 详情抽屉 -->
    <FieldDetailDrawer v-model="drawerOpen" :field="activeField" @action="onAction" />

    <!-- 新建地块弹窗 -->
    <el-dialog v-model="createOpen" title="新建地块" width="420px" align-center>
      <el-form :model="form" label-width="80px">
        <el-form-item label="地块名称" required>
          <el-input v-model="form.name" placeholder="如：东区一号田" maxlength="20" />
        </el-form-item>
        <el-form-item label="作物">
          <el-select v-model="form.crop" class="farm__full">
            <el-option v-for="c in CROP_TYPES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="生育阶段">
          <el-select v-model="form.stage" class="farm__full">
            <el-option v-for="s in STAGES" :key="s" :label="s" :value="s" />
          </el-select>
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
import { computed, onMounted, ref } from 'vue'
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
import { CROP_TYPES } from '@/utils/crops'

const router = useRouter()
const farm = useFarmStore()
const weather = useWeatherStore()

const STAGES = ['播种期', '出苗期', '分蘖期', '拔节期', '抽穗期', '开花期', '灌浆期', '成熟期']
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
    await farm.loadAlerts()
    return
  }
  // water / fertilize / harvest
  const map = { water: '灌溉', fertilize: '施肥', harvest: '收获' }
  try {
    await farm.doAction(field.field_id, type)
    ElMessage.success(`${map[type] || '操作'}成功`)
    await farm.loadAlerts()
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
const form = ref({ name: '', crop: '玉米', stage: '播种期', area: 1.0 })

function openCreate() {
  form.value = { name: '', crop: '玉米', stage: '播种期', area: 1.0 }
  createOpen.value = true
}
async function submitCreate() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请填写地块名称')
    return
  }
  creating.value = true
  try {
    await farm.createField({
      name: form.value.name.trim(),
      crop: form.value.crop,
      stage: form.value.stage,
      area: Number(form.value.area) || 1.0
    })
    ElMessage.success('地块创建成功')
    createOpen.value = false
    await farm.loadAlerts()
  } catch (err) {
    ElMessage.error(err?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  if (!farm.fields.length) farm.loadFields()
  if (!farm.alerts.length) farm.loadAlerts()
  if (!weather.available && !weather.loading) weather.loadWeather(168)
})
</script>

<style scoped>
.farm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1200px;
  margin: 0 auto;
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

.farm__grid {
  display: flex;
  flex-wrap: wrap;
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
  .farm__filter {
    flex: 1 1 100%;
    width: 100%;
  }
  .farm__count {
    margin-left: 0;
  }
}
</style>

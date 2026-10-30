<template>
  <el-popover
    v-model:visible="open"
    placement="bottom-end"
    :width="popWidth"
    trigger="manual"
    popper-class="loc-popover"
    :show-arrow="true"
    @show="syncDraft"
  >
    <template #reference>
      <button
        class="loc-pill"
        :class="{ 'loc-pill--icon': iconOnly }"
        type="button"
        :aria-label="`当前位置：${loc.summary}，点击切换`"
        @click="open = !open"
      >
        <el-icon :size="16"><LocationInformation /></el-icon>
        <span v-if="!iconOnly" class="loc-pill__text truncate">{{ loc.summary }}</span>
        <el-icon v-if="!iconOnly" :size="12" class="loc-pill__caret"><ArrowDown /></el-icon>
      </button>
    </template>

    <div class="loc-form">
      <p class="loc-form__hint">选择省 / 市 / 区后自动解析经纬度，全站气象与农事推演都会随之更新。</p>

      <label class="loc-field">
        <span class="loc-field__label">省份</span>
        <el-select v-model="draft.province" placeholder="请选择省份" filterable class="loc-field__control" @change="onProvinceChange">
          <el-option v-for="p in loc.provinces" :key="p" :label="p" :value="p" />
        </el-select>
      </label>

      <label class="loc-field">
        <span class="loc-field__label">城市</span>
        <el-select
          v-model="draft.city"
          placeholder="请选择城市"
          filterable
          :disabled="!draft.province"
          class="loc-field__control"
          @change="onCityChange"
        >
          <el-option v-for="c in loc.cities" :key="c" :label="c" :value="c" />
        </el-select>
      </label>

      <label class="loc-field">
        <span class="loc-field__label">区县</span>
        <el-select
          v-model="draft.district"
          placeholder="可选，细化到区县"
          filterable
          clearable
          :disabled="!draft.city"
          class="loc-field__control"
        >
          <el-option v-for="d in loc.districts" :key="d" :label="d" :value="d" />
        </el-select>
      </label>

      <div class="loc-coords">
        <span class="loc-coords__item">
          <span class="loc-coords__label">纬度</span>
          <span class="loc-coords__value num">{{ coordText(loc.selected.latitude) }}</span>
        </span>
        <span class="loc-coords__item">
          <span class="loc-coords__label">经度</span>
          <span class="loc-coords__value num">{{ coordText(loc.selected.longitude) }}</span>
        </span>
      </div>

      <el-button class="loc-auto" :loading="locating" plain @click="onAutoLocate">
        <el-icon :size="14"><Aim /></el-icon>
        <span>使用当前位置</span>
      </el-button>

      <p v-if="loc.error" class="loc-error">{{ loc.error }}</p>

      <div class="loc-footer">
        <el-button @click="open = false">取消</el-button>
        <el-button type="primary" :loading="loc.loading" @click="onConfirm">确定</el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useLocationStore } from '@/stores/location'

const props = defineProps({
  /** 仅显示图标（<768px 顶栏使用） */
  iconOnly: { type: Boolean, default: false }
})

const emit = defineEmits(['changed'])

const loc = useLocationStore()
const open = ref(false)
const locating = ref(false)

/** 抽屉内的草稿值，点「确定」后才写回 store */
const draft = reactive({ province: '', city: '', district: '' })

/**
 * 弹层宽度：在窄 iframe（如创空间预览）中也限制宽度，避免溢出视口。
 * 不采用全屏抽屉，保证页面其余部分始终可见、不被遮挡。
 */
const popWidth = computed(() => Math.max(280, Math.min(360, (window.innerWidth || 360) - 32)))

function coordText(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(4) : '--'
}

function syncDraft() {
  draft.province = loc.selected.province || ''
  draft.city = loc.selected.city || ''
  draft.district = loc.selected.district || ''
}

onMounted(async () => {
  if (!loc.provinces.length) await loc.init()
  syncDraft()
})

watch(open, (visible) => {
  if (visible) syncDraft()
})

async function onProvinceChange(province) {
  draft.city = ''
  draft.district = ''
  await loc.loadCities(province)
}

async function onCityChange(city) {
  draft.district = ''
  await loc.loadDistricts(draft.province, city)
}

async function onAutoLocate() {
  locating.value = true
  try {
    const res = await loc.locateByBrowser()
    if (res.ok) {
      ElMessage.success(`已定位到 ${loc.selected.latitude.toFixed(2)}, ${loc.selected.longitude.toFixed(2)}`)
      open.value = false
      emit('changed')
    } else if (res.reason === 'unsupported') {
      ElMessage.warning('当前浏览器不支持自动定位，请手动选择省市')
    } else if (res.reason === 'denied') {
      ElMessage.warning('定位权限被拒绝，请手动选择省市')
    } else {
      ElMessage.warning('定位失败，请手动选择省市或稍后重试')
    }
  } finally {
    locating.value = false
  }
}

async function onConfirm() {
  loc.selected.province = draft.province
  loc.selected.city = draft.city
  loc.selected.district = draft.district || ''
  const ok = await loc.applySelection()
  open.value = false
  if (ok) {
    ElMessage.success(`已切换到 ${loc.summary}`)
  } else {
    ElMessage.warning(loc.error || '未获取到该位置的经纬度，已保留上次坐标')
  }
  emit('changed')
}
</script>

<style scoped>
.loc-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  max-width: 240px;
  height: 36px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  color: var(--text-body);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.loc-pill:hover {
  border-color: var(--brand-300);
  background: var(--brand-50);
  color: var(--brand-600);
}

html.dark .loc-pill:hover {
  background: color-mix(in srgb, var(--brand-500) 16%, transparent);
}

.loc-pill--icon {
  width: 36px;
  padding: 0;
  justify-content: center;
}

.loc-pill__text {
  max-width: 168px;
  font-weight: 500;
}

.loc-pill__caret {
  color: var(--text-disabled);
}

.loc-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.loc-form__hint {
  margin: 0;
  font-size: var(--fs-sm);
  line-height: var(--lh-sm);
  color: var(--text-secondary);
}

.loc-field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.loc-field__label {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-body);
}

.loc-field__control {
  width: 100%;
}

.loc-coords {
  display: flex;
  gap: var(--sp-4);
  padding: var(--sp-3);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
}

.loc-coords__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.loc-coords__label {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.loc-coords__value {
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--text-title);
}

.loc-auto {
  align-self: flex-start;
}

.loc-error {
  margin: 0;
  font-size: var(--fs-caption);
  color: var(--state-danger);
}

.loc-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--sp-2);
}
</style>

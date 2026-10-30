import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { farmApi } from '@/api'
import { useLocationStore } from './location'
import { useWeatherStore } from './weather'
import { deriveFieldMetrics, fieldAdvice } from '@/utils/suitability'

export const useFarmStore = defineStore('farm', () => {
  const fields = ref([])
  const alerts = ref([])
  const loading = ref(false)

  /** 气象 store：地块指标推演的唯一数据来源（近 72h 聚合） */
  const weather = useWeatherStore()

  /**
   * 地块 + 气象联动推演后的视图模型。
   * 健康/水分/生长均由 deriveFieldMetrics 基于真实气象计算；
   * 不可算时 metrics.computable=false，UI 显示 '--'，绝不回退到后端写死值。
   */
  const fieldsWithMetrics = computed(() =>
    fields.value.map((f) => {
      const metrics = deriveFieldMetrics(f, weather.agg72)
      const advice = fieldAdvice(f, metrics, weather.agg72)
      return { ...f, metrics, advice }
    })
  )

  /** 列表/筛选用的状态等级：good 正常 / warn 需关注 / risk 风险 / unknown 无数据 */
  function fieldStatus(field) {
    const m = field?.metrics
    if (!m || !m.computable) return 'unknown'
    const water = Number(m.water)
    const health = Number(m.health)
    const growth = Number(m.growth)
    if ((Number.isFinite(water) && water < 40) || (Number.isFinite(health) && health < 50)) return 'risk'
    if ((Number.isFinite(water) && water < 55) || (Number.isFinite(health) && health < 65) || (Number.isFinite(growth) && growth < 35)) return 'warn'
    return 'good'
  }

  async function loadFields() {
    loading.value = true
    try {
      const res = await farmApi.listFields()
      fields.value = res.fields || []
    } finally {
      loading.value = false
    }
  }

  async function createField(data) {
    const res = await farmApi.createField(data)
    await loadFields()
    return res
  }

  async function deleteField(id) {
    await farmApi.deleteField(id)
    await loadFields()
  }

  async function doAction(id, action) {
    const map = { water: farmApi.water, fertilize: farmApi.fertilize, harvest: farmApi.harvest }
    const res = await map[action](id)
    await loadFields()
    return res
  }

  async function loadAlerts() {
    const loc = useLocationStore()
    const res = await farmApi.alerts({
      latitude: loc.selected.latitude,
      longitude: loc.selected.longitude,
      province: loc.selected.province,
      city: loc.selected.city
    })
    alerts.value = res.alerts || []
  }

  return {
    fields,
    fieldsWithMetrics,
    alerts,
    loading,
    fieldStatus,
    loadFields,
    createField,
    deleteField,
    doAction,
    loadAlerts
  }
})

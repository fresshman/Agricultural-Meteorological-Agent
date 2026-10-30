import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { warningApi } from '@/api'
import { useLocationStore } from './location'

function normalize(w) {
  return {
    type: w?.type || '',
    risk_level: w?.risk_level || '低风险',
    details: w?.details || {},
    category: w?.__cat || 'disaster'
  }
}

function dayKeyOf(dateStr) {
  const d = dateStr ? new Date(dateStr) : null
  if (!d || Number.isNaN(d.getTime())) return null
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export const useWarningStore = defineStore('warning', () => {
  const disasters = ref([])
  const pests = ref([])
  const raw = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)
  const analyzed = ref(false)
  const cropType = ref('玉米')

  /** 所有预警（灾害 + 病虫害） */
  const all = computed(() =>
    [...disasters.value, ...pests.value].map((w, i) => ({ ...w, _id: `${w.category}_${i}` }))
  )

  /** 二次筛选：按 occur_time 的日期归属到 今天 / 明天 / 未来 7 天 */
  function filterByDimension(list, dimension) {
    if (dimension === 'week') return list
    const p = (n) => String(n).padStart(2, '0')
    const todayKey = `${new Date().getFullYear()}-${p(new Date().getMonth() + 1)}-${p(new Date().getDate())}`
    const tmr = new Date(Date.now() + 86400000)
    const tmrKey = `${tmr.getFullYear()}-${p(tmr.getMonth() + 1)}-${p(tmr.getDate())}`
    return list.filter((item) => {
      const k = dayKeyOf(item.details?.occur_time)
      if (!k) return false
      if (dimension === 'today') return k === todayKey
      if (dimension === 'tomorrow') return k === tmrKey
      return true
    })
  }

  async function analyze() {
    loading.value = true
    error.value = null
    const loc = useLocationStore()
    const payload = {
      latitude: loc.selected.latitude,
      longitude: loc.selected.longitude,
      province: loc.selected.province,
      city: loc.selected.city,
      crop_type: cropType.value
    }
    try {
      const [d, p] = await Promise.all([
        warningApi.disaster(payload).catch(() => ({ status: false, warnings: [] })),
        warningApi.pest(payload).catch(() => ({ status: false, warnings: [] }))
      ])
      disasters.value = (d.warnings || []).map((w) => ({ ...normalize(w), __cat: 'disaster', category: 'disaster' }))
      pests.value = (p.warnings || []).map((w) => ({ ...normalize(w), __cat: 'pest', category: 'pest' }))
      raw.value = { disaster: d.raw || null, pest: p.raw || null }
      lastUpdated.value = new Date()
      analyzed.value = true
      if (!d.status && !p.status) {
        error.value = d.message || p.message || '气象 API 未配置，无法分析'
      }
    } catch (err) {
      error.value = err?.message || '预警分析失败'
    } finally {
      loading.value = false
    }
  }

  function setCrop(crop) {
    cropType.value = crop
  }

  return { disasters, pests, raw, loading, error, lastUpdated, analyzed, cropType, all, filterByDimension, analyze, setCrop }
})

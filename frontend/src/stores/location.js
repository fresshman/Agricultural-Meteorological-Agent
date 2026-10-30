import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { locationApi } from '@/api'
import { KEYS, readJSON, writeJSON } from '@/utils/storage'

/** 默认位置：中原主产区，保证首次进入即有可用上下文 */
const DEFAULT_LOCATION = {
  province: '河南省',
  city: '郑州市',
  district: '',
  latitude: 34.75,
  longitude: 113.65,
  formatted_address: '河南省郑州市'
}

export const useLocationStore = defineStore('location', () => {
  const provinces = ref([])
  const cities = ref([])
  const districts = ref([])
  const selected = ref({ ...DEFAULT_LOCATION })

  const loading = ref(false)
  const error = ref(null)
  const autoLocated = ref(false)
  /** 每次位置真正生效后自增，供其他 store watch 后刷新数据 */
  const revision = ref(0)

  /** 展示用的位置摘要，如「河南省 郑州市」 */
  const summary = computed(() => {
    const s = selected.value
    const parts = [s.province, s.city, s.district].filter(Boolean)
    return parts.length ? parts.join(' · ') : '未选择位置'
  })

  /** 是否已具备可用经纬度 */
  const hasCoords = computed(
    () => Number.isFinite(Number(selected.value.latitude)) && Number.isFinite(Number(selected.value.longitude))
  )

  function persist() {
    writeJSON(KEYS.LOCATION, { v: 1, ...selected.value })
  }

  function restore() {
    const saved = readJSON(KEYS.LOCATION, null)
    if (saved && typeof saved === 'object') {
      selected.value = { ...DEFAULT_LOCATION, ...saved }
    }
  }

  /**
   * 统一把失败原因转成可读文案：优先显示 HTTP 状态码，便于区分 404 / 500 / 网络不可达。
   * @param {string} label 列表名称，如「省份列表」
   * @param {any} err 已由 axios 拦截器归一化的错误对象
   * @returns {string}
   */
  function failText(label, err) {
    const detail = err?.code
      ? `HTTP ${err.code}`
      : err?.isTimeout
        ? '请求超时'
        : err?.isNetwork
          ? '网络不可达'
          : (err?.message || '未知错误')
    return `${label}加载失败（${detail}）`
  }

  async function loadProvinces() {
    if (provinces.value.length) return
    loading.value = true
    error.value = null
    try {
      const res = await locationApi.provinces()
      provinces.value = res?.provinces || []
    } catch (err) {
      error.value = failText('省份列表', err)
    } finally {
      loading.value = false
    }
  }

  async function loadCities(province) {
    if (!province) {
      cities.value = []
      districts.value = []
      return
    }
    loading.value = true
    error.value = null
    try {
      const res = await locationApi.cities(province)
      cities.value = res?.cities || []
      districts.value = []
    } catch (err) {
      cities.value = []
      error.value = failText('城市列表', err)
    } finally {
      loading.value = false
    }
  }

  async function loadDistricts(province, city) {
    if (!province || !city) {
      districts.value = []
      return
    }
    loading.value = true
    error.value = null
    try {
      const res = await locationApi.districts(province, city)
      districts.value = res?.districts || []
    } catch (err) {
      districts.value = []
      error.value = failText('区县列表', err)
    } finally {
      loading.value = false
    }
  }

  /** 依据当前省市区回填经纬度（高德地理编码），失败时保留原坐标 */
  async function fetchCoordinates() {
    const s = selected.value
    loading.value = true
    error.value = null
    try {
      const res = await locationApi.coordinates({
        province: s.province,
        city: s.city,
        district: s.district
      })
      if (res?.status && Number.isFinite(Number(res.latitude))) {
        selected.value.latitude = Number(res.latitude)
        selected.value.longitude = Number(res.longitude)
        selected.value.formatted_address = res.formatted_address || s.formatted_address
      } else {
        error.value = res?.message || '未能获取该位置的经纬度'
      }
      return res
    } catch (err) {
      error.value = '地理编码服务不可用'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 切换省份：清空下级并重拉列表。
   * @param {string} province
   */
  async function setProvince(province) {
    selected.value.province = province
    selected.value.city = ''
    selected.value.district = ''
    await loadCities(province)
  }

  /**
   * 切换城市：清空区县并重拉列表。
   * @param {string} city
   */
  async function setCity(city) {
    selected.value.city = city
    selected.value.district = ''
    await loadDistricts(selected.value.province, city)
  }

  /**
   * 切换区县。
   * @param {string} district
   */
  function setDistrict(district) {
    selected.value.district = district
  }

  /**
   * 提交选择：回填经纬度 → 持久化 → 自增 revision 通知其他 store。
   * @returns {Promise<boolean>} 是否成功
   */
  async function applySelection() {
    const res = await fetchCoordinates()
    const ok = Boolean(res?.status)
    if (ok) {
      selected.value.formatted_address =
        res.formatted_address || [selected.value.province, selected.value.city, selected.value.district].filter(Boolean).join('')
    } else if (!selected.value.formatted_address) {
      selected.value.formatted_address = [selected.value.province, selected.value.city].filter(Boolean).join('')
    }
    persist()
    revision.value += 1
    return ok
  }

  /**
   * 浏览器自动定位（navigator.geolocation）。
   * 后端无逆地理编码接口，故只回填经纬度；失败静默降级，由调用方 Toast 提示。
   * @returns {Promise<{ ok: boolean, reason?: string }>}
   */
  async function locateByBrowser() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      return { ok: false, reason: 'unsupported' }
    }
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          selected.value.latitude = Number(pos.coords.latitude.toFixed(4))
          selected.value.longitude = Number(pos.coords.longitude.toFixed(4))
          selected.value.formatted_address = `当前定位 (${selected.value.latitude}, ${selected.value.longitude})`
          autoLocated.value = true
          persist()
          revision.value += 1
          resolve({ ok: true })
        },
        (err) => {
          const reason = err?.code === 1 ? 'denied' : err?.code === 2 ? 'unavailable' : 'timeout'
          resolve({ ok: false, reason })
        },
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 600000 }
      )
    })
  }

  /**
   * 初始化：恢复持久化位置 → 拉取行政区划。
   * @returns {Promise<void>}
   */
  async function init() {
    restore()
    await loadProvinces()
    if (selected.value.province) await loadCities(selected.value.province)
    if (selected.value.province && selected.value.city) {
      await loadDistricts(selected.value.province, selected.value.city)
    }
  }

  return {
    provinces,
    cities,
    districts,
    selected,
    loading,
    error,
    autoLocated,
    revision,
    summary,
    hasCoords,
    init,
    loadProvinces,
    loadCities,
    loadDistricts,
    fetchCoordinates,
    setProvince,
    setCity,
    setDistrict,
    applySelection,
    locateByBrowser,
    persist
  }
})

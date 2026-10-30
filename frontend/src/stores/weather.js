import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { weatherApi } from '@/api'
import { useLocationStore } from './location'
import { formatMonthDay, groupByDay, relativeDayLabel, toDayKey } from '@/utils/format'
import { aggregateHours } from '@/utils/suitability'

/** 按日聚合时判定「样本不足」的阈值 */
const MIN_DAY_SAMPLES = 1

/**
 * 计算平均值的纯函数。
 * @param {number[]} arr
 * @returns {number|null}
 */
function avg(arr) {
  if (!arr.length) return null
  return arr.reduce((a, b) => a + b, 0) / arr.length
}

export const useWeatherStore = defineStore('weather', () => {
  /** 当前（首个样本）气象；无数据时为 null，绝不回退到写死的默认值 */
  const current = ref(null)
  /** 原始逐时序列 */
  const hourly = ref([])
  /** 后端返回的摘要文案 */
  const summary = ref('')
  /** 后端 status=false 表示气象源不可用，此时所有推演指标必须显示 '--' */
  const status = ref(false)
  /** 后端返回的是模拟数据（气象 API 未配置/请求失败降级），UI 应提示非真实数据 */
  const isMock = ref(false)

  const loading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)
  /** 已成功加载过的坐标，避免同一位置重复请求 */
  const loadedKey = ref('')

  /** 未来 7 天按日聚合 */
  const daily7 = computed(() => {
    const groups = groupByDay(hourly.value, (item) => item?.timestamp)
    // 今天只可能拿到"此刻到今晚"的时次，标记为 partial，
    // 供 scoreDay 用 MIN_PARTIAL_SAMPLES 而非完整日的 MIN_SAMPLES 判定
    const todayKey = toDayKey(new Date())
    return groups.slice(0, 7).map((g) => {
      const temps = g.items.map((i) => Number(i.temperature)).filter(Number.isFinite)
      const maxes = g.items.map((i) => Number(i.max_temperature)).filter(Number.isFinite)
      const mins = g.items.map((i) => Number(i.min_temperature)).filter(Number.isFinite)
      const hums = g.items.map((i) => Number(i.humidity)).filter(Number.isFinite)
      const winds = g.items.map((i) => Number(i.wind_speed)).filter(Number.isFinite)
      const rains = g.items.map((i) => Number(i.precipitation)).filter(Number.isFinite)

      const tempAvg = avg(temps)
      return {
        date: g.key,
        label: relativeDayLabel(g.date),
        shortLabel: formatMonthDay(g.date),
        tempMax: maxes.length ? Math.max(...maxes) : temps.length ? Math.max(...temps) : tempAvg,
        tempMin: mins.length ? Math.min(...mins) : temps.length ? Math.min(...temps) : tempAvg,
        tempAvg,
        humidityAvg: avg(hums),
        precipSum: rains.length ? Math.round(rains.reduce((a, b) => a + b, 0) * 10) / 10 : 0,
        windMax: winds.length ? Math.max(...winds) : null,
        hours: g.items.length,
        partial: g.key === todayKey,
        reliable: g.items.length >= MIN_DAY_SAMPLES
      }
    })
  })

  /** 近 72 小时聚合，供地块指标推演 */
  const agg72 = computed(() => aggregateHours(hourly.value.slice(0, 72), 72))

  /** 未来 12 小时累计降水，供指标卡副描述 */
  const precipNext12 = computed(() => {
    const sum = hourly.value
      .slice(0, 12)
      .map((i) => Number(i?.precipitation))
      .filter(Number.isFinite)
      .reduce((a, b) => a + b, 0)
    return Math.round(sum * 10) / 10
  })

  /** 气象是否可用（status=true 且有样本） */
  const available = computed(() => status.value && hourly.value.length > 0)

  function locationParams(hours) {
    const loc = useLocationStore()
    return {
      latitude: loc.selected.latitude,
      longitude: loc.selected.longitude,
      province: loc.selected.province,
      city: loc.selected.city,
      hours
    }
  }

  /**
   * 拉取气象：单次请求同时满足实时、7 天趋势、近 72h 聚合三种需求。
   * hours=168 失败时自动降级为 72 重试一次（R16）。
   * @param {number} [hours=168]
   * @returns {Promise<boolean>} 是否成功
   */
  async function loadWeather(hours = 168) {
    loading.value = true
    error.value = null
    try {
      let res = null
      try {
        res = await weatherApi.get(locationParams(hours))
      } catch (err) {
        if (hours > 72) {
          res = await weatherApi.get(locationParams(72))
        } else {
          throw err
        }
      }

      const list = Array.isArray(res?.data) ? res.data : []
      status.value = Boolean(res?.status) && list.length > 0
      isMock.value = Boolean(res?.is_mock)
      summary.value = res?.summary || res?.message || ''

      if (status.value) {
        hourly.value = list
        current.value = list[0] || null
        error.value = null
      } else {
        // 气象源不可用：清空数据，UI 统一显示 '--'，绝不显示写死的默认值
        hourly.value = []
        current.value = null
        isMock.value = false
        error.value = res?.message || summary.value || '气象服务暂不可用'
      }

      lastUpdated.value = new Date()
      const loc = useLocationStore()
      loadedKey.value = `${loc.selected.latitude},${loc.selected.longitude}`
      return status.value
    } catch (err) {
      hourly.value = []
      current.value = null
      status.value = false
      error.value = err?.message || '气象加载失败'
      return false
    } finally {
      loading.value = false
    }
  }

  /** 按当前位置刷新（沿用上次的 hours） */
  function refresh() {
    return loadWeather(168)
  }

  function reset() {
    current.value = null
    hourly.value = []
    summary.value = ''
    status.value = false
    isMock.value = false
    error.value = null
    lastUpdated.value = null
    loadedKey.value = ''
  }

  // 位置变更后自动刷新（全站共享位置的联动点）
  const loc = useLocationStore()
  watch(
    () => loc.revision,
    () => {
      loadWeather(168)
    }
  )

  return {
    current,
    hourly,
    daily7,
    agg72,
    precipNext12,
    summary,
    status,
    isMock,
    available,
    loading,
    error,
    lastUpdated,
    loadWeather,
    refresh,
    reset
  }
})

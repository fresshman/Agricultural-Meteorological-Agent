/**
 * 作物生长曲线模型（前端推演，用于可视化）
 * --------------------------------------------------------------------------
 * 全站唯一的「作物物候 / 生长曲线」规则来源。
 *
 * 两条曲线：
 *  - 理论生长：按物候期 S 形（logistic）发育曲线，0→100，收获期接近满值。
 *  - 实际生长：理论曲线 × 近期气象胁迫系数（温度偏离最适、降水亏缺），
 *    仅「今天及之前」有值；今天之后属于未来，实际未知，置为 null。
 *
 * 重要：模型为科普级推演，非精准农艺模型；无气象数据时实际曲线整体为 null，
 * UI 显示「需气象数据」，绝不编造实际长势数字。
 */

/** 作物 → 规范化 key（兼容别称） */
const CROP_ALIAS = [
  { key: 'corn', test: /玉/, label: '玉米' },
  { key: 'wheat', test: /麦/, label: '小麦' },
  { key: 'rice', test: /稻/, label: '水稻' },
  { key: 'soy', test: /大?豆/, label: '大豆' },
  { key: 'potato', test: /马铃|土豆/, label: '马铃薯' }
]

export const CROP_LABEL = { corn: '玉米', wheat: '小麦', rice: '水稻', soy: '大豆', potato: '马铃薯', unknown: '作物' }

/** @returns {'corn'|'wheat'|'rice'|'soy'|'potato'|'unknown'} */
export function cropKey(crop) {
  const c = String(crop || '')
  for (const a of CROP_ALIAS) if (a.test.test(c)) return a.key
  return 'unknown'
}

/**
 * 物候配置（seasonDays 为全生育期天数；stages 为各阶段占比；
 * optMid/optTol 为最适均温与容忍带；waterNeed 为近 72h 期望降水 mm）。
 * 数值为常见作物经验近似，仅供可视化。
 */
export const CROP_PHENOLOGY = {
  corn: {
    seasonDays: 120,
    optMid: 26, optTol: 10, waterNeed: 20,
    color: 'var(--gold-500)',
    stages: [
      { name: '苗期', startFrac: 0, endFrac: 0.2 },
      { name: '拔节期', startFrac: 0.2, endFrac: 0.45 },
      { name: '抽雄吐丝', startFrac: 0.45, endFrac: 0.6 },
      { name: '灌浆期', startFrac: 0.6, endFrac: 0.85 },
      { name: '成熟期', startFrac: 0.85, endFrac: 1 }
    ]
  },
  wheat: {
    seasonDays: 230,
    optMid: 18, optTol: 9, waterNeed: 15,
    color: 'var(--gold-500)',
    stages: [
      { name: '出苗期', startFrac: 0, endFrac: 0.1 },
      { name: '分蘖期', startFrac: 0.1, endFrac: 0.3 },
      { name: '越冬期', startFrac: 0.3, endFrac: 0.5 },
      { name: '返青拔节', startFrac: 0.5, endFrac: 0.7 },
      { name: '抽穗期', startFrac: 0.7, endFrac: 0.85 },
      { name: '灌浆期', startFrac: 0.85, endFrac: 0.95 },
      { name: '成熟期', startFrac: 0.95, endFrac: 1 }
    ]
  },
  rice: {
    seasonDays: 150,
    optMid: 27, optTol: 8, waterNeed: 25,
    color: 'var(--sky-500)',
    stages: [
      { name: '秧苗期', startFrac: 0, endFrac: 0.15 },
      { name: '分蘖期', startFrac: 0.15, endFrac: 0.4 },
      { name: '拔节孕穗', startFrac: 0.4, endFrac: 0.6 },
      { name: '抽穗开花', startFrac: 0.6, endFrac: 0.75 },
      { name: '灌浆期', startFrac: 0.75, endFrac: 0.92 },
      { name: '成熟期', startFrac: 0.92, endFrac: 1 }
    ]
  },
  soy: {
    seasonDays: 130,
    optMid: 23, optTol: 8, waterNeed: 18,
    color: 'var(--state-success)',
    stages: [
      { name: '出苗期', startFrac: 0, endFrac: 0.12 },
      { name: '分枝期', startFrac: 0.12, endFrac: 0.35 },
      { name: '开花期', startFrac: 0.35, endFrac: 0.55 },
      { name: '结荚期', startFrac: 0.55, endFrac: 0.78 },
      { name: '鼓粒期', startFrac: 0.78, endFrac: 0.93 },
      { name: '成熟期', startFrac: 0.93, endFrac: 1 }
    ]
  },
  potato: {
    seasonDays: 100,
    optMid: 17, optTol: 8, waterNeed: 16,
    color: 'var(--state-orange)',
    stages: [
      { name: '出苗期', startFrac: 0, endFrac: 0.15 },
      { name: '块茎形成', startFrac: 0.15, endFrac: 0.45 },
      { name: '块茎膨大', startFrac: 0.45, endFrac: 0.8 },
      { name: '淀粉积累', startFrac: 0.8, endFrac: 0.95 },
      { name: '成熟期', startFrac: 0.95, endFrac: 1 }
    ]
  }
}

const STEEP = 7

/** 发育指数 S 形曲线（0→100），frac ∈ [0,1] */
function theoreticalValue(frac) {
  const f = Math.min(1, Math.max(0, frac))
  return Math.round((100 / (1 + Math.exp(-STEEP * (f - 0.5)))) * 10) / 10
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

/** 解析播种日期：优先 planted_at；否则按当前阶段反推；再否则默认 45 天前 */
function resolvePlantDate(field, pheno) {
  if (field?.planted_at) {
    const d = new Date(field.planted_at)
    if (!Number.isNaN(d.getTime())) return d
  }
  const stage = String(field?.stage || '')
  const st = pheno.stages.find((s) => stage.includes(s.name))
  const now = Date.now()
  if (st) {
    const mid = (st.startFrac + st.endFrac) / 2
    return new Date(now - mid * pheno.seasonDays * 86400000)
  }
  return new Date(now - 45 * 86400000)
}

/**
 * 构建地块生长曲线模型。
 * @param {Object} field 地块（含 crop / stage / planted_at）
 * @param {{ agg72:Object, available:boolean, daily7:Array }} weather 气象 store 的部分字段
 * @returns {Object|null} 模型；作物无法识别时返回 null
 */
export function buildGrowthModel(field, weather) {
  const key = cropKey(field?.crop)
  if (key === 'unknown') return null
  const pheno = CROP_PHENOLOGY[key]
  const plant = resolvePlantDate(field, pheno)
  const seasonMs = pheno.seasonDays * 86400000
  const harvest = new Date(plant.getTime() + seasonMs)
  const now = Date.now()
  const currentDay = (now - plant.getTime()) / 86400000
  const currentFrac = clamp(currentDay / pheno.seasonDays, 0, 1)

  // 实际长势系数：由近 72h 气象推演（无气象则为 null）
  const agg = weather?.agg72
  let factor = null
  if (weather?.available && agg && Number.isFinite(Number(agg.tempAvg))) {
    const tempAvg = Number(agg.tempAvg)
    const precip = Number(agg.precipSum) || 0
    const tempScore = 1 - Math.min(1, Math.abs(tempAvg - pheno.optMid) / pheno.optTol)
    const waterScore = clamp(0.5 + precip / (2 * pheno.waterNeed), 0.4, 1)
    factor = clamp(0.6 + 0.4 * (0.6 * tempScore + 0.4 * waterScore), 0.6, 1)
  }

  // 采样时间点
  const N = 31
  const points = []
  let todayIndex = 0
  for (let i = 0; i <= N; i++) {
    const frac = i / N
    const date = new Date(plant.getTime() + frac * seasonMs)
    const theo = theoreticalValue(frac)
    const isPast = date.getTime() <= now
    const actual = factor !== null && isPast ? Math.round(clamp(theo * factor, 0, 100)) : null
    points.push({ date, frac, theo, actual, isPast, isToday: false })
    if (isPast) todayIndex = i
  }
  points[todayIndex].isToday = true

  // 当前阶段
  const curStageObj = pheno.stages.find((s) => currentFrac >= s.startFrac && currentFrac < s.endFrac)
  const harvested = currentDay >= pheno.seasonDays
  const currentStage = harvested ? '已收获' : curStageObj ? curStageObj.name : pheno.stages[0].name
  const harvestEtaDays = harvested ? 0 : Math.max(0, Math.ceil(pheno.seasonDays - currentDay))
  const currentTheo = theoreticalValue(currentFrac)
  const currentActual = factor !== null ? Math.round(clamp(currentTheo * factor, 0, 100)) : null
  const deficit = currentActual !== null ? Math.round(currentTheo - currentActual) : null

  return {
    key,
    crop: field.crop,
    cropLabel: CROP_LABEL[key],
    seasonDays: pheno.seasonDays,
    plantDateIso: plant.toISOString().slice(0, 10),
    harvestDateIso: harvest.toISOString().slice(0, 10),
    color: pheno.color,
    points,
    todayIndex,
    currentFrac,
    currentStage,
    harvested,
    harvestEtaDays,
    currentTheo,
    currentActual,
    deficit,
    hasWeather: Boolean(weather?.available),
    basis: factor !== null
      ? `依据近 72h 气象（均温 ${Number(agg.tempAvg).toFixed(1)}℃、累计降水 ${Number(agg.precipSum).toFixed(1)}mm）推演实际长势系数 ${(factor * 100).toFixed(0)}%`
      : '气象数据不足，仅展示理论发育曲线'
  }
}

export { theoreticalValue }

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

import { CROP_TYPES, getCropStages } from './crops'

/** 作物名规范化：先精确匹配，再按别称匹配 */
const CROP_ALIASES = [
  ['玉米', /玉米|苞米|苞谷/],
  ['小麦', /小麦/],
  ['水稻', /水稻|稻谷/],
  ['大豆', /大豆|黄豆/],
  ['马铃薯', /马铃薯|土豆/],
  ['莜麦', /莜麦|燕麦/],
  ['番茄', /番茄|西红柿/],
  ['黄瓜', /黄瓜/],
  ['辣椒', /辣椒|尖椒/],
  ['白菜', /白菜/],
  ['菠菜', /菠菜/],
  ['胡萝卜', /胡萝卜/],
  ['苹果', /苹果/],
  ['梨', /梨/],
  ['桃', /桃/],
  ['葡萄', /葡萄/],
  ['柑橘', /柑橘|橘子|橙/],
  ['月季', /月季|玫瑰/],
  ['菊花', /菊花/],
  ['百合', /百合/],
  ['兰花', /兰花|蝴蝶兰/],
  ['多肉植物', /多肉/]
]

/** @returns {string} 规范化作物名；不认识的返回 '' */
export function cropName(crop) {
  const c = String(crop || '').trim()
  if (!c) return ''
  if (CROP_TYPES.includes(c)) return c
  const hit = CROP_ALIASES.find(([, test]) => test.test(c))
  return hit ? hit[0] : ''
}

/**
 * 物候参数（seasonDays 为全生育期天数；optMid/optTol 为最适均温与容忍带；
 * waterNeed 为近 72h 期望降水 mm）。数值为常见作物经验近似，仅供可视化。
 * 阶段序列来自 utils/crops.js，与后端 CROP_CONFIG 一致。
 */
const PHENOLOGY_PARAMS = {
  玉米: { seasonDays: 120, optMid: 26, optTol: 10, waterNeed: 20, color: 'var(--gold-500)' },
  小麦: { seasonDays: 240, optMid: 18, optTol: 9, waterNeed: 15, color: 'var(--gold-500)' },
  水稻: { seasonDays: 150, optMid: 27, optTol: 8, waterNeed: 25, color: 'var(--sky-500)' },
  大豆: { seasonDays: 130, optMid: 23, optTol: 8, waterNeed: 18, color: 'var(--state-success)' },
  马铃薯: { seasonDays: 100, optMid: 17, optTol: 8, waterNeed: 16, color: 'var(--state-orange)' },
  莜麦: { seasonDays: 100, optMid: 18, optTol: 9, waterNeed: 15, color: 'var(--gold-500)' },
  番茄: { seasonDays: 120, optMid: 22, optTol: 8, waterNeed: 20, color: 'var(--state-danger)' },
  黄瓜: { seasonDays: 90, optMid: 24, optTol: 8, waterNeed: 22, color: 'var(--state-success)' },
  辣椒: { seasonDays: 120, optMid: 25, optTol: 8, waterNeed: 18, color: 'var(--state-danger)' },
  白菜: { seasonDays: 70, optMid: 18, optTol: 9, waterNeed: 18, color: 'var(--state-success)' },
  菠菜: { seasonDays: 50, optMid: 16, optTol: 9, waterNeed: 15, color: 'var(--state-success)' },
  胡萝卜: { seasonDays: 100, optMid: 19, optTol: 8, waterNeed: 16, color: 'var(--state-orange)' },
  苹果: { seasonDays: 180, optMid: 20, optTol: 9, waterNeed: 20, color: 'var(--state-danger)' },
  梨: { seasonDays: 180, optMid: 20, optTol: 9, waterNeed: 20, color: 'var(--state-success)' },
  桃: { seasonDays: 160, optMid: 22, optTol: 8, waterNeed: 18, color: 'var(--state-danger)' },
  葡萄: { seasonDays: 150, optMid: 24, optTol: 8, waterNeed: 18, color: 'var(--brand-500)' },
  柑橘: { seasonDays: 210, optMid: 24, optTol: 8, waterNeed: 20, color: 'var(--state-orange)' },
  月季: { seasonDays: 120, optMid: 20, optTol: 8, waterNeed: 18, color: 'var(--state-danger)' },
  菊花: { seasonDays: 120, optMid: 20, optTol: 8, waterNeed: 18, color: 'var(--gold-500)' },
  百合: { seasonDays: 100, optMid: 18, optTol: 8, waterNeed: 16, color: 'var(--brand-500)' },
  兰花: { seasonDays: 200, optMid: 22, optTol: 8, waterNeed: 18, color: 'var(--state-success)' },
  多肉植物: { seasonDays: 120, optMid: 24, optTol: 10, waterNeed: 8, color: 'var(--state-success)' }
}

/** 按阶段名估算相对时长权重，用于把全生育期切成阶段区间 */
const STAGE_WEIGHT_RULES = [
  [/播种/, 0.6],
  [/出苗|幼苗|秧苗|萌芽/, 0.9],
  [/苗期/, 1.1],
  [/分蘖|三叶|分枝/, 1.2],
  [/越冬/, 2.2],
  [/返青|拔节|伸蔓|定植|新芽/, 1.3],
  [/抽雄|吐丝|孕穗|抽穗|现蕾|上色|抽薹/, 0.9],
  [/开花/, 0.9],
  [/坐果|结荚|结果/, 1.1],
  [/灌浆|鼓粒|块茎|淀粉|膨大|结球|莲座|叶丛|生长期|肉质根/, 1.7],
  [/成熟/, 0.7]
]

function stageBands(stages) {
  if (!stages.length) return []
  const weights = stages.map((name) => {
    const hit = STAGE_WEIGHT_RULES.find(([re]) => re.test(name))
    return hit ? hit[1] : 1
  })
  const total = weights.reduce((a, b) => a + b, 0) || 1
  let acc = 0
  return stages.map((name, i) => {
    const startFrac = acc / total
    acc += weights[i]
    return { name, startFrac, endFrac: i === stages.length - 1 ? 1 : acc / total }
  })
}

/** 22 种作物的物候配置（阶段区间由 stageBands 生成） */
export const CROP_PHENOLOGY = Object.fromEntries(
  Object.entries(PHENOLOGY_PARAMS).map(([crop, params]) => [
    crop,
    { ...params, stages: stageBands(getCropStages(crop)) }
  ])
)

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
  const name = cropName(field?.crop)
  const pheno = name ? CROP_PHENOLOGY[name] : null
  if (!pheno || !pheno.stages.length) return null
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

  // 当前阶段：用户填写的阶段优先（后端收获判定也按它走），
  // 匹配不到再按播种日期推演，最后落到首阶段，绝不出现 undefined
  const curStageObj = pheno.stages.find((s) => currentFrac >= s.startFrac && currentFrac < s.endFrac)
  const userStage = pheno.stages.find((s) => String(field?.stage || '').includes(s.name))
  const harvested = currentDay >= pheno.seasonDays
  const currentStage = harvested
    ? '已收获'
    : userStage
      ? userStage.name
      : curStageObj
        ? curStageObj.name
        : pheno.stages[0].name
  const harvestEtaDays = harvested ? 0 : Math.max(0, Math.ceil(pheno.seasonDays - currentDay))
  const currentTheo = theoreticalValue(currentFrac)
  const currentActual = factor !== null ? Math.round(clamp(currentTheo * factor, 0, 100)) : null
  const deficit = currentActual !== null ? Math.round(currentTheo - currentActual) : null

  return {
    key: name,
    crop: field.crop,
    cropLabel: name,
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

/**
 * 按播种日期推算当前阶段（新建地块时把「日期」与「阶段」对齐用）。
 * @returns {string} 阶段名；作物或日期无效时返回 ''
 */
export function stageForDate(crop, isoDate) {
  const name = cropName(crop)
  const pheno = name ? CROP_PHENOLOGY[name] : null
  if (!pheno || !pheno.stages.length || !isoDate) return ''
  const raw = String(isoDate)
  const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw) ? `${raw}T00:00:00` : raw)
  if (Number.isNaN(d.getTime())) return ''
  const frac = clamp((Date.now() - d.getTime()) / (pheno.seasonDays * 86400000), 0, 1)
  if (frac >= 1) return pheno.stages[pheno.stages.length - 1].name
  const hit = pheno.stages.find((s) => frac >= s.startFrac && frac < s.endFrac)
  return hit ? hit.name : pheno.stages[0].name
}

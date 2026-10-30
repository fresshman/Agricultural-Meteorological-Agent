/**
 * 农事适宜度规则引擎 + 地块指标气象推演
 * --------------------------------------------------------------------------
 * 全站唯一的「适宜度阈值 / 推演规则」来源。
 * 输入必须是真实气象数据（GET /api/weather 逐时聚合后的按日数据），
 * 不可算时统一返回 null，由 UI 显示 `--`，绝不产出无来源的数字。
 */

/**
 * 7 类农事操作，与后端 OPERATION_WINDOW_MAP 严格对齐。
 * @type {string[]}
 */
export const OPERATIONS = ['播种', '移栽', '授粉', '喷药', '追肥', '采收', '灌溉']

/**
 * @typedef {Object} DayWeather
 * @property {string} date        YYYY-MM-DD
 * @property {string} label       今天 / 明天 / 06-20
 * @property {number|null} tempMax
 * @property {number|null} tempMin
 * @property {number|null} tempAvg
 * @property {number|null} humidityAvg
 * @property {number|null} precipSum
 * @property {number|null} windMax
 * @property {number} hours       有效样本数（完整日 <6 视为不可靠）
 * @property {boolean} [partial]  true = 当天进行中（样本只覆盖今天剩余时次）
 */

/**
 * 每类操作的阈值配置（数值即规则，公开在 UI 的 ⓘ 浮层里）
 * @type {Record<string, {
 *   icon: string, desc: string,
 *   temp: { ideal: number[], hard: number[], weight: number },
 *   precip: { kind: 'dry-good'|'wet-good'|'moderate-good', bad: number, weight: number },
 *   wind: { good: number, bad: number, weight: number },
 *   humidity: { ideal: number[], hard: number[], weight: number }
 * }>}
 */
export const OPERATION_RULES = {
  播种: {
    icon: 'Sunny',
    desc: '播种要求地温稳定、墒情适中，忌暴雨板结与低温烂种',
    temp: { ideal: [15, 28], hard: [8, 35], weight: 28 },
    precip: { kind: 'dry-good', bad: 10, weight: 36 },
    wind: { good: 4, bad: 9, weight: 10 },
    humidity: { ideal: [55, 85], hard: [40, 95], weight: 12 }
  },
  移栽: {
    icon: 'Sunny',
    desc: '移栽缓苗期忌烈日暴晒与大雨冲刷，宜阴天或傍晚进行',
    temp: { ideal: [16, 28], hard: [10, 34], weight: 26 },
    precip: { kind: 'dry-good', bad: 8, weight: 34 },
    wind: { good: 4, bad: 8, weight: 14 },
    humidity: { ideal: [60, 88], hard: [45, 96], weight: 14 }
  },
  授粉: {
    icon: 'Sunny',
    desc: '授粉需晴朗微风，雨水冲刷花粉、大风影响传粉',
    temp: { ideal: [20, 30], hard: [14, 36], weight: 28 },
    precip: { kind: 'dry-good', bad: 3, weight: 40 },
    wind: { good: 3, bad: 7, weight: 16 },
    humidity: { ideal: [55, 80], hard: [40, 92], weight: 12 }
  },
  喷药: {
    icon: 'Drizzling',
    desc: '喷药需无雨、风力小于 3 级，避免药液飘移与雨水冲刷',
    temp: { ideal: [15, 28], hard: [8, 33], weight: 22 },
    precip: { kind: 'dry-good', bad: 2, weight: 44 },
    wind: { good: 3, bad: 7, weight: 26 },
    humidity: { ideal: [50, 85], hard: [35, 95], weight: 10 }
  },
  追肥: {
    icon: 'UploadFilled',
    desc: '追肥宜在土壤湿润时施用，暴雨会造成养分流失',
    temp: { ideal: [14, 30], hard: [6, 36], weight: 22 },
    precip: { kind: 'moderate-good', bad: 20, weight: 38 },
    wind: { good: 5, bad: 10, weight: 10 },
    humidity: { ideal: [55, 88], hard: [35, 97], weight: 12 }
  },
  采收: {
    icon: 'Sunny',
    desc: '采收需连续晴好，籽粒含水率随降水升高影响贮藏',
    temp: { ideal: [12, 30], hard: [4, 37], weight: 20 },
    precip: { kind: 'dry-good', bad: 3, weight: 42 },
    wind: { good: 5, bad: 10, weight: 12 },
    humidity: { ideal: [40, 75], hard: [30, 92], weight: 14 }
  },
  灌溉: {
    icon: 'Drizzling',
    desc: '灌溉依据土壤失墒程度：近期降水越少、气温越高越需要补水',
    temp: { ideal: [22, 34], hard: [8, 42], weight: 22 },
    precip: { kind: 'wet-good', bad: 10, weight: 44 },
    wind: { good: 5, bad: 10, weight: 8 },
    humidity: { ideal: [30, 70], hard: [20, 92], weight: 14 }
  }
}

/** 有效样本数的下限，低于此值判定为不可靠（用于完整的自然日） */
export const MIN_SAMPLES = 6

/**
 * 「当天进行中」的最小样本数。
 * 今天只可能拿到"此刻到今晚"的时次（例如傍晚打开只有 4~5 条），用 6 条完整日样本去卡
 * 会永远判为样本不足 → 首页"今日农事建议"永久卡在加载态。有样本即可评估。
 */
export const MIN_PARTIAL_SAMPLES = 1

/** @returns {number} 区间惩罚：0 表示完全适宜，weight 表示完全不适宜 */
function rangePenalty(value, ideal, hard, weight) {
  const v = Number(value)
  if (!Number.isFinite(v)) return 0
  if (v < hard[0] || v > hard[1]) return weight
  if (v < ideal[0]) {
    const span = Math.max(1e-6, ideal[0] - hard[0])
    return weight * Math.min(1, (ideal[0] - v) / span)
  }
  if (v > ideal[1]) {
    const span = Math.max(1e-6, hard[1] - ideal[1])
    return weight * Math.min(1, (v - ideal[1]) / span)
  }
  return 0
}

/** 线性惩罚 */
function linearPenalty(value, start, end, weight) {
  const v = Number(value)
  if (!Number.isFinite(v)) return 0
  if (end === start) return v > start ? weight : 0
  return weight * Math.min(1, Math.max(0, (v - start) / (end - start)))
}

function clampScore(v) {
  return Math.round(Math.min(100, Math.max(0, v)))
}

function fmt(value, digits = 1) {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(digits) : '--'
}

/**
 * 单日 × 单操作的适宜度评分（前端规则推演，可解释）。
 * @param {string} op 操作名，须为 OPERATIONS 之一
 * @param {DayWeather|null} day 按日聚合后的气象
 * @returns {{ score: number|null, level: string, reasons: string[], source: 'rule' }}
 */
export function scoreDay(op, day) {
  const rule = OPERATION_RULES[op]
  const empty = { score: null, level: 'unknown', reasons: [], source: 'rule' }
  if (!rule || !day) return empty
  // 当天进行中：样本天然只有"今天剩余时次"，按 MIN_PARTIAL_SAMPLES 判定
  const minSamples = day.partial ? MIN_PARTIAL_SAMPLES : MIN_SAMPLES
  if (!Number.isFinite(Number(day.hours)) || Number(day.hours) < minSamples) {
    return { ...empty, reasons: ['预报样本不足，暂不评估'] }
  }

  const reasons = []
  let score = 100

  // 温度
  const tempPenalty = rangePenalty(day.tempAvg, rule.temp.ideal, rule.temp.hard, rule.temp.weight)
  score -= tempPenalty
  if (tempPenalty >= rule.temp.weight * 0.3) {
    const t = Number(day.tempAvg)
    reasons.push(
      t < rule.temp.ideal[0]
        ? `日均气温 ${fmt(t)}℃ 低于适宜下限 ${rule.temp.ideal[0]}℃`
        : `日均气温 ${fmt(t)}℃ 高于适宜上限 ${rule.temp.ideal[1]}℃`
    )
  }

  // 降水
  const precip = Number(day.precipSum)
  let precipPenalty = 0
  if (Number.isFinite(precip)) {
    if (rule.precip.kind === 'wet-good') {
      // 灌溉：降水越多越不需要灌溉
      precipPenalty = linearPenalty(precip, 0, rule.precip.bad, rule.precip.weight)
      if (precipPenalty <= rule.precip.weight * 0.2) {
        reasons.push(`未来累计降水仅 ${fmt(precip)}mm，土壤失墒，适宜补水`)
      } else if (precipPenalty >= rule.precip.weight * 0.5) {
        reasons.push(`未来累计降水 ${fmt(precip)}mm，自然降水已可满足需求`)
      }
    } else if (rule.precip.kind === 'moderate-good') {
      // 追肥：小雨有利，暴雨流失
      precipPenalty = linearPenalty(precip, 3, rule.precip.bad, rule.precip.weight)
      if (precipPenalty >= rule.precip.weight * 0.3) {
        reasons.push(`未来累计降水 ${fmt(precip)}mm，易造成养分流失`)
      } else if (precip > 0.5 && precip <= 3) {
        reasons.push(`有小雨（${fmt(precip)}mm），利于肥料溶解下渗`)
      }
    } else {
      precipPenalty = linearPenalty(precip, 0, rule.precip.bad, rule.precip.weight)
      if (precipPenalty >= rule.precip.weight * 0.3) {
        reasons.push(`预计降水 ${fmt(precip)}mm，雨水会冲刷影响作业效果`)
      }
    }
    score -= precipPenalty
  }

  // 风
  const wind = Number(day.windMax)
  if (Number.isFinite(wind)) {
    const windPenalty = linearPenalty(wind, rule.wind.good, rule.wind.bad, rule.wind.weight)
    score -= windPenalty
    if (windPenalty >= rule.wind.weight * 0.3) {
      reasons.push(`最大风速 ${fmt(wind)}m/s，超过 ${rule.wind.good}m/s 的作业上限`)
    }
  }

  // 湿度
  const humidity = Number(day.humidityAvg)
  if (Number.isFinite(humidity)) {
    const humPenalty = rangePenalty(humidity, rule.humidity.ideal, rule.humidity.hard, rule.humidity.weight)
    score -= humPenalty
    if (humPenalty >= rule.humidity.weight * 0.3) {
      reasons.push(
        humidity > rule.humidity.ideal[1]
          ? `相对湿度 ${fmt(humidity, 0)}% 偏高`
          : `相对湿度 ${fmt(humidity, 0)}% 偏干`
      )
    }
  }

  if (!reasons.length) reasons.push(`气象条件总体有利于${op}`)

  const final = clampScore(score)
  return { score: final, level: levelOf(final), reasons: reasons.slice(0, 3), source: 'rule' }
}

/**
 * 分值 → 分档（与 utils/risk.js 的 suitabilityMeta 保持同一阈值口径）。
 * @param {number|null} score
 * @returns {'good'|'ok'|'care'|'bad'|'unknown'}
 */
export function levelOf(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) return 'unknown'
  if (n >= 75) return 'good'
  if (n >= 50) return 'ok'
  if (n >= 25) return 'care'
  return 'bad'
}

/**
 * 构建 7 操作 × 7 天的适宜度矩阵。
 * @param {DayWeather[]} daily7 按日聚合后的气象（建议取 7 天）
 * @param {string[]} [ops=OPERATIONS]
 * @returns {{ operations: string[], days: DayWeather[], rows: { op: string, icon: string, desc: string, cells: {score:number|null,level:string,reasons:string[],source:string}[] }[] }}
 */
export function buildWeekMatrix(daily7, ops = OPERATIONS) {
  const days = Array.isArray(daily7) ? daily7.slice(0, 7) : []
  const rows = ops.map((op) => {
    const rule = OPERATION_RULES[op] || { icon: 'Sunny', desc: '' }
    return {
      op,
      icon: rule.icon,
      desc: rule.desc,
      // 缺数据的单元格固定为 null（而不是 0），由 UI 显示 '--'
      cells: days.map((day) => scoreDay(op, day))
    }
  })
  return { operations: ops, days, rows }
}

/**
 * 从后端逐时数据聚合出「近 N 小时」统计（供地块推演使用）。
 * @param {{timestamp:string|number|Date, temperature?:number, humidity?:number, precipitation?:number}[]} hourly
 * @param {number} [hours=72]
 * @returns {{ precipSum: number, tempAvg: number|null, humidityAvg: number|null, hotHours: number, wetHours: number, sampleHours: number }}
 */
export function aggregateHours(hourly, hours = 72) {
  const list = (Array.isArray(hourly) ? hourly : []).slice(0, hours)
  const temps = []
  const hums = []
  let precipSum = 0
  let hotHours = 0
  let wetHours = 0

  for (const item of list) {
    const t = Number(item?.temperature)
    const h = Number(item?.humidity)
    const p = Number(item?.precipitation)
    if (Number.isFinite(t)) temps.push(t)
    if (Number.isFinite(h)) hums.push(h)
    if (Number.isFinite(p)) precipSum += p
    if (Number.isFinite(t) && t >= 32) hotHours += 1
    if (Number.isFinite(h) && h >= 85) wetHours += 1
  }

  const avg = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null)
  return {
    precipSum: Math.round(precipSum * 10) / 10,
    tempAvg: avg(temps),
    humidityAvg: avg(hums),
    hotHours,
    wetHours,
    sampleHours: list.length
  }
}

/**
 * 取最近一次灌溉时间。
 * @param {{ time?: string, action?: string }[]} actions
 * @returns {Date|null}
 */
export function lastIrrigationAt(actions) {
  const list = Array.isArray(actions) ? actions : []
  let latest = null
  for (const item of list) {
    const text = String(item?.action || '')
    if (!/(灌溉|浇水|补水|水)/.test(text)) continue
    const d = item?.time ? new Date(item.time) : null
    if (d && !Number.isNaN(d.getTime()) && (!latest || d > latest)) latest = d
  }
  return latest
}

/**
 * 地块健康 / 水分 / 生长指标的气象联动推演。
 * @param {Object} field 地块（含 actions）
 * @param {{ precipSum:number, tempAvg:number|null, humidityAvg:number|null, hotHours:number, wetHours:number, sampleHours:number }} agg72
 * @returns {{ health: number|null, water: number|null, growth: number|null, computable: boolean, basis: string }}
 */
export function deriveFieldMetrics(field, agg72) {
  const noData = {
    health: null,
    water: null,
    growth: null,
    computable: false,
    basis: '气象数据不足，无法推演（需近 72 小时至少 6 个有效样本）'
  }
  if (!agg72 || !Number.isFinite(Number(agg72.tempAvg)) || Number(agg72.sampleHours) < MIN_SAMPLES) {
    return noData
  }

  const tempAvg = Number(agg72.tempAvg)
  const precipSum = Number(agg72.precipSum) || 0
  const humidityAvg = Number(agg72.humidityAvg)
  const hotHours = Number(agg72.hotHours) || 0
  const wetHours = Number(agg72.wetHours) || 0

  // 水分：基础值 + 降水补给 − 距上次灌溉天数衰减 − 高温蒸散
  const lastAt = lastIrrigationAt(field?.actions)
  const daysSince = lastAt ? (Date.now() - lastAt.getTime()) / 86400000 : null
  const sinceFactor = daysSince === null ? 4 : Math.min(10, Math.max(0, daysSince))
  const water = Math.min(98, Math.max(5, 70 + precipSum * 2.2 - sinceFactor * 4.5 - Math.max(0, tempAvg - 25) * 1.6))

  // 健康：高温时数、高湿时数、低温胁迫
  const health = Math.min(98, Math.max(20, 88 - hotHours * 1.2 - wetHours * 0.6 - Math.max(0, 30 - tempAvg) * 2))

  // 生长：积温为主，水分为辅
  const thermal = Math.min(100, Math.max(0, (tempAvg - 6) * 3.4))
  const growth = Math.min(98, Math.max(5, thermal * 0.55 + water * 0.45))

  const round = (v) => Math.round(v)
  return {
    health: round(health),
    water: round(water),
    growth: round(growth),
    computable: true,
    basis:
      `依据近 72h 气象推演：累计降水 ${precipSum.toFixed(1)}mm、` +
      `均温 ${tempAvg.toFixed(1)}℃` +
      (Number.isFinite(humidityAvg) ? `、均湿 ${humidityAvg.toFixed(0)}%` : '') +
      `；高温(≥32℃) ${hotHours}h、高湿(≥85%) ${wetHours}h；` +
      (lastAt ? `距上次灌溉 ${daysSince.toFixed(1)} 天` : '无灌溉记录，按 4 天失墒估算')
  }
}

/**
 * 地块一句话智能建议（无数据时返回 null，由 UI 显示 '--'）。
 * @param {Object} field
 * @param {{ health: number|null, water: number|null, growth: number|null, computable: boolean }} metrics
 * @param {{ precipSum:number, tempAvg:number|null, humidityAvg:number|null, wetHours:number, hotHours:number }} [agg72]
 * @returns {string|null}
 */
export function fieldAdvice(field, metrics, agg72 = null) {
  if (!metrics || !metrics.computable) return null
  const humidity = Number(agg72?.humidityAvg)
  const water = Number(metrics.water)
  const health = Number(metrics.health)

  if (Number.isFinite(humidity) && humidity >= 85 && Number(agg72?.wetHours) >= 12) {
    return '湿度持续偏高，注意纹枯病与霜霉病巡查'
  }
  if (Number.isFinite(water) && water < 40) {
    return '土壤缺水，建议 48 小时内灌溉'
  }
  if (Number.isFinite(agg72?.hotHours) && agg72.hotHours >= 8) {
    return '高温时数偏多，建议叶面喷水降温并暂停追肥'
  }
  if (Number.isFinite(agg72?.precipSum) && agg72.precipSum >= 25) {
    return '近期降水偏多，及时清沟排水防渍害'
  }
  if (Number.isFinite(health) && health < 55) {
    return '长势偏弱，建议补充叶面肥并复核病虫害'
  }
  return '气象条件平稳，按常规农事安排即可'
}

/**
 * 首页「今日待办农事」聚合：优先用地块警报，无地块时退化为基于今日气象的通用建议。
 * @param {{ alerts?: any[], daily7?: DayWeather[], cropType?: string, fields?: any[] }} input
 * @returns {{ id: string, title: string, subtitle: string, score: number|null, level: string, reasons: string[], source: string }[]} 最多 5 条
 */
export function buildTodayTodo(input = {}) {
  const { alerts = [], daily7 = [], cropType = '', fields = [] } = input
  const today = daily7[0] || null
  const out = []

  for (const alert of Array.isArray(alerts) ? alerts.slice(0, 5) : []) {
    const name = alert?.field_name || alert?.name || alert?.field_id || '地块'
    const type = alert?.alert_type || alert?.type || '农事提醒'
    const level = alert?.risk_level || alert?.level || '低风险'
    const msg = alert?.message || alert?.suggestion || alert?.advice || ''
    out.push({
      id: `alert_${alert?.field_id || name}_${type}`,
      title: `${name} · ${type}`,
      subtitle: msg || `风险等级：${level}`,
      score: null,
      level,
      reasons: msg ? [msg] : [],
      source: 'alert'
    })
  }

  if (out.length) return out.slice(0, 5)

  // 无地块警报：基于今日气象给出 3 项通用建议（标注为通用）
  const genericOps = ['喷药', '灌溉', '采收']
  for (const op of genericOps) {
    const cell = scoreDay(op, today)
    if (!cell || cell.score === null) continue
    out.push({
      id: `generic_${op}`,
      title: `今日${op}${cropType ? `（${cropType}）` : ''}`,
      subtitle: cell.reasons[0] || '',
      score: cell.score,
      level: cell.level,
      reasons: cell.reasons,
      source: 'rule'
    })
  }

  if (!out.length && Array.isArray(fields) && fields.length) {
    out.push({
      id: 'no_weather',
      title: '气象数据暂不可用',
      subtitle: '无法推演今日农事，请稍后重试或手动选择地区',
      score: null,
      level: 'unknown',
      reasons: [],
      source: 'none'
    })
  }

  return out.slice(0, 5)
}

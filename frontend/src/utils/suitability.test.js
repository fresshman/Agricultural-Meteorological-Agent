import { describe, it, expect } from 'vitest'
import {
  OPERATIONS,
  OPERATION_RULES,
  MIN_SAMPLES,
  MIN_PARTIAL_SAMPLES,
  scoreDay,
  levelOf,
  buildWeekMatrix,
  aggregateHours,
  lastIrrigationAt,
  deriveFieldMetrics,
  fieldAdvice,
  buildTodayTodo
} from './suitability.js'

const PERFECT = {
  date: '2026-10-14', label: '今天',
  tempMax: 25, tempMin: 15, tempAvg: 21,
  humidityAvg: 70, precipSum: 0, windMax: 2, hours: 12
}
const AWFUL = {
  date: '2026-10-15', label: '明天',
  tempMax: 42, tempMin: 35, tempAvg: 40,
  humidityAvg: 98, precipSum: 30, windMax: 12, hours: 24
}

describe('utils/suitability · 常量', () => {
  it('7 类农事操作与后端口径一致', () => {
    expect(OPERATIONS).toEqual(['播种', '移栽', '授粉', '喷药', '追肥', '采收', '灌溉'])
  })

  it('每个操作都有 icon/desc/四要素阈值', () => {
    for (const op of OPERATIONS) {
      const r = OPERATION_RULES[op]
      expect(r, op).toBeTruthy()
      expect(typeof r.icon).toBe('string')
      expect(typeof r.desc).toBe('string')
      expect(r.temp.ideal).toHaveLength(2)
      expect(r.temp.hard).toHaveLength(2)
      expect(r.temp.weight).toBeGreaterThan(0)
    }
  })

  it('MIN_SAMPLES = 6', () => {
    expect(MIN_SAMPLES).toBe(6)
  })

  it('MIN_PARTIAL_SAMPLES = 1（当天进行中只要求有样本）', () => {
    expect(MIN_PARTIAL_SAMPLES).toBe(1)
  })
})

describe('utils/suitability · 当天进行中（partial）', () => {
  // 线上真实场景：今天只可能拿到"此刻到今晚"的时次（傍晚打开仅 4~5 条），
  // 旧逻辑用完整日的 6 条去卡 → 7 类操作全部 null → 首页"今日农事建议"永久卡在加载态
  it('partial 日样本 3 条也能出分（不再卡"气象数据加载中"）', () => {
    const r = scoreDay('播种', { ...PERFECT, hours: 3, partial: true })
    expect(r.score).toBe(100)
    expect(r.level).toBe('good')
  })

  it('partial 日样本 1 条即可评估', () => {
    expect(scoreDay('播种', { ...PERFECT, hours: 1, partial: true }).score).toBe(100)
  })

  it('partial 日但完全没样本（hours=0）→ 仍判样本不足', () => {
    expect(scoreDay('播种', { ...PERFECT, hours: 0, partial: true })).toEqual({
      score: null, level: 'unknown', reasons: ['预报样本不足，暂不评估'], source: 'rule'
    })
  })

  it('非 partial 的完整日口径不变：hours<6 仍不出分', () => {
    expect(scoreDay('播种', { ...PERFECT, hours: 3 }).score).toBeNull()
    expect(scoreDay('播种', { ...PERFECT, hours: 3, partial: false }).score).toBeNull()
  })

  it('buildWeekMatrix 对 partial 首列出分、其余不可靠日仍为 null', () => {
    const days = [
      { ...PERFECT, hours: 5, partial: true },
      { ...PERFECT, hours: 2 }
    ]
    const { rows } = buildWeekMatrix(days, ['播种'])
    expect(rows[0].cells[0].score).toBe(100)
    expect(rows[0].cells[1].score).toBeNull()
  })
})

describe('utils/suitability · scoreDay 评分推演', () => {
  it('理想日 → 100 分 good', () => {
    expect(scoreDay('播种', PERFECT)).toEqual({
      score: 100, level: 'good', reasons: ['气象条件总体有利于播种'], source: 'rule'
    })
  })

  it('恶劣日 → 14 分 bad（28+36+10+12 四项扣满），reasons 最多 3 条', () => {
    const r = scoreDay('播种', AWFUL)
    expect(r.score).toBe(14)
    expect(r.level).toBe('bad')
    expect(r.reasons).toHaveLength(3)
    expect(r.source).toBe('rule')
  })

  it('温度超硬区间给满惩罚（播种 temp.weight=28）', () => {
    expect(scoreDay('播种', { ...PERFECT, tempAvg: 40 }).score).toBe(72)
  })

  it('样本不足（hours<6）→ score null + 说明原因', () => {
    expect(scoreDay('播种', { ...PERFECT, hours: 4 })).toEqual({
      score: null, level: 'unknown', reasons: ['预报样本不足，暂不评估'], source: 'rule'
    })
  })

  it('未知操作 / 空日期 → score null', () => {
    expect(scoreDay('不存在', PERFECT)).toEqual({ score: null, level: 'unknown', reasons: [], source: 'rule' })
    expect(scoreDay('播种', null)).toEqual({ score: null, level: 'unknown', reasons: [], source: 'rule' })
  })

  it('灌溉 wet-good：降水越多越不需要灌溉', () => {
    const dry = scoreDay('灌溉', { ...PERFECT, tempAvg: 26, precipSum: 0 })
    expect(dry.score).toBe(100)
    expect(dry.reasons[0]).toContain('土壤失墒')
    const wet = scoreDay('灌溉', { ...PERFECT, tempAvg: 26, precipSum: 20 })
    expect(wet.score).toBe(56) // 100 - linearPenalty(20,0,10,44)=44
    expect(wet.reasons[0]).toContain('自然降水已可满足需求')
  })

  it('追肥 moderate-good：小雨有利、暴雨流失', () => {
    const light = scoreDay('追肥', { ...PERFECT, tempAvg: 20, precipSum: 2 })
    expect(light.score).toBe(100)
    expect(light.reasons[0]).toContain('利于肥料溶解下渗')
    const heavy = scoreDay('追肥', { ...PERFECT, tempAvg: 20, precipSum: 30 })
    expect(heavy.score).toBe(62) // 100 - linearPenalty(30,3,20,38)=38
    expect(heavy.reasons[0]).toContain('养分流失')
  })
})

describe('utils/suitability · levelOf 分档口径（与 risk.js 一致）', () => {
  it('阈值边界', () => {
    expect(levelOf(100)).toBe('good')
    expect(levelOf(75)).toBe('good')
    expect(levelOf(74)).toBe('ok')
    expect(levelOf(50)).toBe('ok')
    expect(levelOf(49)).toBe('care')
    expect(levelOf(25)).toBe('care')
    expect(levelOf(24)).toBe('bad')
    expect(levelOf(0)).toBe('bad')
  })

  it('非数值 → unknown', () => {
    expect(levelOf(undefined)).toBe('unknown')
    expect(levelOf('abc')).toBe('unknown')
    expect(levelOf(NaN)).toBe('unknown')
  })
})

describe('utils/suitability · buildWeekMatrix 矩阵', () => {
  it('7 操作 × N 天，天数截断到 7', () => {
    const days = Array.from({ length: 9 }, (_, i) => ({ ...PERFECT, date: `2026-10-${10 + i}` }))
    const m = buildWeekMatrix(days)
    expect(m.operations).toEqual(OPERATIONS)
    expect(m.days).toHaveLength(7)
    expect(m.rows).toHaveLength(7)
    expect(m.rows[0].op).toBe('播种')
    expect(m.rows[0].icon).toBe('Sunny')
    expect(m.rows[0].cells).toHaveLength(7)
    expect(m.rows[0].cells[0].score).toBe(100)
  })

  it('非数组入参 → 空矩阵', () => {
    const m = buildWeekMatrix(null)
    expect(m.days).toEqual([])
    expect(m.rows.every((r) => r.cells.length === 0)).toBe(true)
  })
})

describe('utils/suitability · aggregateHours 逐时聚合', () => {
  const hourly = [
    { temperature: 20, humidity: 50, precipitation: 0.5 },
    { temperature: 33, humidity: 85, precipitation: 0.7 },
    { temperature: 31, humidity: 90, precipitation: 0.2 },
    { temperature: 28, humidity: 60, precipitation: 0 },
    { temperature: 25, humidity: 55, precipitation: 1.1 },
    { temperature: 30, humidity: 70, precipitation: 0.3 }
  ]

  it('均值 / 累计 / 高温高湿时数 / 样本数', () => {
    const agg = aggregateHours(hourly)
    expect(agg.precipSum).toBe(2.8)
    expect(agg.tempAvg).toBeCloseTo(27.83, 2)
    expect(agg.humidityAvg).toBeCloseTo(68.33, 2)
    expect(agg.hotHours).toBe(1) // 33 ≥ 32
    expect(agg.wetHours).toBe(2) // 85 / 90 ≥ 85
    expect(agg.sampleHours).toBe(6)
  })

  it('hours 参数限制取数窗口', () => {
    const agg = aggregateHours(hourly, 2)
    expect(agg.sampleHours).toBe(2)
    expect(agg.tempAvg).toBe(26.5)
  })

  it('非数组入参 → 全零/null', () => {
    expect(aggregateHours(null)).toEqual({
      precipSum: 0, tempAvg: null, humidityAvg: null, hotHours: 0, wetHours: 0, sampleHours: 0
    })
  })

  it('非法字段被忽略', () => {
    expect(aggregateHours([{ temperature: 'x', humidity: undefined, precipitation: 'y' }])).toEqual({
      precipSum: 0, tempAvg: null, humidityAvg: null, hotHours: 0, wetHours: 0, sampleHours: 1
    })
  })
})

describe('utils/suitability · lastIrrigationAt 最近灌溉', () => {
  it('取灌溉类动作中最新时间', () => {
    const at = lastIrrigationAt([
      { time: '2026-10-10T08:00:00', action: '施肥' },
      { time: '2026-10-12T08:00:00', action: '灌溉' },
      { time: '2026-10-11T08:00:00', action: '浇水' }
    ])
    expect(at).toBeInstanceOf(Date)
    expect(at.toISOString().slice(0, 10)).toBe('2026-10-12')
  })

  it('非灌溉动作 / 非法时间被忽略', () => {
    expect(lastIrrigationAt([{ time: '2026-10-10T08:00:00', action: '施肥' }])).toBeNull()
    expect(lastIrrigationAt([{ time: 'not-a-date', action: '灌溉' }])).toBeNull()
  })

  it('非数组入参 → null', () => {
    expect(lastIrrigationAt(null)).toBeNull()
    expect(lastIrrigationAt(undefined)).toBeNull()
  })
})

describe('utils/suitability · deriveFieldMetrics 地块指标推演', () => {
  it('样本不足 → computable=false，指标全 null', () => {
    expect(deriveFieldMetrics({ actions: [] }, {
      precipSum: 0, tempAvg: null, humidityAvg: null, hotHours: 0, wetHours: 0, sampleHours: 3
    })).toEqual({
      health: null, water: null, growth: null, computable: false,
      basis: '气象数据不足，无法推演（需近 72 小时至少 6 个有效样本）'
    })
  })

  it('可计算 → 三项指标符合推演公式 + basis 可解释', () => {
    const agg = { precipSum: 5, tempAvg: 24, humidityAvg: 60, hotHours: 0, wetHours: 1, sampleHours: 20 }
    const m = deriveFieldMetrics({ actions: [] }, agg)
    expect(m.computable).toBe(true)
    expect(m.water).toBe(63) // 70 + 5*2.2 - 4*4.5 - 0
    expect(m.health).toBe(75) // 88 - 0 - 1*0.6 - 6*2 = 75.4
    expect(m.growth).toBe(62) // (24-6)*3.4*0.55 + 63*0.45 = 62.01
    expect(m.basis).toContain('依据近 72h 气象推演')
    expect(m.basis).toContain('无灌溉记录，按 4 天失墒估算')
  })

  it('有灌溉记录 → basis 标注距上次灌溉天数', () => {
    const agg = { precipSum: 5, tempAvg: 24, humidityAvg: 60, hotHours: 0, wetHours: 1, sampleHours: 20 }
    const m = deriveFieldMetrics(
      { actions: [{ time: new Date(Date.now() - 86400000).toISOString(), action: '灌溉' }] },
      agg
    )
    expect(m.computable).toBe(true)
    expect(m.basis).toContain('距上次灌溉')
  })
})

describe('utils/suitability · fieldAdvice 地块建议', () => {
  const base = { precipSum: 0, tempAvg: 22, humidityAvg: 60, hotHours: 0, wetHours: 0, sampleHours: 20 }
  const metricsOf = (agg) => deriveFieldMetrics({ actions: [] }, agg)

  it('不可计算 → null', () => {
    expect(fieldAdvice({}, { computable: false, water: null })).toBeNull()
  })

  it('缺水 → 建议 48h 内灌溉', () => {
    const agg = { ...base, tempAvg: 35 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('土壤缺水，建议 48 小时内灌溉')
  })

  it('持续高湿 → 病虫害巡查', () => {
    const agg = { ...base, tempAvg: 20, humidityAvg: 90, wetHours: 12 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('湿度持续偏高，注意纹枯病与霜霉病巡查')
  })

  it('高温时数多 → 叶面喷水降温', () => {
    const agg = { ...base, tempAvg: 28, hotHours: 10 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('高温时数偏多，建议叶面喷水降温并暂停追肥')
  })

  it('降水偏多 → 清沟排水', () => {
    const agg = { ...base, precipSum: 30 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('近期降水偏多，及时清沟排水防渍害')
  })

  it('长势弱 → 补叶面肥', () => {
    // health = 88 - 6*1.2 - 12*0.6 - (30-20)*2 = 53.6 → 54 < 55
    const agg = { ...base, tempAvg: 20, hotHours: 6, wetHours: 12 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('长势偏弱，建议补充叶面肥并复核病虫害')
  })

  it('平稳 → 常规安排', () => {
    const agg = { ...base, precipSum: 1 }
    expect(fieldAdvice({}, metricsOf(agg), agg)).toBe('气象条件平稳，按常规农事安排即可')
  })
})

describe('utils/suitability · buildTodayTodo 今日待办', () => {
  it('有地块警报 → 直接映射，最多 5 条', () => {
    const alerts = Array.from({ length: 7 }, (_, i) => ({
      field_id: `f${i}`, field_name: `地块${i}`, alert_type: '干旱预警', risk_level: '高风险', message: '建议立即灌溉'
    }))
    const todo = buildTodayTodo({ alerts })
    expect(todo).toHaveLength(5)
    expect(todo[0]).toMatchObject({
      id: 'alert_f0_干旱预警',
      title: '地块0 · 干旱预警',
      subtitle: '建议立即灌溉',
      level: '高风险',
      source: 'alert'
    })
  })

  it('无警报 → 基于今日气象的通用三项', () => {
    const todo = buildTodayTodo({ daily7: [{ ...PERFECT, tempAvg: 22 }], cropType: '水稻' })
    expect(todo.map((t) => t.id)).toEqual(['generic_喷药', 'generic_灌溉', 'generic_采收'])
    expect(todo[0].title).toBe('今日喷药（水稻）')
    expect(todo.every((t) => t.score === 100)).toBe(true)
    expect(todo[1].subtitle).toContain('土壤失墒')
  })

  it('无气象 + 有地块 → 提示数据不可用', () => {
    const todo = buildTodayTodo({ daily7: [], fields: [{}] })
    expect(todo).toHaveLength(1)
    expect(todo[0]).toMatchObject({ id: 'no_weather', level: 'unknown', source: 'none' })
  })

  it('全空 → 空数组', () => {
    expect(buildTodayTodo()).toEqual([])
    expect(buildTodayTodo({})).toEqual([])
  })
})

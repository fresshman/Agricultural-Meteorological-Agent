import { describe, it, expect } from 'vitest'
import { CROP_TYPES, getCropStages } from './crops.js'
import {
  CROP_PHENOLOGY,
  cropName,
  buildGrowthModel,
  stageForDate
} from './growth.js'

function isoDaysAgo(days) {
  const d = new Date(Date.now() - days * 86400000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

describe('utils/crops · 作物与阶段', () => {
  it('22 种作物都有阶段序列，且首末阶段为播种/成熟', () => {
    expect(CROP_TYPES).toHaveLength(22)
    for (const crop of CROP_TYPES) {
      const stages = getCropStages(crop)
      expect(stages.length, crop).toBeGreaterThanOrEqual(4)
      expect(stages[0], crop).toBe('播种期')
      expect(stages[stages.length - 1], crop).toBe('成熟期')
    }
    expect(getCropStages('不存在的作物')).toEqual([])
  })
})

describe('utils/growth · 作物识别与物候', () => {
  it('每种作物都有物候配置，阶段序列与 crops.js 完全一致', () => {
    for (const crop of CROP_TYPES) {
      const pheno = CROP_PHENOLOGY[crop]
      expect(pheno, crop).toBeTruthy()
      expect(pheno.stages.map((s) => s.name), crop).toEqual(getCropStages(crop))
    }
  })

  it('阶段区间从 0 连续铺到 1', () => {
    for (const crop of CROP_TYPES) {
      const stages = CROP_PHENOLOGY[crop].stages
      expect(stages[0].startFrac).toBe(0)
      expect(stages[stages.length - 1].endFrac).toBe(1)
      for (let i = 1; i < stages.length; i++) {
        expect(stages[i].startFrac).toBeCloseTo(stages[i - 1].endFrac, 10)
      }
    }
  })

  it('别名归一：西红柿/土豆/燕麦/稻谷', () => {
    expect(cropName('西红柿')).toBe('番茄')
    expect(cropName('土豆')).toBe('马铃薯')
    expect(cropName('燕麦')).toBe('莜麦')
    expect(cropName('稻谷')).toBe('水稻')
    expect(cropName('玉米')).toBe('玉米')
    expect(cropName('外星作物')).toBe('')
    expect(cropName('')).toBe('')
  })
})

describe('utils/growth · 生长模型', () => {
  it('22 种作物都能出模型，阶段不会是 undefined', () => {
    for (const crop of CROP_TYPES) {
      const m = buildGrowthModel({ crop, stage: getCropStages(crop)[0] }, { available: false })
      expect(m, crop).not.toBeNull()
      expect(m.cropLabel).toBe(crop)
      expect(typeof m.currentStage).toBe('string')
      expect(m.currentStage.length).toBeGreaterThan(0)
      // 出生即首阶段
      expect(m.currentStage).toBe(getCropStages(crop)[0])
    }
  })

  it('用户填写的阶段优先于日期推演', () => {
    const m = buildGrowthModel(
      { crop: '玉米', stage: '抽雄期', planted_at: isoDaysAgo(90) },
      { available: false }
    )
    expect(m.currentStage).toBe('抽雄期')
    expect(m.currentFrac).toBeGreaterThan(0.5)
  })

  it('未知作物返回 null，不编造曲线', () => {
    expect(buildGrowthModel({ crop: '外星作物' }, { available: false })).toBeNull()
  })

  it('stageForDate 与播种天数一致', () => {
    expect(stageForDate('玉米', isoDaysAgo(0))).toBe('播种期')
    expect(stageForDate('玉米', isoDaysAgo(200))).toBe('成熟期')
    expect(stageForDate('玉米', isoDaysAgo(100))).toBe('灌浆期')
    expect(stageForDate('外星作物', isoDaysAgo(10))).toBe('')
    expect(stageForDate('玉米', '')).toBe('')
  })
})

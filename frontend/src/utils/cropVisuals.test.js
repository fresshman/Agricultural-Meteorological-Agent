import { describe, it, expect } from 'vitest'
import { CROP_TYPES } from '@/utils/crops'
import {
  VISUAL_STAGES,
  MORPHOLOGY_FAMILIES,
  CROP_MORPHOLOGY,
  stageFromName,
  resolveVisualStage,
  getCropVisual,
  hash01
} from '@/utils/cropVisuals'

describe('cropVisuals · 22 种作物到 8 个形态族的映射', () => {
  it('每种作物都有族归属，且族名都合法', () => {
    expect(Object.keys(CROP_MORPHOLOGY).sort()).toEqual([...CROP_TYPES].sort())
    for (const crop of CROP_TYPES) {
      expect(MORPHOLOGY_FAMILIES[CROP_MORPHOLOGY[crop]]).toBeTruthy()
    }
  })

  it('8 个族都至少有作物，避免出现画不出来的空族', () => {
    const used = new Set(Object.values(CROP_MORPHOLOGY))
    expect(used.size).toBe(8)
    for (const key of Object.keys(MORPHOLOGY_FAMILIES)) expect(used.has(key)).toBe(true)
  })
})

describe('cropVisuals · 阶段解析', () => {
  it('阶段名按语义归类', () => {
    expect(stageFromName('播种期')).toBe(0)
    expect(stageFromName('出苗期')).toBe(0)
    expect(stageFromName('幼苗期')).toBe(1)
    expect(stageFromName('分蘖期')).toBe(2)
    expect(stageFromName('莲座期')).toBe(2)
    expect(stageFromName('抽薹期')).toBe(3)
    expect(stageFromName('开花期')).toBe(3)
    expect(stageFromName('灌浆期')).toBe(4)
    expect(stageFromName('结球期')).toBe(4)
    expect(stageFromName('成熟期')).toBe(5)
    expect(stageFromName('已收获')).toBe(5)
    expect(stageFromName('')).toBeNull()
    expect(stageFromName('说不清的阶段')).toBeNull()
  })

  it('表单阶段优先于生长模型', () => {
    expect(resolveVisualStage({ stage: '开花期', growth: { currentStage: '灌浆期' } })).toBe(3)
  })

  it('无表单阶段时用模型阶段，模型已收获直接到成熟', () => {
    expect(resolveVisualStage({ growth: { currentStage: '抽穗期' } })).toBe(3)
    expect(resolveVisualStage({ growth: { harvested: true, currentStage: '成熟期' } })).toBe(5)
  })

  it('模型只有连续进度时按比例落到 6 段', () => {
    expect(resolveVisualStage({ growth: { currentStage: '', currentFrac: 0.05 } })).toBe(0)
    expect(resolveVisualStage({ growth: { currentStage: '', currentFrac: 0.5 } })).toBe(3)
    expect(resolveVisualStage({ growth: { currentStage: '', currentFrac: 0.99 } })).toBe(5)
  })

  it('完全没信息时取折中阶段 3', () => {
    expect(resolveVisualStage()).toBe(3)
    expect(resolveVisualStage({ stage: '', growth: null })).toBe(3)
  })
})

describe('cropVisuals · 绘制参数', () => {
  it('别称归一到本名与对应族', () => {
    expect(getCropVisual('西红柿').crop).toBe('番茄')
    expect(getCropVisual('西红柿').family).toBe('solanaceous')
    expect(getCropVisual('土豆').family).toBe('tuber')
    expect(getCropVisual('燕麦').family).toBe('dense_grass')
    expect(getCropVisual('苞米').family).toBe('tall_grass')
  })

  it('未知作物回退到叶菜形态，不抛错', () => {
    const v = getCropVisual('神秘作物')
    expect(v.family).toBe('rosette_leaf')
    expect(v.stage).toBe(3)
    expect(v.height).toBeGreaterThan(0)
  })

  it('成熟阶段叶子转干枯色，花/果标记与阶段一致', () => {
    const mature = getCropVisual('玉米', { stage: '成熟期' })
    expect(mature.mature).toBe(true)
    expect(mature.colors.leaf).toBe('var(--gold-500)')
    expect(mature.colors.stem).toBe('var(--gold-700)')

    const flowering = getCropVisual('玉米', { stage: '抽雄期' })
    expect(flowering.flowering).toBe(true)
    expect(flowering.fruiting).toBe(false)

    const fruiting = getCropVisual('玉米', { stage: '灌浆期' })
    expect(fruiting.fruiting).toBe(true)
  })

  it('同族作物用果色区分', () => {
    expect(getCropVisual('葡萄', { stage: '灌浆期' }).colors.fruit).toBe('var(--state-purple)')
    expect(getCropVisual('柑橘', { stage: '灌浆期' }).colors.fruit).toBe('var(--state-orange)')
  })

  it('摆动相位由 seed 决定且稳定在 0~1', () => {
    expect(hash01('field-1')).toBe(hash01('field-1'))
    expect(hash01('field-1')).toBeGreaterThanOrEqual(0)
    expect(hash01('field-1')).toBeLessThan(1)
    const a = getCropVisual('玉米', { seed: 'f1' })
    const b = getCropVisual('玉米', { seed: 'f1' })
    expect(a.sway.phase).toBe(b.sway.phase)
  })

  it('6 个阶段全覆盖且下标合法', () => {
    for (const crop of CROP_TYPES) {
      const v = getCropVisual(crop)
      expect(v.stage).toBeGreaterThanOrEqual(0)
      expect(v.stage).toBeLessThan(VISUAL_STAGES.length)
      expect(v.stageLabel).toBe(VISUAL_STAGES[v.stage].label)
    }
  })
})

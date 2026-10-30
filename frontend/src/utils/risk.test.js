import { describe, it, expect, vi } from 'vitest'
import {
  riskMeta,
  riskBadgeStyle,
  riskRank,
  elTagType,
  suitabilityMeta,
  suitabilityLegend,
  hexToRgbTriplet
} from './risk.js'

// riskBadgeStyle 内部经 getComputedStyle 读 CSS 变量；jsdom 无样式表，
// mock 成确定色值，保证 rgba 三元组可精确断言
const TOKEN_HEX = {
  '--state-success': '#2e7d32',
  '--state-info': '#1565c0',
  '--state-warning': '#f9a825',
  '--state-orange': '#ef6c00',
  '--state-danger': '#c62828'
}

describe('utils/risk · riskMeta 等级归一化（全站风险色单源）', () => {
  it('气象四级预警口径：蓝/黄/橙/红 → info/warning/orange/danger', () => {
    expect(riskMeta('蓝色预警').key).toBe('info')
    expect(riskMeta('黄色预警').key).toBe('warning')
    expect(riskMeta('橙色预警').key).toBe('orange')
    expect(riskMeta('红色预警').key).toBe('danger')
  })

  it('病虫害四级风险口径：低/中/高/极高 → success/warning/orange/danger', () => {
    expect(riskMeta('低风险').key).toBe('success')
    expect(riskMeta('中风险').key).toBe('warning')
    expect(riskMeta('高').key).toBe('orange')
    expect(riskMeta('极高风险').key).toBe('danger')
  })

  it('英文 key 未登记在 LEVEL_MAP → 兜底 success（已知 doc/impl 差异：FieldCard.vue:21 传入英文 key，会全部回落为「正常」绿色，发布报告已标注）', () => {
    expect(riskMeta('danger').key).toBe('success')
    expect(riskMeta('success').key).toBe('success')
  })

  it('去后缀二次匹配：带「级/风险」等后缀也能命中', () => {
    expect(riskMeta('蓝色级').key).toBe('info')
    expect(riskMeta('黄色风险').key).toBe('warning')
  })

  it('空值 / 未知值兜底为 success（正常）', () => {
    expect(riskMeta(undefined).key).toBe('success')
    expect(riskMeta('').key).toBe('success')
    expect(riskMeta('   ').key).toBe('success')
    expect(riskMeta('完全未知的等级').key).toBe('success')
  })

  it('输入带空白字符时先 trim', () => {
    expect(riskMeta('  高风险  ').key).toBe('danger')
  })

  it('元数据完整：label/token/color/icon/rank', () => {
    expect(riskMeta('红色预警')).toMatchObject({
      key: 'danger',
      label: '高危',
      token: '--state-danger',
      color: 'var(--state-danger)',
      icon: 'CircleCloseFilled',
      rank: 4
    })
    expect(riskMeta('正常').label).toBe('正常')
    expect(riskMeta('橙色预警').label).toBe('较重')
  })
})

describe('utils/risk · riskRank / elTagType', () => {
  it('rank 随严重程度单调递增', () => {
    expect(riskRank('正常')).toBe(0)
    expect(riskRank('一般')).toBe(1)
    expect(riskRank('注意')).toBe(1) // 「注意」归 info 档
    expect(riskRank('黄色预警')).toBe(2)
    expect(riskRank('橙色预警')).toBe(3)
    expect(riskRank('红色预警')).toBe(4)
  })

  it('elTagType：EP 只有四档，orange 归入 warning', () => {
    expect(elTagType('正常')).toBe('success')
    expect(elTagType('一般')).toBe('info')
    expect(elTagType('黄色预警')).toBe('warning')
    expect(elTagType('橙色预警')).toBe('warning')
    expect(elTagType('红色预警')).toBe('danger')
  })
})

describe('utils/risk · suitabilityMeta 分档（PRD 6.4.6 阈值口径）', () => {
  it('75–100 → good 适宜', () => {
    expect(suitabilityMeta(100)).toMatchObject({ level: 'good', label: '适宜', key: 'success', percent: 100 })
    expect(suitabilityMeta(75)).toMatchObject({ level: 'good', label: '适宜' })
  })

  it('50–74 → ok 尚可', () => {
    expect(suitabilityMeta(74)).toMatchObject({ level: 'ok', label: '尚可', key: 'info' })
    expect(suitabilityMeta(50)).toMatchObject({ level: 'ok', label: '尚可' })
  })

  it('25–49 → care 谨慎（key=warning 但色板用 orange）', () => {
    const m = suitabilityMeta(49)
    expect(m.level).toBe('care')
    expect(m.label).toBe('谨慎')
    expect(m.key).toBe('warning')
    expect(m.token).toBe('--state-orange')
    expect(m.color).toBe('var(--state-orange)')
    expect(suitabilityMeta(25).level).toBe('care')
  })

  it('0–24 → bad 不宜', () => {
    expect(suitabilityMeta(24)).toMatchObject({ level: 'bad', label: '不宜', key: 'danger' })
    expect(suitabilityMeta(0).level).toBe('bad')
  })

  it('undefined / NaN / 非数字字符串 → unknown 暂无', () => {
    expect(suitabilityMeta(undefined)).toMatchObject({ level: 'unknown', label: '暂无', key: 'info', percent: 0 })
    expect(suitabilityMeta(NaN).level).toBe('unknown')
    expect(suitabilityMeta('abc').level).toBe('unknown')
  })

  it('null 走 Number(null)=0 → bad 不宜（已知 coercing 口径，调用方需自行判空）', () => {
    expect(suitabilityMeta(null)).toMatchObject({ level: 'bad', label: '不宜', key: 'danger', percent: 0 })
  })

  it('超范围分值被钳制到 0~100', () => {
    expect(suitabilityMeta(120)).toMatchObject({ level: 'good', percent: 100 })
    expect(suitabilityMeta(-10)).toMatchObject({ level: 'bad', percent: 0 })
  })
})

describe('utils/risk · suitabilityLegend / hexToRgbTriplet / riskBadgeStyle', () => {
  it('图例四档区间与色板', () => {
    const legend = suitabilityLegend()
    expect(legend.map((x) => x.label)).toEqual(['适宜', '尚可', '谨慎', '不宜'])
    expect(legend.map((x) => x.range)).toEqual(['75–100', '50–74', '25–49', '0–24'])
    expect(legend[2].color).toBe('var(--state-orange)')
    expect(legend[3].color).toBe('var(--state-danger)')
  })

  it('hexToRgbTriplet：3 位/6 位 hex 与 rgb()/rgba()', () => {
    expect(hexToRgbTriplet('#fff')).toBe('255, 255, 255')
    expect(hexToRgbTriplet('#2e7d32')).toBe('46, 125, 50')
    expect(hexToRgbTriplet('rgb(1, 2, 3)')).toBe('1, 2, 3')
    expect(hexToRgbTriplet('rgba(1,2,3,0.5)')).toBe('1, 2, 3')
  })

  it('hexToRgbTriplet：非法输入返回 null', () => {
    expect(hexToRgbTriplet('')).toBeNull()
    expect(hexToRgbTriplet(null)).toBeNull()
    expect(hexToRgbTriplet('#xyz')).toBeNull()
    expect(hexToRgbTriplet('#12345')).toBeNull()
    expect(hexToRgbTriplet('red')).toBeNull()
  })

  it('riskBadgeStyle：同色 12% 底 + 1px 边框 + 同色文字', () => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (token) => TOKEN_HEX[token] || ''
    })
    expect(riskBadgeStyle('红色预警')).toEqual({
      background: 'rgba(198, 40, 40, 0.12)',
      border: '1px solid rgba(198, 40, 40, 0.3)',
      color: 'var(--state-danger)'
    })
    const custom = riskBadgeStyle('正常', { alpha: 0.5, borderAlpha: 1 })
    expect(custom.background).toBe('rgba(46, 125, 50, 0.5)')
    expect(custom.border).toBe('1px solid rgba(46, 125, 50, 1)')
    vi.restoreAllMocks()
  })

  it('riskBadgeStyle：CSS 变量取不到时回退中性灰，不抛错', () => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({ getPropertyValue: () => '' })
    const style = riskBadgeStyle('橙色预警')
    expect(style.background).toBe('rgba(107, 124, 115, 0.12)')
    expect(style.color).toBe('var(--state-orange)')
    vi.restoreAllMocks()
  })
})

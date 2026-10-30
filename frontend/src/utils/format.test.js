import { describe, it, expect } from 'vitest'
import {
  makeId,
  formatTime,
  formatDate,
  formatDateTime,
  formatMonthDay,
  toDayKey,
  weekdayLabel,
  formatDuration,
  relativeDayLabel,
  formatPercent,
  formatNumber,
  clamp,
  beaufortLevel,
  normalizeWindDirection,
  groupByDay,
  dayGroupLabel,
  greeting,
  copyText
} from './format.js'

describe('utils/format · makeId', () => {
  it('默认 m_ 前缀 + 时间戳随机后缀', () => {
    const id = makeId()
    expect(id.startsWith('m_')).toBe(true)
    expect(id.length).toBeGreaterThan(8)
  })

  it('自定义前缀', () => {
    expect(makeId('sess').startsWith('sess_')).toBe(true)
  })

  it('连续生成不重复', () => {
    const ids = new Set(Array.from({ length: 200 }, () => makeId()))
    expect(ids.size).toBe(200)
  })
})

describe('utils/format · 日期时间格式化', () => {
  it('formatTime HH:mm / 带秒 / 非法兜底', () => {
    expect(formatTime(new Date(2026, 0, 1, 9, 5, 3))).toBe('09:05')
    expect(formatTime(new Date(2026, 0, 1, 9, 5, 3), true)).toBe('09:05:03')
    expect(formatTime('bad')).toBe('--:--')
    expect(formatTime(null)).toBe('--:--')
  })

  it('formatDate / formatDateTime / formatMonthDay / toDayKey', () => {
    const d = new Date(2026, 9, 4, 8, 7)
    expect(formatDate(d)).toBe('2026-10-04')
    expect(formatDateTime(d)).toBe('2026-10-04 08:07')
    expect(formatMonthDay(d)).toBe('10-04')
    expect(toDayKey(d)).toBe('2026-10-04')
    expect(formatDate(null)).toBe('----')
  })

  it('weekdayLabel 中文星期', () => {
    expect(weekdayLabel(new Date(2024, 0, 1))).toBe('星期一') // 2024-01-01 是星期一
    expect(weekdayLabel(null)).toBe('')
  })

  it('relativeDayLabel 今天/明天/后天/昨天/MM-DD', () => {
    const now = new Date()
    const day = 86400000
    expect(relativeDayLabel(now)).toBe('今天')
    expect(relativeDayLabel(new Date(now.getTime() + day))).toBe('明天')
    expect(relativeDayLabel(new Date(now.getTime() + 2 * day))).toBe('后天')
    expect(relativeDayLabel(new Date(now.getTime() - day))).toBe('昨天')
    expect(relativeDayLabel(new Date(now.getTime() + 10 * day))).toMatch(/^\d{2}-\d{2}$/)
    expect(relativeDayLabel(null)).toBe('--')
  })

  it('dayGroupLabel 今天/昨天/更早', () => {
    const now = new Date()
    expect(dayGroupLabel(now)).toBe('今天')
    expect(dayGroupLabel(new Date(now.getTime() - 86400000))).toBe('昨天')
    expect(dayGroupLabel(new Date(now.getTime() - 3 * 86400000))).toBe('更早')
    expect(dayGroupLabel(null)).toBe('更早')
  })
})

describe('utils/format · 数值格式化', () => {
  it('formatDuration 分档', () => {
    expect(formatDuration(500)).toBe('500ms')
    expect(formatDuration(3200)).toBe('3.2s')
    expect(formatDuration(60000)).toBe('1分')
    expect(formatDuration(72000)).toBe('1分12秒')
    expect(formatDuration(-1)).toBe('--')
    expect(formatDuration('abc')).toBe('--')
    expect(formatDuration(NaN)).toBe('--')
  })

  it('formatPercent 小数/百分数双兼容', () => {
    expect(formatPercent(0.82)).toBe('82%')
    expect(formatPercent(82)).toBe('82%')
    expect(formatPercent(0.826, 1)).toBe('82.6%')
    expect(formatPercent('x')).toBe('--')
  })

  it('formatNumber 小数位与空值口径', () => {
    expect(formatNumber(3.14159)).toBe('3.1')
    expect(formatNumber(3.14159, 3)).toBe('3.142')
    expect(formatNumber(undefined)).toBe('--')
    expect(formatNumber('abc')).toBe('--')
    expect(formatNumber(null)).toBe('0.0') // Number(null)=0 的已知口径
  })

  it('clamp 钳制，非法值回退 min', () => {
    expect(clamp(5, 0, 3)).toBe(3)
    expect(clamp(-5, 0, 3)).toBe(0)
    expect(clamp(2, 0, 3)).toBe(2)
    expect(clamp('x', 1, 3)).toBe(1)
  })
})

describe('utils/format · groupByDay 按日分组', () => {
  it('按自然日分组、升序、跳过非法日期', () => {
    const d1 = new Date(2026, 9, 4, 8, 0)
    const d2 = new Date(2026, 9, 4, 20, 0)
    const d3 = new Date(2026, 9, 5, 9, 0)
    const groups = groupByDay(
      [{ v: 'a', t: d3 }, { v: 'b', t: d2 }, { v: 'c', t: d1 }, { v: 'bad', t: 'nope' }],
      (x) => x.t
    )
    expect(groups).toHaveLength(2)
    expect(groups[0].key).toBe('2026-10-04')
    expect(groups[0].items.map((i) => i.v)).toEqual(['b', 'c'])
    expect(groups[1].key).toBe('2026-10-05')
    expect(groups[1].items).toHaveLength(1)
  })

  it('空列表 → 空数组', () => {
    expect(groupByDay([], (x) => x)).toEqual([])
    expect(groupByDay(null, (x) => x)).toEqual([])
  })
})

describe('utils/format · greeting / copyText', () => {
  it('greeting 分时段', () => {
    expect(greeting(new Date(2026, 0, 1, 3, 0))).toBe('夜深了')
    expect(greeting(new Date(2026, 0, 1, 8, 0))).toBe('早上好')
    expect(greeting(new Date(2026, 0, 1, 12, 0))).toBe('中午好')
    expect(greeting(new Date(2026, 0, 1, 15, 0))).toBe('下午好')
    expect(greeting(new Date(2026, 0, 1, 20, 0))).toBe('晚上好')
  })

  it('copyText 空文本直接返回 false', async () => {
    await expect(copyText('')).resolves.toBe(false)
    await expect(copyText(null)).resolves.toBe(false)
  })
})

describe('utils/format · beaufortLevel 风速折算风级', () => {
  it('真实接口样本：ws10m=1.4496349 m/s → 1 级（不再显示原始浮点）', () => {
    expect(beaufortLevel(1.4496349)).toBe(1)
    expect(beaufortLevel(2.2959425)).toBe(2)
  })

  it('分档边界', () => {
    expect(beaufortLevel(0)).toBe(0)
    expect(beaufortLevel(0.29)).toBe(0)
    expect(beaufortLevel(0.3)).toBe(1)
    expect(beaufortLevel(1.59)).toBe(1)
    expect(beaufortLevel(1.6)).toBe(2)
    expect(beaufortLevel(3.4)).toBe(3)
    expect(beaufortLevel(32.6)).toBe(12)
    expect(beaufortLevel(45)).toBe(12)
  })

  it('非法值 → null（由 UI 决定不展示）', () => {
    expect(beaufortLevel(null)).toBeNull()
    expect(beaufortLevel(undefined)).toBeNull()
    expect(beaufortLevel('')).toBeNull()
    expect(beaufortLevel('abc')).toBeNull()
    expect(beaufortLevel(-1)).toBeNull()
  })
})

describe('utils/format · normalizeWindDirection 风向规整', () => {
  it('缺测占位统一为空串（避免出现"未知 1级"）', () => {
    for (const raw of ['', '   ', null, undefined, '未知', '未知风向', '不详', '暂无', '无', 'unknown', 'UNKNOWN', 'n/a', 'N/A', '--', '—', '-']) {
      expect(normalizeWindDirection(raw), String(raw)).toBe('')
    }
  })

  it('真实风向原样返回并去空格', () => {
    expect(normalizeWindDirection('东北风')).toBe('东北风')
    expect(normalizeWindDirection(' 东南风 ')).toBe('东南风')
    expect(normalizeWindDirection('西')).toBe('西')
  })
})

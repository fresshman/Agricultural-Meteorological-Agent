import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 掉 @/api：只关心按日聚合与 partial 标记，不真的发请求
vi.mock('@/api', () => ({
  weatherApi: { get: vi.fn() },
  locationApi: { coordinates: vi.fn(), provinces: vi.fn(), cities: vi.fn(), districts: vi.fn() },
  authApi: { me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() },
  chatApi: { send: vi.fn(), stream: vi.fn(), submitFeedback: vi.fn(), feedbackStats: vi.fn() }
}))

import { weatherApi } from '@/api'
import { useWeatherStore } from '@/stores/weather'
import { scoreDay } from '@/utils/suitability'

/**
 * 构造一条与线上同形态的样本（气象源给的是原始浮点）。
 * 用本地 Date 生成再转 ISO，保证按日分组落在预期的自然日。
 */
function sample(dayOffset, hour) {
  const d = new Date()
  d.setDate(d.getDate() + dayOffset)
  d.setHours(hour, 0, 0, 0)
  return {
    timestamp: d.toISOString(),
    temperature: 20.91401,
    humidity: 47.057594,
    precipitation: 0,
    wind_speed: 2.2959425,
    wind_direction: ''
  }
}

describe('weather store · daily7 按日聚合与「当天进行中」标记', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('线上真实形态（昨天残留 3 条 + 今天 24 条）→ 今天必须 partial 且可评估', async () => {
    const items = [
      // 起报时刻早于当前时刻时，序列里会带上昨天的尾巴（实测 API 如此）
      sample(-1, 21), sample(-1, 22), sample(-1, 23),
      ...Array.from({ length: 24 }, (_, h) => sample(0, h)),
      ...Array.from({ length: 24 }, (_, h) => sample(1, h))
    ]
    weatherApi.get.mockResolvedValue({ status: true, data: items, is_mock: false })

    const weather = useWeatherStore()
    await weather.loadWeather(168)

    expect(weather.available).toBe(true)
    const [yesterday, today, tomorrow] = weather.daily7
    expect(yesterday.partial).toBe(false)
    expect(today.partial).toBe(true)
    expect(tomorrow.partial).toBe(false)
    expect(yesterday.hours).toBe(3)
    expect(today.hours).toBe(24)

    // 关键回归：昨天那 3 条永远算不出分（旧 bug 正是把它当成"今天"），
    // 而"今天"必须算得出分，首页"今日农事建议"才不会卡在加载态。
    expect(scoreDay('播种', yesterday).score).toBeNull()
    expect(scoreDay('播种', today).score).not.toBeNull()
  })

  it('当天样本不足 6 条（傍晚打开）也仍可评估', async () => {
    const items = [...Array.from({ length: 4 }, (_, i) => sample(0, 19 + i))]
    weatherApi.get.mockResolvedValue({ status: true, data: items, is_mock: false })

    const weather = useWeatherStore()
    await weather.loadWeather(168)

    expect(weather.daily7[0].partial).toBe(true)
    expect(weather.daily7[0].hours).toBe(4)
    expect(scoreDay('播种', weather.daily7[0]).score).not.toBeNull()
  })

  it('气象源不可用（status=false）→ 清空数据，不残留旧值', async () => {
    weatherApi.get.mockResolvedValue({ status: false, data: [], message: '未获取到气象数据' })

    const weather = useWeatherStore()
    const ok = await weather.loadWeather(168)

    expect(ok).toBe(false)
    expect(weather.available).toBe(false)
    expect(weather.daily7).toEqual([])
    expect(weather.current).toBeNull()
  })
})

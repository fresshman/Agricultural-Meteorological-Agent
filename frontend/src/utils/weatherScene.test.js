import { describe, it, expect } from 'vitest'
import { hourOf, isNightHour, resolveWeatherScene } from './weatherScene.js'

const NOON = new Date('2026-11-06T12:00:00+08:00')

describe('utils/weatherScene · 昼夜', () => {
  it('19 点到次日 6 点前算夜间', () => {
    expect(isNightHour(5)).toBe(true)
    expect(isNightHour(6)).toBe(false)
    expect(isNightHour(18)).toBe(false)
    expect(isNightHour(19)).toBe(true)
  })

  it('时间戳缺失或非法时回退到当前时刻', () => {
    expect(hourOf(null, NOON)).toBe(12)
    expect(hourOf('not-a-date', NOON)).toBe(12)
    expect(hourOf('2026-11-06T22:30:00+08:00', NOON)).toBe(22)
  })
})

describe('utils/weatherScene · 场景判定', () => {
  it('天气现象文本优先：雨/雪/雾/云', () => {
    expect(resolveWeatherScene({ conditionText: '雷阵雨' }, NOON).scene).toBe('rain')
    expect(resolveWeatherScene({ conditionText: '小雪' }, NOON).scene).toBe('snow')
    expect(resolveWeatherScene({ conditionText: '雾' }, NOON).scene).toBe('fog')
    expect(resolveWeatherScene({ conditionText: '多云' }, NOON).scene).toBe('cloudy')
  })

  it('无天气现象文本时按降水量推演，低温降水为雪', () => {
    expect(resolveWeatherScene({ precipitation: 0.6, temperature: 20 }, NOON).scene).toBe('rain')
    expect(resolveWeatherScene({ precipitation: 3, temperature: -2 }, NOON).scene).toBe('snow')
  })

  it('高湿低风推雾，高湿有风推阴，大风推风场景', () => {
    expect(resolveWeatherScene({ humidity: 95, windSpeed: 2 }, NOON).scene).toBe('fog')
    expect(resolveWeatherScene({ humidity: 85, windSpeed: 3 }, NOON).scene).toBe('cloudy')
    expect(resolveWeatherScene({ humidity: 60, windSpeed: 9 }, NOON).scene).toBe('wind')
  })

  it('干燥平静为晴天场景', () => {
    expect(resolveWeatherScene({ humidity: 55, windSpeed: 2, precipitation: 0 }, NOON).scene).toBe('clear')
  })
})

describe('utils/weatherScene · 强度与动效参数', () => {
  it('降水强度按 mm/h 分级，粒子数量随之增加', () => {
    const light = resolveWeatherScene({ precipitation: 1, temperature: 20 }, NOON)
    const moderate = resolveWeatherScene({ precipitation: 5, temperature: 20 }, NOON)
    const heavy = resolveWeatherScene({ precipitation: 20, temperature: 20 }, NOON)
    expect(light.intensity).toBe('light')
    expect(moderate.intensity).toBe('moderate')
    expect(heavy.intensity).toBe('heavy')
    expect(light.particles).toBeLessThan(moderate.particles)
    expect(moderate.particles).toBeLessThan(heavy.particles)
  })

  it('只有天气文本没有降水量时按小雨处理', () => {
    const s = resolveWeatherScene({ conditionText: '小雨' }, NOON)
    expect(s.intensity).toBe('light')
    expect(s.particles).toBeGreaterThan(0)
  })

  it('无降水时不下粒子', () => {
    expect(resolveWeatherScene({ humidity: 55, windSpeed: 2 }, NOON).particles).toBe(0)
  })

  it('风越大云漂移越快、雨丝越斜', () => {
    const calm = resolveWeatherScene({ windSpeed: 2 }, NOON)
    const windy = resolveWeatherScene({ windSpeed: 10 }, NOON)
    expect(windy.driftSeconds).toBeLessThan(calm.driftSeconds)
    expect(windy.tilt).toBeGreaterThan(calm.tilt)
  })

  it('湿度越高云层越厚', () => {
    const dry = resolveWeatherScene({ humidity: 50 }, NOON)
    const damp = resolveWeatherScene({ humidity: 78 }, NOON)
    expect(damp.cloudOpacity).toBeGreaterThan(dry.cloudOpacity)
  })

  it('夜间标记跟随样本时间戳', () => {
    expect(resolveWeatherScene({ timestamp: '2026-11-06T22:00:00+08:00' }, NOON).night).toBe(true)
    expect(resolveWeatherScene({ timestamp: '2026-11-06T10:00:00+08:00' }, NOON).night).toBe(false)
  })

  it('夜间与降雨场景标记为深色底，雪/雾/晴保持浅色底', () => {
    expect(resolveWeatherScene({ timestamp: '2026-11-06T22:00:00+08:00' }, NOON).onDark).toBe(true)
    expect(resolveWeatherScene({ precipitation: 1 }, NOON).onDark).toBe(true)
    expect(resolveWeatherScene({ precipitation: 1, temperature: -2 }, NOON).onDark).toBe(false)
    expect(resolveWeatherScene({ humidity: 95, windSpeed: 1 }, NOON).onDark).toBe(false)
    expect(resolveWeatherScene({ temperature: 25, humidity: 50 }, NOON).onDark).toBe(false)
    // 夜间雾仍用浅色雾幕，不能切白字
    expect(
      resolveWeatherScene({ humidity: 95, windSpeed: 1, timestamp: '2026-11-06T22:00:00+08:00' }, NOON).onDark
    ).toBe(false)
  })
})

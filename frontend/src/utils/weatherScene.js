/**
 * 气象场景判定：把原始气象样本映射成背景动效所需的场景与强度参数。
 *
 * 判定顺序：气象源给出的天气现象文本最可信（有则直接用）；当前订阅拿不到
 * 天气现象时，退回实测降水量 / 湿度 / 风速推演，绝不用随机数造天气。
 */

function num(value) {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

/** 取样本所在小时；时间戳缺失或非法时回退到当前时刻 */
export function hourOf(timestamp, now = new Date()) {
  const d = timestamp === null || timestamp === undefined ? now : new Date(timestamp)
  const date = Number.isNaN(d.getTime()) ? now : d
  return date.getHours()
}

/** 夜间定义：19:00–05:59，用于切换星空/月亮与冷色调 */
export function isNightHour(hour) {
  return hour < 6 || hour >= 19
}

/** 降水强度按小时降水量分级（mm/h，气象上小雨≤2.5、中雨≤8、其余为大到暴雨） */
const RAIN_COUNTS = { light: 18, moderate: 36, heavy: 56 }
const SNOW_COUNTS = { light: 24, moderate: 44, heavy: 60 }

/**
 * @param {{
 *   temperature?: number|null,
 *   humidity?: number|null,
 *   windSpeed?: number|null,
 *   precipitation?: number|null,
 *   conditionText?: string,
 *   timestamp?: string|null
 * }} input 当前时次气象样本
 * @param {Date} [now] 仅当 timestamp 缺失时用于判断昼夜，便于测试注入
 */
export function resolveWeatherScene(input = {}, now = new Date()) {
  const t = num(input.temperature)
  const hum = num(input.humidity)
  const wind = num(input.windSpeed)
  const p = num(input.precipitation)
  const text = String(input.conditionText || '')

  let scene
  if (/雪|冰粒|冻雨/.test(text)) scene = 'snow'
  else if (/雨|雷|暴雨|阵雨/.test(text)) scene = 'rain'
  else if (/雾|霾|沙尘/.test(text)) scene = 'fog'
  else if (/云|阴/.test(text)) scene = 'cloudy'
  else if (p !== null && p >= 0.1) scene = t !== null && t <= 1 ? 'snow' : 'rain'
  else if (hum !== null && hum >= 92 && (wind === null || wind <= 4)) scene = 'fog'
  else if (wind !== null && wind >= 8) scene = 'wind'
  else if (hum !== null && hum >= 80) scene = 'cloudy'
  else scene = 'clear'

  const precip = p ?? 0
  let intensity = ''
  if (scene === 'rain' || scene === 'snow') {
    // 只有天气现象文本、没有降水量时按小雨/小雪处理
    intensity = precip >= 8 ? 'heavy' : precip >= 2.5 ? 'moderate' : 'light'
  }
  const counts = scene === 'snow' ? SNOW_COUNTS : RAIN_COUNTS

  const cloudBase =
    scene === 'cloudy' || scene === 'fog'
      ? 0.32
      : clamp(0.1 + (Math.max(0, (hum ?? 55) - 55) / 45) * 0.35, 0.1, 0.4)
  // 降水场景让云退后一步，把视觉焦点留给雨丝/雪花
  const cloudOpacity = scene === 'rain' || scene === 'snow' ? Math.min(cloudBase, 0.24) : cloudBase

  const night = isNightHour(hourOf(input.timestamp, now))

  return {
    scene,
    intensity,
    night,
    /**
     * 背景是否会铺成深色：夜间与降雨场景在浅色主题下用深色底，
     * 文字必须同步切浅色；雪/晴/阴等浅色场景继续用深色字。
     * 雾天即使入夜也保持浅色雾幕，避免深底上盖白雾导致对比度反转。
     */
    onDark: scene === 'rain' || (night && scene !== 'fog'),
    /** 粒子数量：无降水场景为 0 */
    particles: intensity ? counts[intensity] : 0,
    /** 云层漂移一圈的秒数：风越大越快，无风也保留缓慢漂移 */
    driftSeconds: Math.round(clamp(54 - (wind ?? 0) * 5, 16, 54)),
    /** 云层浓度：湿度越高越厚，阴天/雾天单独上调 */
    cloudOpacity: Math.round(cloudOpacity * 100) / 100,
    /** 雨丝倾角：风越大越斜 */
    tilt: Math.round(clamp(3 + (wind ?? 0) * 1.2, 3, 20)),
    /** 风线数量分级：0 无风、1 大风、2 强风 */
    gustLevel: wind !== null && wind >= 8 ? (wind >= 12 ? 2 : 1) : 0
  }
}

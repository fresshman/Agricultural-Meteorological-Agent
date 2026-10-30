/**
 * 日期 / 时间 / 数值格式化工具（纯函数，不依赖 store 与 DOM）
 */

const PAIR = (n) => String(n).padStart(2, '0')

/**
 * 安全地把入参转成 Date。
 * @param {number|string|Date} input
 * @returns {Date|null}
 */
export function toDate(input) {
  if (input === null || input === undefined || input === '') return null
  const d = input instanceof Date ? input : new Date(input)
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * HH:mm（可选秒）
 * @param {number|string|Date} ts
 * @param {boolean} [withSeconds=false]
 * @returns {string} 无法解析时返回 '--:--'
 */
export function formatTime(ts, withSeconds = false) {
  const d = toDate(ts)
  if (!d) return '--:--'
  const base = `${PAIR(d.getHours())}:${PAIR(d.getMinutes())}`
  return withSeconds ? `${base}:${PAIR(d.getSeconds())}` : base
}

/**
 * YYYY-MM-DD
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function formatDate(ts) {
  const d = toDate(ts)
  if (!d) return '----'
  return `${d.getFullYear()}-${PAIR(d.getMonth() + 1)}-${PAIR(d.getDate())}`
}

/**
 * YYYY-MM-DD HH:mm
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function formatDateTime(ts) {
  const d = toDate(ts)
  if (!d) return '----'
  return `${formatDate(d)} ${formatTime(d)}`
}

/**
 * MM-DD
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function formatMonthDay(ts) {
  const d = toDate(ts)
  if (!d) return '--'
  return `${PAIR(d.getMonth() + 1)}-${PAIR(d.getDate())}`
}

/**
 * 自然日键（用于按日分组，粒度无关）。
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function toDayKey(ts) {
  return formatDate(ts)
}

const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

/**
 * 星期几中文。
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function weekdayLabel(ts) {
  const d = toDate(ts)
  if (!d) return ''
  return WEEKDAYS[d.getDay()]
}

/**
 * 时长：小于 60s 显示 `3.2s`，否则 `1分12秒`。
 * @param {number} ms 毫秒；非法值返回 '--'
 * @returns {string}
 */
export function formatDuration(ms) {
  const n = Number(ms)
  if (!Number.isFinite(n) || n < 0) return '--'
  if (n < 1000) return `${Math.round(n)}ms`
  if (n < 60000) return `${(n / 1000).toFixed(1)}s`
  const min = Math.floor(n / 60000)
  const sec = Math.round((n % 60000) / 1000)
  return sec ? `${min}分${sec}秒` : `${min}分`
}

/**
 * 相对日标签：今天 / 明天 / 后天 / 昨天 / MM-DD。
 * @param {number|string|Date} ts
 * @returns {string}
 */
export function relativeDayLabel(ts) {
  const d = toDate(ts)
  if (!d) return '--'
  const today = new Date()
  const a = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const b = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diff = Math.round((b.getTime() - a.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  if (diff === 2) return '后天'
  if (diff === -1) return '昨天'
  return formatMonthDay(d)
}

/**
 * 0~1 的小数转百分比字符串。
 * @param {number} v 0~1；已是百分数（>1）时按原值处理
 * @param {number} [digits=0]
 * @returns {string} 如 '82%'；非法值返回 '--'
 */
export function formatPercent(v, digits = 0) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '--'
  const pct = n > 1 ? n : n * 100
  return `${pct.toFixed(digits)}%`
}

/**
 * 数值格式化：保留指定小数位，非法值返回 '--'（全站空值统一口径）。
 * @param {number|string|null} v
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatNumber(v, digits = 1) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '--'
  return n.toFixed(digits)
}

/**
 * 把数值限制在区间内。
 * @param {number} v
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(v, min, max) {
  const n = Number(v)
  if (!Number.isFinite(n)) return min
  return Math.min(max, Math.max(min, n))
}

/** 蒲福风级上限（m/s）表：第 i 项为第 i 级的上界 */
const BEAUFORT_UPPER = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.6]

/**
 * 风速 m/s → 蒲福风级（0~12）。
 * 气象接口给的 ws10m 单位是 m/s，直接拼"级"会得到"1.4496349级"这类错值，必须先换算。
 * @param {number|string|null} ms 风速（m/s）
 * @returns {number|null} 非法值返回 null
 */
export function beaufortLevel(ms) {
  // Number(null) === 0、Number('') === 0：缺测值必须先挡掉，否则会显示成"风力0级"
  if (ms === null || ms === undefined || ms === '') return null
  const v = Number(ms)
  if (!Number.isFinite(v) || v < 0) return null
  for (let i = 0; i < BEAUFORT_UPPER.length; i += 1) {
    if (v < BEAUFORT_UPPER[i]) return i
  }
  return 12
}

/** 缺测风向的各种写法 */
const EMPTY_DIRECTION = /^(未知|不详|暂无|未知风向|无|n\/?a|unknown|null|undefined|--|—|-)$/i

/**
 * 风向文案规整：把缺测占位（空串 / null / 未知 / unknown / -- 等）统一成 ''，
 * 由 UI 决定是否展示，避免出现"未知 1 级"这类真实数据里并不存在的风向。
 * @param {string|null|undefined} raw
 * @returns {string} 可展示的风向；缺测时返回 ''
 */
export function normalizeWindDirection(raw) {
  const s = String(raw ?? '').trim()
  if (!s) return ''
  return EMPTY_DIRECTION.test(s) ? '' : s
}

/**
 * 按自然日分组（粒度无关聚合用）。
 * @template T
 * @param {T[]} list
 * @param {(item: T) => number|string|Date} dateOf 取时间戳的函数
 * @returns {{ key: string, date: Date, items: T[] }[]} 按日期升序
 */
export function groupByDay(list, dateOf) {
  const map = new Map()
  for (const item of list || []) {
    const d = toDate(dateOf(item))
    if (!d) continue
    const key = toDayKey(d)
    if (!map.has(key)) map.set(key, { key, date: d, items: [] })
    map.get(key).items.push(item)
  }
  return [...map.values()].sort((a, b) => a.date.getTime() - b.date.getTime())
}

/**
 * 会话列表用的时间分组标签：今天 / 昨天 / 更早。
 * @param {number|string|Date} ts
 * @returns {'今天'|'昨天'|'更早'}
 */
export function dayGroupLabel(ts) {
  const d = toDate(ts)
  if (!d) return '更早'
  const today = new Date()
  const a = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const b = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diff = Math.round((b.getTime() - a.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === -1) return '昨天'
  return '更早'
}

/**
 * 据当前时间给出问候语。
 * @param {Date} [now=new Date()]
 * @returns {string}
 */
export function greeting(now = new Date()) {
  const h = now.getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
}

/**
 * 复制文本到剪贴板（带 execCommand 兜底，兼容微信内置浏览器）。
 * @param {string} text
 * @returns {Promise<boolean>} 是否成功
 */
export async function copyText(text) {
  const value = String(text ?? '')
  if (!value) return false
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value)
      return true
    }
  } catch (err) {
    /* 降级到 execCommand */
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = value
    ta.setAttribute('readonly', 'readonly')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch (err) {
    return false
  }
}

/**
 * 生成短 id（非加密用途，仅用于前端消息/会话标识）。
 * @param {string} [prefix='m']
 * @returns {string}
 */
export function makeId(prefix = 'm') {
  const rand = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${Date.now().toString(36)}${rand}`
}

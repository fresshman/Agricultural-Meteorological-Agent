/**
 * 风险等级 / 适宜度分值 ↔ 颜色 Token / 图标 / Element Tag 类型
 * --------------------------------------------------------------------------
 * 全站唯一来源：任何组件都不许再写 if-else 色值分支。
 */

/**
 * @typedef {'success'|'info'|'warning'|'orange'|'danger'} RiskKey
 * @typedef {'good'|'ok'|'care'|'bad'|'unknown'} SuitabilityLevel
 */

/** 风险等级 → 归一化 key 的映射表（覆盖气象四级预警与病虫害四级风险两套口径） */
const LEVEL_MAP = {
  // 正常 / 无风险
  正常: 'success',
  无: 'success',
  低: 'success',
  低风险: 'success',
  适宜: 'success',
  良好: 'success',
  绿色: 'success',
  // 一般 / 蓝色
  一般: 'info',
  注意: 'info',
  蓝色: 'info',
  蓝色预警: 'info',
  // 黄色
  中风险: 'warning',
  中等: 'warning',
  黄色: 'warning',
  黄色预警: 'warning',
  较重: 'warning',
  // 橙色
  橙色: 'orange',
  橙色预警: 'orange',
  高: 'orange',
  // 红色
  高风险: 'danger',
  极高风险: 'danger',
  极高: 'danger',
  红色: 'danger',
  红色预警: 'danger',
  高危: 'danger',
  紧急: 'danger'
}

/** 每个风险 key 的视觉元数据 */
const RISK_META = {
  success: {
    key: 'success',
    label: '正常',
    token: '--state-success',
    color: 'var(--state-success)',
    icon: 'SuccessFilled',
    rank: 0
  },
  info: {
    key: 'info',
    label: '一般',
    token: '--state-info',
    color: 'var(--state-info)',
    icon: 'InfoFilled',
    rank: 1
  },
  warning: {
    key: 'warning',
    label: '注意',
    token: '--state-warning',
    color: 'var(--state-warning)',
    icon: 'WarningFilled',
    rank: 2
  },
  orange: {
    key: 'orange',
    label: '较重',
    token: '--state-orange',
    color: 'var(--state-orange)',
    icon: 'WarnTriangleFilled',
    rank: 3
  },
  danger: {
    key: 'danger',
    label: '高危',
    token: '--state-danger',
    color: 'var(--state-danger)',
    icon: 'CircleCloseFilled',
    rank: 4
  }
}

/**
 * 风险等级（中文或已归一化的 key）→ 视觉元数据。
 * @param {string} [level] 如 '高风险' / '橙色预警' / 'danger'
 * @returns {{ key: RiskKey, label: string, token: string, color: string, icon: string, rank: number }}
 */
export function riskMeta(level) {
  if (!level) return RISK_META.success
  const raw = String(level).trim()
  // 先按原值匹配，再去除「预警」「风险」「级」等后缀做二次匹配
  const key = LEVEL_MAP[raw] || LEVEL_MAP[raw.replace(/(预警|风险|级|色)$/g, '')]
  return RISK_META[key] || RISK_META.success
}

/**
 * 四级风险色卡行内样式：`同色 12% 底 + 同色 1px 边框 + 同色文字`。
 * @param {string} [level]
 * @param {{ alpha?: number, borderAlpha?: number }} [opts]
 * @returns {{ background: string, border: string, color: string }}
 */
export function riskBadgeStyle(level, opts = {}) {
  const meta = riskMeta(level)
  const alpha = opts.alpha ?? 0.12
  const borderAlpha = opts.borderAlpha ?? 0.3
  const rgb = tokenToRgbTriplet(meta.token)
  return {
    background: `rgba(${rgb}, ${alpha})`,
    border: `1px solid rgba(${rgb}, ${borderAlpha})`,
    color: meta.color
  }
}

/**
 * 适宜度分值 → 分档元数据（PRD 6.4.6：适宜 75–100 / 尚可 50–74 / 谨慎 25–49 / 不宜 0–24）。
 * @param {number|null|undefined} score 0~100
 * @returns {{ level: SuitabilityLevel, label: string, key: RiskKey, token: string, color: string, icon: string, percent: number }}
 */
export function suitabilityMeta(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) {
    return {
      level: 'unknown',
      label: '暂无',
      key: 'info',
      token: '--text-disabled',
      color: 'var(--text-disabled)',
      icon: 'QuestionFilled',
      percent: 0
    }
  }
  const v = Math.min(100, Math.max(0, n))
  if (v >= 75) return { level: 'good', label: '适宜', key: 'success', token: '--state-success', color: 'var(--state-success)', icon: 'SuccessFilled', percent: Math.round(v) }
  if (v >= 50) return { level: 'ok', label: '尚可', key: 'info', token: '--state-info', color: 'var(--state-info)', icon: 'InfoFilled', percent: Math.round(v) }
  if (v >= 25) return { level: 'care', label: '谨慎', key: 'warning', token: '--state-orange', color: 'var(--state-orange)', icon: 'WarningFilled', percent: Math.round(v) }
  return { level: 'bad', label: '不宜', key: 'danger', token: '--state-danger', color: 'var(--state-danger)', icon: 'CircleCloseFilled', percent: Math.round(v) }
}

/**
 * 适宜度四档的静态图例（供日历/矩阵页渲染图例）。
 * @returns {{ level: SuitabilityLevel, label: string, range: string, color: string }[]}
 */
export function suitabilityLegend() {
  return [
    { level: 'good', label: '适宜', range: '75–100', color: 'var(--state-success)' },
    { level: 'ok', label: '尚可', range: '50–74', color: 'var(--state-info)' },
    { level: 'care', label: '谨慎', range: '25–49', color: 'var(--state-orange)' },
    { level: 'bad', label: '不宜', range: '0–24', color: 'var(--state-danger)' }
  ]
}

/**
 * 风险等级 → Element Plus Tag 的 `type`（EP 只有四档，橙色归入 warning）。
 * @param {string} [level]
 * @returns {'success'|'info'|'warning'|'danger'|'primary'}
 */
export function elTagType(level) {
  const map = { success: 'success', info: 'info', warning: 'warning', orange: 'warning', danger: 'danger' }
  return map[riskMeta(level).key] || 'info'
}

/**
 * 风险排序权重（降序排列时用 b - a）。
 * @param {string} [level]
 * @returns {number}
 */
export function riskRank(level) {
  return riskMeta(level).rank
}

/** CSS 变量 → 'r, g, b' 三元组（用于 rgba() 拼接；取不到时回退到中性灰） */
function tokenToRgbTriplet(token) {
  if (typeof window === 'undefined' || !window.getComputedStyle) return '107, 124, 115'
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  return hexToRgbTriplet(value) || '107, 124, 115'
}

/**
 * HEX / rgb() 字符串 → 'r, g, b'。
 * @param {string} value
 * @returns {string|null}
 */
export function hexToRgbTriplet(value) {
  if (!value) return null
  const text = value.trim()
  if (text.startsWith('#')) {
    let hex = text.slice(1)
    if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('')
    if (hex.length !== 6 || /[^0-9a-fA-F]/.test(hex)) return null
    const n = parseInt(hex, 16)
    return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`
  }
  const m = text.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i)
  if (m) return `${m[1]}, ${m[2]}, ${m[3]}`
  return null
}

/**
 * localStorage 读写封装层（全站唯一入口）
 *
 * 设计要点：
 * 1. Key 统一前缀 `agri:`，集中在 KEYS 常量中定义，禁止在业务代码里硬编码字符串；
 * 2. 所有读写包 try/catch —— 隐私模式 / 禁用 Cookie / 配额溢出时都不能抛异常；
 * 3. `QuotaExceededError` 时先通知调用方淘汰数据（一次重试），仍失败则降级为「内存模式」；
 * 4. SCHEMA_VERSION 变化时清空业务 key 并以默认值重建，避免旧结构污染。
 */

/** @enum {string} localStorage 键名常量 */
export const KEYS = {
  VERSION: 'agri:version',
  SESSIONS: 'agri:sessions',
  THEME: 'agri:theme',
  LOCATION: 'agri:location',
  PREFS: 'agri:prefs'
}

/** 数据结构版本号；升级结构时 +1 即可触发一次性重建 */
export const SCHEMA_VERSION = 1

/** 旧版本遗留的裸字符串会话 id（只读，不做删除，便于回退版本） */
export const LEGACY_SESSION_KEY = 'agri_session_id'

/** 内存模式：localStorage 不可用时兜底，进程内可用、关闭即丢 */
let memoryMode = false
const memoryStore = new Map()

/** @returns {boolean} 当前是否处于内存模式 */
export function isMemoryMode() {
  return memoryMode
}

function enterMemoryMode() {
  if (memoryMode) return
  memoryMode = true
  console.warn('[storage] localStorage 不可用，已降级为内存模式（本次会话内有效）')
}

function isQuotaError(err) {
  if (!err) return false
  const name = err.name || ''
  return (
    name === 'QuotaExceededError' ||
    name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
    err.code === 22 ||
    err.code === 1014
  )
}

/**
 * 读取原始字符串。
 * @param {string} key
 * @returns {string|null}
 */
export function readRaw(key) {
  if (memoryMode) return memoryStore.has(key) ? memoryStore.get(key) : null
  try {
    return window.localStorage.getItem(key)
  } catch (err) {
    enterMemoryMode()
    return null
  }
}

/**
 * 写入原始字符串。
 * @param {string} key
 * @param {string} value
 * @returns {boolean} 是否写入成功
 */
export function writeRaw(key, value) {
  if (memoryMode) {
    memoryStore.set(key, value)
    return true
  }
  try {
    window.localStorage.setItem(key, value)
    return true
  } catch (err) {
    if (isQuotaError(err)) return false
    enterMemoryMode()
    memoryStore.set(key, value)
    return true
  }
}

/**
 * 删除指定 key。
 * @param {string} key
 */
export function remove(key) {
  memoryStore.delete(key)
  if (memoryMode) return
  try {
    window.localStorage.removeItem(key)
  } catch (err) {
    enterMemoryMode()
  }
}

/**
 * 读取并反序列化 JSON。数据缺失 / 损坏 / 类型不符时一律返回兜底值，不抛错。
 * @param {string} key
 * @param {*} fallback 兜底值
 * @returns {*} 解析结果或兜底值
 */
export function readJSON(key, fallback = null) {
  const raw = readRaw(key)
  if (raw === null || raw === '') return fallback
  try {
    const parsed = JSON.parse(raw)
    return parsed === null || parsed === undefined ? fallback : parsed
  } catch (err) {
    console.warn(`[storage] ${key} 数据损坏，已重置为默认值`)
    remove(key)
    return fallback
  }
}

/**
 * 序列化并写入 JSON。
 * @param {string} key
 * @param {*} value
 * @param {{ onQuotaError?: () => boolean }} [opts] onQuotaError 返回 true 表示已腾出空间，可重试一次
 * @returns {boolean} 是否写入成功
 */
export function writeJSON(key, value, opts = {}) {
  let text
  try {
    text = JSON.stringify(value)
  } catch (err) {
    console.warn(`[storage] ${key} 序列化失败，已跳过写入`)
    return false
  }
  if (writeRaw(key, text)) return true

  // 配额溢出：给调用方一次「淘汰旧数据」的机会
  const freed = typeof opts.onQuotaError === 'function' ? opts.onQuotaError() === true : false
  if (freed && writeRaw(key, text)) return true

  enterMemoryMode()
  memoryStore.set(key, text)
  return false
}

/**
 * 读取旧版本遗留的裸字符串 session id（不存在时返回 null）。
 * @returns {string|null}
 */
export function readLegacySessionId() {
  if (memoryMode) return null
  try {
    return window.localStorage.getItem(LEGACY_SESSION_KEY)
  } catch (err) {
    return null
  }
}

/**
 * 版本校验与一次性迁移。应用启动时调用一次。
 * @returns {{ migrated: boolean, fromVersion: number|null }}
 */
export function migrateIfNeeded() {
  if (typeof window === 'undefined') return { migrated: false, fromVersion: null }
  const stored = readJSON(KEYS.VERSION, null)
  const fromVersion = typeof stored === 'number' ? stored : Number(stored?.v ?? NaN)

  if (Number.isFinite(fromVersion) && fromVersion === SCHEMA_VERSION) {
    return { migrated: false, fromVersion }
  }

  // 版本不符：清空业务 key，以默认值重建（保留 LEGACY_SESSION_KEY 供 chat store 迁移）
  Object.values(KEYS).forEach((key) => {
    if (key !== KEYS.VERSION) remove(key)
  })
  writeJSON(KEYS.VERSION, { v: SCHEMA_VERSION })
  return { migrated: true, fromVersion: Number.isFinite(fromVersion) ? fromVersion : null }
}

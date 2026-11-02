/**
 * localStorage 读写封装层（全站唯一入口）
 *
 * 设计要点：
 * 1. Key 统一前缀 `agri:`，集中在 KEYS 常量中定义，禁止在业务代码里硬编码字符串；
 * 2. 所有读写包 try/catch —— 隐私模式 / 禁用 Cookie / 配额溢出时都不能抛异常；
 * 3. `QuotaExceededError` 时先通知调用方淘汰数据（一次重试），仍失败则降级为「内存模式」；
 * 4. SCHEMA_VERSION 变化时清空业务 key 并以默认值重建，避免旧结构污染；
 * 5. 账号级数据（对话/位置/偏好）的 key 带 `@{userId}` 后缀，换账号即换存储，
 *    主题这类设备级偏好不分桶。
 */

/** @enum {string} localStorage 键名常量 */
export const KEYS = {
  VERSION: 'agri:version',
  SESSIONS: 'agri:sessions',
  THEME: 'agri:theme',
  LOCATION: 'agri:location',
  PREFS: 'agri:prefs'
}

/**
 * 数据结构版本号；升级结构时 +1 即可触发一次性重建。
 * v2（2026-11-02）：对话历史改为按账号分桶，老浏览器里那份「所有账号共用一把键」的历史
 * 是隔离漏洞的产物，不值得保留，抬版本即一次性作废。
 */
export const SCHEMA_VERSION = 2

/** 业务 key 的统一前缀，用于按前缀清理（含分桶后的 key） */
const KEY_PREFIX = 'agri:'

/** 最早版本留下的裸字符串会话 id，不带前缀；结构迁移时一并清除 */
const LEGACY_SESSION_KEY = 'agri_session_id'

/** 账号后缀分隔符 */
const SCOPE_SEP = '@'

/** 需要按账号隔离的 key 集合 */
const USER_SCOPED_KEYS = new Set([KEYS.SESSIONS, KEYS.PREFS, KEYS.LOCATION])

/** 账号使用记录（设备级索引，不分桶）：[{ id, lastUsed }] */
const ACCOUNTS_KEY = `${KEY_PREFIX}accounts`

/**
 * 同一浏览器最多保留最近这么多个账号的数据桶，超出的最旧桶连同会话/位置/偏好一起删除。
 * 真正的上限是浏览器按源计算的存储配额，所以写入撞配额时还会再丢一次最旧账号兜底。
 */
export const MAX_ACCOUNT_BUCKETS = 12

/** 内存模式：localStorage 不可用时兜底，进程内可用、关闭即丢 */
let memoryMode = false
const memoryStore = new Map()

/** 当前登录用户 id；null 表示未登录（此时账号级 key 落回不带后缀的原 key） */
let userScope = null

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
 * 设置当前账号作用域（登录态确认后调用；传 null 回到未登录）。
 * 同时记录该账号的使用时间，并把超出上限的最旧账号数据整桶删除。
 * @param {string|null} userId
 */
export function setUserScope(userId) {
  userScope = userId || null
  if (userScope) pruneAccountBuckets(userScope)
}

/** @returns {string|null} 当前账号 id */
export function getUserScope() {
  return userScope
}

/**
 * 把逻辑 key 解析为实际存储 key。账号级 key 在登录后带 `@{userId}` 后缀。
 * @param {string} key
 * @returns {string}
 */
export function scopedKey(key) {
  if (!userScope || !USER_SCOPED_KEYS.has(key)) return key
  return `${key}${SCOPE_SEP}${userScope}`
}

/** @returns {Array<{id: string, lastUsed: number}>} 账号使用记录 */
function readAccounts() {
  const raw = rawGet(ACCOUNTS_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((a) => a && typeof a.id === 'string') : []
  } catch (err) {
    return []
  }
}

/**
 * 删除某账号的全部账号级数据（按 `@{id}` 后缀匹配，id 是 uuid，不会误伤别的桶）。
 * @param {string} id
 */
function dropAccountBuckets(id) {
  const suffix = `${SCOPE_SEP}${id}`
  if (!memoryMode) {
    try {
      const stale = []
      for (let i = 0; i < window.localStorage.length; i += 1) {
        const k = window.localStorage.key(i) || ''
        if (k.endsWith(suffix)) stale.push(k)
      }
      stale.forEach((k) => rawDel(k))
    } catch (err) {
      enterMemoryMode()
    }
  }
  USER_SCOPED_KEYS.forEach((key) => memoryStore.delete(`${key}${suffix}`))
}

/**
 * 记录当前账号使用时间，并只保留最近 MAX_ACCOUNT_BUCKETS 个账号。
 * @param {string} activeId
 */
function pruneAccountBuckets(activeId) {
  const list = readAccounts().filter((a) => a.id !== activeId)
  // 当前账号放最前：同一毫秒内连续切号时排序时间戳相等，稳定排序才不会把刚登录的账号当成最旧丢掉
  list.unshift({ id: activeId, lastUsed: Date.now() })
  list.sort((a, b) => (b.lastUsed || 0) - (a.lastUsed || 0))
  list.slice(MAX_ACCOUNT_BUCKETS).forEach((a) => dropAccountBuckets(a.id))
  const kept = list.slice(0, MAX_ACCOUNT_BUCKETS)
  rawSet(ACCOUNTS_KEY, JSON.stringify(kept))
}

/**
 * 写入撞配额时的兜底：丢掉最近使用时间最早的那个账号（绝不动当前账号），腾出空间。
 * @param {string} activeId 当前账号
 * @returns {boolean} 是否真的丢掉了数据
 */
export function evictOldestAccountBucket(activeId) {
  const others = readAccounts().filter((a) => a.id !== activeId)
  if (!others.length) return false
  others.sort((a, b) => (a.lastUsed || 0) - (b.lastUsed || 0))
  const victim = others[0].id
  dropAccountBuckets(victim)
  rawSet(ACCOUNTS_KEY, JSON.stringify(readAccounts().filter((a) => a.id !== victim)))
  return true
}

function rawGet(key) {
  if (memoryMode) return memoryStore.has(key) ? memoryStore.get(key) : null
  try {
    return window.localStorage.getItem(key)
  } catch (err) {
    enterMemoryMode()
    return null
  }
}

function rawSet(key, value) {
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

function rawDel(key) {
  memoryStore.delete(key)
  if (memoryMode) return
  try {
    window.localStorage.removeItem(key)
  } catch (err) {
    enterMemoryMode()
  }
}

/**
 * 读取原始字符串（自动按当前账号解析 key）。
 * @param {string} key
 * @returns {string|null}
 */
export function readRaw(key) {
  return rawGet(scopedKey(key))
}

/**
 * 写入原始字符串（自动按当前账号解析 key）。
 * @param {string} key
 * @param {string} value
 * @returns {boolean} 是否写入成功
 */
export function writeRaw(key, value) {
  return rawSet(scopedKey(key), value)
}

/**
 * 删除指定 key（自动按当前账号解析 key）。
 * @param {string} key
 */
export function remove(key) {
  rawDel(scopedKey(key))
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

  // 配额溢出：先给调用方一次「本账号内淘汰旧数据」的机会
  const freed = typeof opts.onQuotaError === 'function' ? opts.onQuotaError() === true : false
  if (freed && writeRaw(key, text)) return true

  // 本账号已经淘汰到不能再淘汰：丢掉最旧的其他账号，再试一次
  if (userScope && evictOldestAccountBucket(userScope) && writeRaw(key, text)) return true

  enterMemoryMode()
  memoryStore.set(key, text)
  return false
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

  // 版本不符：清空全部业务 key（含各账号分桶、账号索引，以及最早的裸 session id），以默认值重建
  if (!memoryMode) {
    try {
      const stale = []
      for (let i = 0; i < window.localStorage.length; i += 1) {
        const k = window.localStorage.key(i) || ''
        if (k !== KEYS.VERSION && (k.startsWith(KEY_PREFIX) || k === LEGACY_SESSION_KEY)) stale.push(k)
      }
      stale.forEach((k) => rawDel(k))
    } catch (err) {
      enterMemoryMode()
    }
  }
  // 内存模式下没有可遍历的存储，按已知 key 逐个清
  Object.values(KEYS).forEach((key) => {
    if (key !== KEYS.VERSION) rawDel(key)
  })
  rawDel(LEGACY_SESSION_KEY)
  writeJSON(KEYS.VERSION, { v: SCHEMA_VERSION })
  return { migrated: true, fromVersion: Number.isFinite(fromVersion) ? fromVersion : null }
}

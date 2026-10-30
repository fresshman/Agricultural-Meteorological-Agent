import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { KEYS, SCHEMA_VERSION, LEGACY_SESSION_KEY } from './storage.js'

// memoryMode 是模块级单例，被置位后会跨用例污染；
// 每个用例通过 resetModules + 动态 import 拿全新模块实例
async function freshStorage() {
  vi.resetModules()
  return import('./storage.js')
}

function quotaError() {
  return Object.assign(new Error('quota'), { name: 'QuotaExceededError' })
}

describe('utils/storage · 常量', () => {
  it('业务 key 统一 agri: 前缀', () => {
    for (const [name, key] of Object.entries(KEYS)) {
      expect(key.startsWith('agri:'), name).toBe(true)
    }
    expect(KEYS.VERSION).toBe('agri:version')
    expect(LEGACY_SESSION_KEY).toBe('agri_session_id')
    expect(SCHEMA_VERSION).toBe(1)
  })
})

describe('utils/storage · JSON 读写', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('writeJSON / readJSON 往返', async () => {
    const s = await freshStorage()
    expect(s.writeJSON(KEYS.SESSIONS, [{ id: 's1' }])).toBe(true)
    expect(s.readJSON(KEYS.SESSIONS)).toEqual([{ id: 's1' }])
    expect(window.localStorage.getItem(KEYS.SESSIONS)).toBe('[{"id":"s1"}]')
  })

  it('readJSON 缺失 key → 兜底值', async () => {
    const s = await freshStorage()
    expect(s.readJSON('agri:nope', { d: 1 })).toEqual({ d: 1 })
    expect(s.readJSON('agri:nope')).toBeNull()
  })

  it('readJSON 数据损坏 → 兜底值并删除该 key', async () => {
    const s = await freshStorage()
    window.localStorage.setItem('agri:broken', '{oops')
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(s.readJSON('agri:broken', 'fallback')).toBe('fallback')
    expect(window.localStorage.getItem('agri:broken')).toBeNull()
    warn.mockRestore()
  })

  it('readJSON 存的是 JSON null → 兜底值', async () => {
    const s = await freshStorage()
    window.localStorage.setItem('agri:nullish', 'null')
    expect(s.readJSON('agri:nullish', 'fb')).toBe('fb')
  })

  it('writeJSON 序列化失败（循环引用）→ false', async () => {
    const s = await freshStorage()
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const circular = {}
    circular.self = circular
    expect(s.writeJSON('agri:circular', circular)).toBe(false)
    expect(window.localStorage.getItem('agri:circular')).toBeNull()
    warn.mockRestore()
  })

  it('writeRaw / readRaw / remove 基本语义', async () => {
    const s = await freshStorage()
    expect(s.writeRaw('agri:x', 'v')).toBe(true)
    expect(s.readRaw('agri:x')).toBe('v')
    expect(s.readRaw('agri:missing')).toBeNull()
    s.remove('agri:x')
    expect(s.readRaw('agri:x')).toBeNull()
  })
})

describe('utils/storage · 配额超额回退', () => {
  const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage')

  beforeEach(() => {
    window.localStorage.clear()
  })

  afterEach(() => {
    // 还原 jsdom 原生 localStorage
    if (originalDescriptor) {
      Object.defineProperty(window, 'localStorage', originalDescriptor)
    } else {
      delete window.localStorage
    }
  })

  // jsdom 的 localStorage 是 Proxy，实例级 vi.spyOn 拦截不到方法调用，
  // 这里用 Map-backed 假存储整体替换 window.localStorage，可精确注入抛错行为
  function installFakeStorage({ setItem, getItem } = {}) {
    const map = new Map()
    const fake = {
      getItem: getItem || ((k) => (map.has(k) ? map.get(k) : null)),
      // 自定义 setItem 仅用于注入抛错行为，之后仍正常写入 Map
      setItem: (k, v) => {
        if (setItem) setItem(k, v)
        map.set(k, String(v))
      },
      removeItem: (k) => { map.delete(k) },
      clear: () => { map.clear() },
      key: (i) => [...map.keys()][i] ?? null,
      get length() { return map.size }
    }
    Object.defineProperty(window, 'localStorage', { configurable: true, value: fake })
  }

  it('QuotaExceeded + onQuotaError 腾出空间 → 重试成功', async () => {
    const s = await freshStorage()
    let calls = 0
    installFakeStorage({
      setItem: () => {
        calls += 1
        if (calls === 1) throw quotaError()
      }
    })
    let freed = false
    const ok = s.writeJSON(KEYS.PREFS, { a: 1 }, {
      onQuotaError: () => {
        freed = true
        return true
      }
    })
    expect(freed).toBe(true)
    expect(ok).toBe(true)
    expect(s.readJSON(KEYS.PREFS)).toEqual({ a: 1 })
  })

  it('QuotaExceeded + 无法腾出 → 返回 false 并降级内存模式（进程内仍可读写）', async () => {
    const s = await freshStorage()
    installFakeStorage({ setItem: () => { throw quotaError() } })
    const ok = s.writeJSON(KEYS.PREFS, { a: 1 }, { onQuotaError: () => false })
    expect(ok).toBe(false)
    expect(s.isMemoryMode()).toBe(true)
    expect(s.writeRaw(KEYS.PREFS, 'mem')).toBe(true)
    expect(s.readRaw(KEYS.PREFS)).toBe('mem')
  })

  it('读取抛错（隐私模式/禁用存储）→ 降级内存模式并返回 null', async () => {
    const s = await freshStorage()
    installFakeStorage({ getItem: () => { throw new Error('denied') } })
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(s.readRaw(KEYS.THEME)).toBeNull()
    expect(s.isMemoryMode()).toBe(true)
    warn.mockRestore()
  })
})

describe('utils/storage · 版本迁移与旧版兼容', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('首次启动：迁移并写入版本', async () => {
    const s = await freshStorage()
    expect(s.migrateIfNeeded()).toEqual({ migrated: true, fromVersion: null })
    expect(window.localStorage.getItem(KEYS.VERSION)).toBe('{"v":1}')
  })

  it('版本一致：不迁移', async () => {
    const s = await freshStorage()
    s.migrateIfNeeded()
    expect(s.migrateIfNeeded()).toEqual({ migrated: false, fromVersion: 1 })
  })

  it('旧版本：清空业务 key 后以默认值重建', async () => {
    const s = await freshStorage()
    s.writeJSON(KEYS.SESSIONS, [{ id: 'old' }])
    s.writeJSON(KEYS.THEME, 'dark')
    window.localStorage.setItem(KEYS.VERSION, '0')
    const r = s.migrateIfNeeded()
    expect(r.migrated).toBe(true)
    expect(r.fromVersion).toBe(0)
    expect(s.readJSON(KEYS.SESSIONS, null)).toBeNull()
    expect(s.readJSON(KEYS.THEME, null)).toBeNull()
    expect(s.readJSON(KEYS.VERSION)).toEqual({ v: 1 })
  })

  it('readLegacySessionId 读取旧版裸字符串', async () => {
    const s = await freshStorage()
    window.localStorage.setItem(LEGACY_SESSION_KEY, 'sess_old')
    expect(s.readLegacySessionId()).toBe('sess_old')
    window.localStorage.removeItem(LEGACY_SESSION_KEY)
    expect(s.readLegacySessionId()).toBeNull()
  })
})

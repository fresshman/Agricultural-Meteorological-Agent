import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { KEYS, SCHEMA_VERSION } from './storage.js'

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
    expect(SCHEMA_VERSION).toBe(2)
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

describe('utils/storage · 账号分桶隔离', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('账号级 key 按 userId 分桶，换账号读不到别人的数据', async () => {
    const s = await freshStorage()
    s.setUserScope('u1')
    expect(s.writeJSON(KEYS.SESSIONS, { list: [{ id: 'a' }] })).toBe(true)
    expect(window.localStorage.getItem(`${KEYS.SESSIONS}@u1`)).toContain('"a"')

    s.setUserScope('u2')
    expect(s.readJSON(KEYS.SESSIONS, null)).toBeNull()

    s.setUserScope('u1')
    expect(s.readJSON(KEYS.SESSIONS).list[0].id).toBe('a')
  })

  it('主题这类设备级偏好不分桶', async () => {
    const s = await freshStorage()
    s.setUserScope('u1')
    s.writeJSON(KEYS.THEME, { v: 1, mode: 'dark' })
    expect(window.localStorage.getItem(KEYS.THEME)).toContain('dark')
    s.setUserScope('u2')
    expect(s.readJSON(KEYS.THEME).mode).toBe('dark')
  })

  it('未登录时读写落回不带后缀的原 key', async () => {
    const s = await freshStorage()
    s.writeJSON(KEYS.PREFS, { v: 1 })
    expect(window.localStorage.getItem(KEYS.PREFS)).toContain('"v"')
    expect(s.getUserScope()).toBeNull()
  })

  it('登录后只读自己的分桶，历史遗留的裸 key 不会再被任何账号读到', async () => {
    const s = await freshStorage()
    window.localStorage.setItem(KEYS.SESSIONS, JSON.stringify({ v: 1, list: [{ id: 'legacy-shared' }] }))

    s.setUserScope('u1')
    expect(s.readJSON(KEYS.SESSIONS, null)).toBeNull()
    s.setUserScope('u2')
    expect(s.readJSON(KEYS.SESSIONS, null)).toBeNull()
  })

  it('退出登录（scope 置空）后新账号看不到上一账号的分桶数据', async () => {
    const s = await freshStorage()
    s.setUserScope('u1')
    s.writeJSON(KEYS.LOCATION, { v: 1, city: '郑州市' })
    s.setUserScope(null)
    expect(s.readJSON(KEYS.LOCATION, null)).toBeNull()
  })
})

describe('utils/storage · 账号桶上限与配额兜底', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('只保留最近 MAX_ACCOUNT_BUCKETS 个账号，最旧账号整桶删除', async () => {
    const s = await freshStorage()
    const total = s.MAX_ACCOUNT_BUCKETS + 3
    for (let i = 0; i < total; i += 1) {
      s.setUserScope(`u${i}`)
      s.writeJSON(KEYS.SESSIONS, { v: 1, list: [{ id: `s${i}` }] })
      s.writeJSON(KEYS.LOCATION, { v: 1, city: `市${i}` })
    }
    const buckets = Object.keys(window.localStorage).filter((k) => k.startsWith(`${KEYS.SESSIONS}@`))
    expect(buckets.length).toBe(s.MAX_ACCOUNT_BUCKETS)
    // 最先进来的三个账号已经被挤掉
    for (let i = 0; i < 3; i += 1) {
      expect(window.localStorage.getItem(`${KEYS.SESSIONS}@u${i}`)).toBeNull()
      expect(window.localStorage.getItem(`${KEYS.LOCATION}@u${i}`)).toBeNull()
    }
    // 当前账号数据完好
    expect(s.readJSON(KEYS.SESSIONS).list[0].id).toBe(`s${total - 1}`)
  })

  it('同一毫秒内连续切号不会把刚登录的账号当成最旧丢掉', async () => {
    const s = await freshStorage()
    for (let i = 0; i < s.MAX_ACCOUNT_BUCKETS + 5; i += 1) {
      s.setUserScope(`fast${i}`)
      s.writeJSON(KEYS.PREFS, { v: 1, n: i })
    }
    expect(s.readJSON(KEYS.PREFS)).toEqual({ v: 1, n: s.MAX_ACCOUNT_BUCKETS + 4 })
  })

  it('evictOldestAccountBucket：丢最旧账号，当前账号不动', async () => {
    const s = await freshStorage()
    s.setUserScope('old')
    s.writeJSON(KEYS.SESSIONS, { v: 1, list: [{ id: 'o' }] })
    s.setUserScope('fresh')
    s.writeJSON(KEYS.SESSIONS, { v: 1, list: [{ id: 'f' }] })

    expect(s.evictOldestAccountBucket('fresh')).toBe(true)
    expect(window.localStorage.getItem(`${KEYS.SESSIONS}@old`)).toBeNull()
    expect(s.readJSON(KEYS.SESSIONS).list[0].id).toBe('f')
    // 只剩当前账号时无可丢，返回 false
    expect(s.evictOldestAccountBucket('fresh')).toBe(false)
  })

  it('写入撞配额：先挤掉最旧账号再重试，避免直接降级内存模式', async () => {
    const s = await freshStorage()
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage')
    const map = new Map()
    map.set(`${KEYS.SESSIONS}@old`, JSON.stringify({ v: 1, list: [{ id: 'o' }] }))
    map.set('agri:accounts', JSON.stringify([
      { id: 'fresh', lastUsed: 2000 },
      { id: 'old', lastUsed: 1000 }
    ]))
    let attempts = 0
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (k) => (map.has(k) ? map.get(k) : null),
        // 第一次写当前账号的会话桶抛配额错，挤掉旧账号后的重试才放行
        setItem: (k, v) => {
          if (k.startsWith(KEYS.SESSIONS) && ++attempts === 1) {
            throw Object.assign(new Error('quota'), { name: 'QuotaExceededError' })
          }
          map.set(k, String(v))
        },
        removeItem: (k) => { map.delete(k) },
        clear: () => map.clear(),
        key: (i) => [...map.keys()][i] ?? null,
        get length() { return map.size }
      }
    })
    try {
      s.setUserScope('fresh')
      const ok = s.writeJSON(KEYS.SESSIONS, { v: 1, list: [{ id: 'f' }] }, { onQuotaError: () => false })
      expect(ok).toBe(true)
      expect(s.isMemoryMode()).toBe(false)
      expect(map.get(`${KEYS.SESSIONS}@fresh`)).toContain('"f"')
      expect(map.has(`${KEYS.SESSIONS}@old`)).toBe(false)
    } finally {
      if (originalDescriptor) Object.defineProperty(window, 'localStorage', originalDescriptor)
    }
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
    expect(window.localStorage.getItem(KEYS.VERSION)).toBe('{"v":2}')
  })

  it('版本一致：不迁移', async () => {
    const s = await freshStorage()
    s.migrateIfNeeded()
    expect(s.migrateIfNeeded()).toEqual({ migrated: false, fromVersion: 2 })
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
    expect(s.readJSON(KEYS.VERSION)).toEqual({ v: 2 })
  })

  it('v1 → v2：各账号分桶、账号索引、旧版裸 session id 一次性全清', async () => {
    const s = await freshStorage()
    window.localStorage.setItem(`${KEYS.SESSIONS}@u1`, '{"list":[{"id":"a"}]}')
    window.localStorage.setItem(`${KEYS.LOCATION}@u2`, '{"city":"郑州市"}')
    window.localStorage.setItem('agri:accounts', '[{"id":"u1","lastUsed":1}]')
    window.localStorage.setItem(KEYS.SESSIONS, '{"list":[{"id":"shared"}]}')
    window.localStorage.setItem('agri_session_id', 'sess_old')
    window.localStorage.setItem(KEYS.VERSION, '1')

    expect(s.migrateIfNeeded()).toEqual({ migrated: true, fromVersion: 1 })
    expect(Object.keys(window.localStorage).sort()).toEqual(['agri:version'])
    expect(s.readJSON(KEYS.SESSIONS, null)).toBeNull()
  })

  it('迁移只清 agri: 前缀与旧 session id，别源的同名 key 不误伤', async () => {
    const s = await freshStorage()
    window.localStorage.setItem('other:keep', 'v')
    window.localStorage.setItem('agriculture', 'v')
    window.localStorage.setItem(KEYS.VERSION, '1')
    s.migrateIfNeeded()
    expect(window.localStorage.getItem('other:keep')).toBe('v')
    expect(window.localStorage.getItem('agriculture')).toBe('v')
  })
})

/**
 * 魔搭 OAuth 登录入口。
 *
 * 创空间页面运行在 iframe 中：授权流程必须在新窗口里走完，
 * 否则 state cookie 会落在第三方上下文里被浏览器丢弃（表现为 mismatching_state）。
 */
export const OAUTH_WINDOW_NAME = 'agri_modelscope_login'

/** 一次性通行证：授权回调写入，路由守卫消费一次后删除 */
export const ENTRY_FLAG = 'agri:entry'

export function markEntryVerified() {
  try {
    sessionStorage.setItem(ENTRY_FLAG, '1')
  } catch (err) {
    /* 隐私模式下 sessionStorage 不可用时忽略：只影响本次免登录，不影响正确性 */
  }
}

/** @returns {boolean} 本次页面加载是否刚完成过身份核验 */
export function consumeEntryFlag() {
  try {
    if (sessionStorage.getItem(ENTRY_FLAG) !== '1') return false
    sessionStorage.removeItem(ENTRY_FLAG)
    return true
  } catch (err) {
    return false
  }
}

/** 当前页面址（登录页本身不作为落点，登录完直接进工作台） */
export function currentPath() {
  const { pathname, search } = window.location
  if (pathname === '/login') return '/dashboard'
  return `${pathname}${search}`
}

/**
 * @param {{ switchAccount?: boolean, next?: string }} [opts]
 *   switchAccount：带 prompt=login，让魔搭重新走一次登录（换账号）
 *   next：授权完成后的落点，默认当前页面
 * @returns {{ popup: boolean }} 是否成功打开了新窗口
 */
export function startModelScopeLogin({ switchAccount = false, next } = {}) {
  const params = new URLSearchParams()
  if (switchAccount) params.set('switch', '1')
  params.set('next', next || currentPath())
  const url = `/api/auth/modelscope?${params.toString()}`

  // 独立标签页访问（studio 域名直连）不需要弹窗
  if (window.self === window.top) {
    window.location.href = url
    return { popup: false }
  }

  let win = null
  try {
    win = window.open(url, OAUTH_WINDOW_NAME, 'width=520,height=680')
  } catch (err) {
    win = null
  }
  if (!win) {
    // 弹窗被拦截：退化为当前窗口跳转，回调页结束时会自行进入工作台
    window.location.href = url
    return { popup: false }
  }
  return { popup: true }
}

/** 是否运行在创空间的 iframe 里（iframe 内无法整页跳转去授权） */
export function inIframe() {
  try {
    return window.self !== window.top
  } catch (err) {
    return true
  }
}

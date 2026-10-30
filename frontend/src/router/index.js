import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { consumeEntryFlag, inIframe } from '@/utils/oauth'

/**
 * 主导航配置：顶栏、移动抽屉、底部 TabBar 共用同一份来源。
 * @type {{ path: string, name: string, title: string, icon: string }[]}
 */
export const NAV_ITEMS = [
  { path: '/dashboard', name: 'dashboard', title: '总览', icon: 'Odometer' },
  { path: '/chat', name: 'chat', title: '智能问答', icon: 'ChatDotRound' },
  { path: '/farm', name: 'farm', title: '我的农场', icon: 'Grape' },
  { path: '/warning', name: 'warning', title: '预警中心', icon: 'WarnTriangleFilled' },
  { path: '/calendar', name: 'calendar', title: '农事日历', icon: 'Calendar' }
]

const VIEW_OF = {
  dashboard: () => import('@/views/DashboardView.vue'),
  chat: () => import('@/views/ChatView.vue'),
  farm: () => import('@/views/FarmView.vue'),
  warning: () => import('@/views/WarningView.vue'),
  calendar: () => import('@/views/CalendarView.vue'),
  login: () => import('@/views/LoginView.vue')
}

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: VIEW_OF.login, meta: { title: '登录', public: true } },
  ...NAV_ITEMS.map((item) => ({
    path: item.path,
    name: item.name,
    component: VIEW_OF[item.name],
    meta: { title: item.title, icon: item.icon }
  })),
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

/** 自动整页授权的尝试时间戳：浏览器拒绝跨站 cookie 时避免 MS ↔ 应用之间来回跳 */
const SSO_ATTEMPT_KEY = 'agri:sso-at'
const SSO_ATTEMPT_COOLDOWN = 60_000

function ssoRecentlyAttempted() {
  try {
    return Date.now() - Number(sessionStorage.getItem(SSO_ATTEMPT_KEY) || 0) < SSO_ATTEMPT_COOLDOWN
  } catch (err) {
    return false
  }
}

function markSsoAttempt() {
  try {
    sessionStorage.setItem(SSO_ATTEMPT_KEY, String(Date.now()))
  } catch (err) {
    /* 隐私模式下无法记录：只影响防抖，不影响鉴权 */
  }
}

/**
 * 全局登录守卫：除 /login 外，所有页面都要求已登录（后端用 HttpOnly Cookie 识别身份）。
 *
 * 关键：Cookie 有 30 天有效期，而浏览器里可能已经换了魔搭账号（同一浏览器先退 A 再登 B），
 * 所以「本次页面加载」必须重新向魔搭核验一次身份，不能凭旧 Cookie 直接放行。
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // 授权回调留下的一次性通行证：本次加载刚核验过，直接放行
  if (consumeEntryFlag()) auth.markVerified()
  if (!auth.checked) {
    await auth.fetchMe()
  }

  if (to.meta.public) return true

  if (auth.verifyRequired && !auth.verified) {
    // 顶层窗口（直接访问 studio 域名）：整页跳去授权，魔搭侧已登录则回来即绑定本人账号
    if (!inIframe() && !ssoRecentlyAttempted()) {
      markSsoAttempt()
      window.location.replace(`/api/auth/modelscope?next=${encodeURIComponent(to.fullPath)}`)
      return false
    }
    // iframe 内不能整页跳转（魔搭登录页会白屏），退回登录页由用户点一下完成核验
    return { path: '/login', query: { verify: '1', redirect: to.fullPath } }
  }

  if (auth.user) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} · 农业气象智能体`
})

export default router

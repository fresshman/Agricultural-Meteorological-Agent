import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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

/**
 * 全局登录守卫：除 /login 外，所有页面都要求已登录（后端用 HttpOnly Cookie 识别身份）。
 * 身份是用户自己输昵称+密码换来的，Cookie 即身份，不需要每次打开再核验。
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.checked) {
    await auth.fetchMe()
  }

  if (to.meta.public) return true
  if (auth.user) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} · 农业气象智能体`
})

export default router

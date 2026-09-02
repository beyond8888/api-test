import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    name: 'Builder',
    component: () => import('@/views/WorkspaceView.vue'),
    meta: { title: 'API 测试' },
  },
  {
    path: '/calendar',
    name: 'Calendar',
    component: () => import('@/views/ScheduleView.vue'),
    meta: { title: '排班日历' },
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: { title: '项目管理' },
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/ToolsView.vue'),
    meta: { title: '工具箱' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置' },
  },
  {
    path: '/mock',
    name: 'Mock',
    component: () => import('@/views/MockView.vue'),
    meta: { title: 'Mock 服务' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Global guard: redirect to login if not authenticated
router.beforeEach((to, _from, next) => {
  const title = to.meta?.title as string | undefined
  document.title = title ? `${title} · API Test Platform` : 'API Test Platform'

  const authStore = useAuthStore()
  if (to.meta.public || authStore.isAuthenticated) {
    next()
  } else {
    next('/login')
  }
})

export default router

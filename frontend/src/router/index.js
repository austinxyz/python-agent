import { createRouter, createWebHistory } from 'vue-router'

import WikiView from '../views/WikiView.vue'
import IngestView from '../views/IngestView.vue'
import ChatView from '../views/ChatView.vue'
import PrivateView from '../views/PrivateView.vue'
import LoginView from '../views/LoginView.vue'
import AcceptInviteView from '../views/AcceptInviteView.vue'
import ChangePasswordView from '../views/ChangePasswordView.vue'
import MeView from '../views/MeView.vue'
import AdminCertView from '../views/AdminCertView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' }, // multi-user-auth-core: default landing /chat
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/accept-invite', component: AcceptInviteView, meta: { public: true } },
    { path: '/change-password', component: ChangePasswordView, meta: { requiresAuth: true } },
    { path: '/me', component: MeView, meta: { requiresAuth: true } },
    { path: '/wiki', component: WikiView, meta: { requiresAuth: true } },
    { path: '/ingest', component: IngestView, meta: { requiresAuth: true } },
    { path: '/chat', component: ChatView, meta: { requiresAuth: true } },
    { path: '/private', component: PrivateView, meta: { requiresAuth: true } },
    { path: '/admin/cert', component: AdminCertView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/users', component: AdminUsersView, meta: { requiresAuth: true, requiresAdmin: true } },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta?.public) {
    return true
  }

  // Lazy import to avoid circular imports during module load.
  const { useAuthStore } = await import('../stores/auth.js')
  const auth = useAuthStore()

  if (auth.currentUser === null) {
    await auth.fetchMe()
  }

  if (auth.currentUser === null) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // Admin-only routes (none in core; admin-ui change registers /admin/users
  // which inherits this guard).
  if (to.path.startsWith('/admin/') && auth.currentUser.role !== 'admin') {
    return { path: '/chat' }
  }

  return true
})

export default router

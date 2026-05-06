import { createRouter, createWebHistory } from 'vue-router'
import WikiView from '../views/WikiView.vue'
import IngestView from '../views/IngestView.vue'
import ChatView from '../views/ChatView.vue'
import PrivateView from '../views/PrivateView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/wiki' },
    { path: '/wiki', component: WikiView },
    { path: '/ingest', component: IngestView },
    { path: '/chat', component: ChatView },
    { path: '/private', component: PrivateView },
  ],
})

export default router

import './style.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerOnUnauthorized } from './api/index.js'
import { useAuthStore } from './stores/auth.js'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Wire axios 401 interceptor → clear auth + redirect to /login.
registerOnUnauthorized(() => {
  const auth = useAuthStore()
  auth.currentUser = null
  const current = router.currentRoute.value
  if (current.path !== '/login') {
    router.push({ path: '/login', query: { redirect: current.fullPath } })
  }
})

app.mount('#app')

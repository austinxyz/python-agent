import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'

// Task 6.3: Axios baseURL
import api from '../src/api/index.js'

// Task 6.5: AppLayout nav items
import AppLayout from '../src/components/AppLayout.vue'

// Task 6.7: View headings
import WikiView from '../src/views/WikiView.vue'
import IngestView from '../src/views/IngestView.vue'
import ChatView from '../src/views/ChatView.vue'
import PrivateView from '../src/views/PrivateView.vue'

// Task 7.1: TreeNav
import TreeNav from '../src/components/tree-nav/TreeNav.vue'

// Task 7.3: Pinia stores
import { useWikiStore } from '../src/stores/wiki.js'
import { useIngestStore } from '../src/stores/ingest.js'
import { useChatStore } from '../src/stores/chat.js'
import { usePrivateStore } from '../src/stores/private.js'


describe('api/index', () => {
  it('has baseURL /api', () => {
    expect(api.defaults.baseURL).toBe('/api')
  })
})


function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', redirect: '/wiki' },
      { path: '/wiki', component: WikiView },
      { path: '/ingest', component: IngestView },
      { path: '/chat', component: ChatView },
      { path: '/private', component: PrivateView },
    ],
  })
}


describe('AppLayout', () => {
  it('renders all four nav items', async () => {
    const router = makeRouter()
    await router.push('/wiki')
    const wrapper = mount(AppLayout, {
      global: { plugins: [router, createPinia()] },
    })
    const text = wrapper.text()
    expect(text).toContain('知识库')
    expect(text).toContain('摄入')
    expect(text).toContain('对话')
    expect(text).toContain('私有')
  })
})


describe('View skeletons', () => {
  // Provide a router for views that read route state (WikiView reads
  // ?file=<id>) or render <router-link> (ChatView source chips).
  function withRouter() {
    const router = makeRouter()
    return { global: { plugins: [router, createPinia()] } }
  }

  it('WikiView renders heading', () => {
    const wrapper = mount(WikiView, withRouter())
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('IngestView renders heading', () => {
    const wrapper = mount(IngestView)
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('ChatView renders heading', () => {
    const wrapper = mount(ChatView, withRouter())
    expect(wrapper.find('h1').exists()).toBe(true)
  })

  it('PrivateView renders heading', () => {
    const wrapper = mount(PrivateView, withRouter())
    expect(wrapper.find('h1').exists()).toBe(true)
  })
})


describe('TreeNav', () => {
  it('renders item labels', () => {
    const wrapper = mount(TreeNav, {
      props: { items: [{ label: 'Finance' }, { label: 'Health' }] },
    })
    expect(wrapper.text()).toContain('Finance')
    expect(wrapper.text()).toContain('Health')
  })

  it('emits select event when item is clicked', async () => {
    const wrapper = mount(TreeNav, {
      props: { items: [{ label: 'Finance' }] },
    })
    await wrapper.find('li').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')[0][0]).toEqual({ label: 'Finance' })
  })
})


describe('Pinia stores', () => {
  it('all stores are callable without error', () => {
    const pinia = createPinia()
    const wiki = useWikiStore(pinia)
    const ingest = useIngestStore(pinia)
    const chat = useChatStore(pinia)
    const priv = usePrivateStore(pinia)
    expect(wiki).toBeDefined()
    expect(ingest).toBeDefined()
    expect(chat).toBeDefined()
    expect(priv).toBeDefined()
  })
})

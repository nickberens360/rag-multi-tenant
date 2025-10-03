import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import KnowledgeNavigation from '@/components/knowledge/KnowledgeNavigation.vue'

// Monaco Editor Web Worker setup
import './monaco-env.js'

// Global CSS
import './styles/main.css'
import './styles/typography.css'
import './styles/design-system.css'



const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

// Globally register Knowledge navigation component to avoid resolution issues during HMR
app.component('KnowledgeNavigation', KnowledgeNavigation)

app.mount('#app')

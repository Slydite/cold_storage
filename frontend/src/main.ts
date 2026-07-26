import './assets/main.css'
import './api/client'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'

// Open-Source MIT Custom PrimeVue Preset
const ColdStoragePreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
      950: '#2e1065'
    }
  }
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(VueQueryPlugin)
app.use(PrimeVue, {
  theme: {
    preset: ColdStoragePreset,
    options: {
      darkModeSelector: '[data-theme="dark"]',
      cssLayer: false
    }
  }
})
app.use(ToastService)
app.use(ConfirmationService)

// Wait for the router's FIRST navigation to resolve before mounting.
// The global beforeEach guard awaits /api/auth/me/ to decide whether to
// redirect to /login. Mounting immediately painted App.vue while that request
// was still in flight, and since an unresolved route has no `meta.public`,
// App.vue fell through to the authenticated branch and rendered the full app
// chrome (sidebar, header) for a beat before bouncing to the login screen.
// isReady() resolves after the guard, so the first paint is already correct.
router.isReady().then(() => {
  app.mount('#app')
})

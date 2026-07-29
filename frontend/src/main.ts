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
import i18n from './i18n'
import { useLocaleStore } from './stores/locale'
import { hydrateToken } from './api/authToken'

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
app.use(i18n)

// Initialize locale store pre-mount to sync locale and document.documentElement.lang
useLocaleStore()

// Hydrate token before installing router to ensure route guards see it
await hydrateToken()

app.use(router)
// Explicit query defaults.
//
// The shop leaves this open on a counter machine all day, so nothing ever
// triggers a visibility or focus event and the screen would otherwise show
// whatever it loaded that morning. A slow poll keeps it current: at ten
// minutes that is six requests an hour per open screen, which is nothing at
// this scale, and it refreshes data in place rather than reloading the page,
// so a half-entered GRN is never lost.
//
// refetchIntervalInBackground stays off (the default) so a phone with the tab
// backgrounded stops polling instead of burning battery and mobile data.
const POLL_INTERVAL_MS = 10 * 60 * 1000

app.use(VueQueryPlugin, {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        staleTime: 2 * 60 * 1000,
        refetchInterval: POLL_INTERVAL_MS,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        retry: 1
      }
    }
  }
})
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
router.isReady().then(async () => {
  await hydrateToken()
  app.mount('#app')
})

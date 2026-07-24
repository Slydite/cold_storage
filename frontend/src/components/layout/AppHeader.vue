<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '../../stores/theme'
import { useAuthStore } from '../../stores/auth'
import { useToast } from 'primevue/usetoast'
import OverlayBadge from 'primevue/overlaybadge'
import Menu from 'primevue/menu'
import { Calendar, Bell, Sun, Moon } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const themeStore = useThemeStore()
const authStore = useAuthStore()

const pageMeta = computed(() => ({
  title: (route.meta.title as string) ?? 'Dashboard',
  subtitle: (route.meta.subtitle as string) ?? ''
}))

const dateFormatOptions: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short', year: 'numeric', weekday: 'short' }
const currentDateFormatted = ref(new Date().toLocaleDateString('en-GB', dateFormatOptions))
let dateRefreshInterval: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  dateRefreshInterval = setInterval(() => {
    currentDateFormatted.value = new Date().toLocaleDateString('en-GB', dateFormatOptions)
  }, 60_000)
})

onUnmounted(() => {
  clearInterval(dateRefreshInterval)
})

const menu = ref()

const toggleMenu = (event: Event) => {
  menu.value?.toggle(event)
}

const userInitials = computed(() => {
  const user = authStore.user
  if (!user) return 'AU'
  const firstInitial = user.first_name?.[0]
  const lastInitial = user.last_name?.[0]
  if (firstInitial && lastInitial) {
    return (firstInitial + lastInitial).toUpperCase()
  }
  const username = user.username
  const parts = username.split(/[\s._-]+/).filter(Boolean)
  const [firstPart, secondPart] = parts
  if (firstPart && secondPart) {
    return (firstPart.charAt(0) + secondPart.charAt(0)).toUpperCase()
  }
  return username.slice(0, 2).toUpperCase()
})

const usernameDisplay = computed(() => authStore.user?.username ?? 'Admin User')

const menuItems = computed(() => [
  {
    label: authStore.user?.username ? `@${authStore.user.username}` : 'Account',
    items: [
      {
        label: 'Sign out',
        icon: 'pi pi-sign-out',
        command: async () => {
          await authStore.logout()
          toast.add({
            severity: 'info',
            summary: 'Signed out',
            detail: 'You have been logged out successfully.',
            life: 3000
          })
          router.push({ name: 'login' })
        }
      }
    ]
  }
])
</script>

<template>
  <header class="app-header">
    <!-- Header Left Title & Contextual Greeting -->
    <div class="header-titles">
      <h2 class="page-title">{{ pageMeta.title }}</h2>
      <p class="page-subtitle">{{ pageMeta.subtitle }}</p>
    </div>

    <!-- Header Right Controls -->
    <div class="header-actions">
      <!-- Date Display Button -->
      <div class="date-badge">
        <Calendar :size="15" class="icon-muted" />
        <span>{{ currentDateFormatted }}</span>
      </div>

      <!-- Theme Switcher Toggle -->
      <button
        class="icon-action-btn"
        :title="themeStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        @click="themeStore.toggleTheme"
      >
        <Sun v-if="themeStore.theme === 'dark'" :size="18" />
        <Moon v-else :size="18" />
      </button>

      <!-- Notification Bell -->
      <div class="notification-wrapper">
        <OverlayBadge value="3" severity="danger">
          <button class="icon-action-btn" title="Notifications">
            <Bell :size="18" />
          </button>
        </OverlayBadge>
      </div>

      <!-- Avatar Pill & Menu -->
      <Menu ref="menu" :model="menuItems" popup />
      <button
        class="header-avatar"
        :title="usernameDisplay"
        @click="toggleMenu"
        type="button"
        aria-haspopup="true"
        aria-controls="overlay_menu"
      >
        <span>{{ userInitials }}</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 72px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-page);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 90;
  transition: background-color 0.25s ease, border-color 0.25s ease;
}

.header-titles {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.page-subtitle {
  font-size: 12.5px;
  color: var(--text-secondary);
  font-weight: 400;
  margin-top: 2px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.date-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
  box-shadow: var(--shadow-card);
}

.icon-muted {
  color: var(--text-secondary);
}

.icon-action-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: var(--shadow-card);
}

.icon-action-btn:hover {
  background-color: var(--bg-surface-hover);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.notification-wrapper {
  display: flex;
  align-items: center;
}

.header-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--accent-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
  cursor: pointer;
  border: none;
}
</style>

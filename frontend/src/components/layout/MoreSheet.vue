<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import { useFacility } from '../../composables/useFacility'
import { useAuthStore } from '../../stores/auth'
import { useToast } from 'primevue/usetoast'
import {
  Receipt,
  FileText,
  Users,
  BarChart3,
  Settings as SettingsIcon,
  ChevronDown,
  LogOut
} from 'lucide-vue-next'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const toast = useToast()

const { facilities, selectedFacilityId, setSelectedFacilityId } = useFacility()
const authStore = useAuthStore()

const overflowItems = computed(() => [
  { label: t('nav.billing'), icon: Receipt, path: '/billing' },
  { label: t('nav.invoicing'), icon: FileText, path: '/invoicing' },
  { label: t('nav.parties'), icon: Users, path: '/parties' },
  { label: t('nav.reports'), icon: BarChart3, path: '/reports' },
  { label: t('nav.settings'), icon: SettingsIcon, path: '/settings' }
])

const facilityOptions = computed(() =>
  facilities.value.map((f) => ({ label: f.name, value: f.id }))
)

const activeFacilityId = computed({
  get: () => selectedFacilityId.value,
  set: (val: number | undefined) => {
    setSelectedFacilityId(val)
  }
})

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

const userNameDisplay = computed(() => {
  const user = authStore.user
  if (!user) return 'Admin User'
  if (user.first_name || user.last_name) {
    return [user.first_name, user.last_name].filter(Boolean).join(' ')
  }
  return user.username
})

const userEmailDisplay = computed(() => authStore.user?.email || 'admin@coldstore.in')

const isActive = (path: string) => {
  return route.path.startsWith(path)
}

const navigate = (path: string) => {
  emit('close')
  router.push(path)
}

const handleSignOut = async () => {
  emit('close')
  await authStore.logout()
  toast.add({
    severity: 'info',
    summary: t('auth.signedOut'),
    detail: t('auth.loggedOutSuccess'),
    life: 3000
  })
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="more-sheet-wrapper">
    <!-- Backdrop -->
    <Transition name="fade">
      <div v-if="isOpen" class="more-sheet-backdrop" @click="emit('close')" />
    </Transition>

    <!-- Bottom Sheet Content -->
    <Transition name="slide-up">
      <div v-if="isOpen" class="more-sheet" role="dialog" aria-modal="true">
        <!-- Drag Handle / Visual cue -->
        <div class="sheet-drag-handle" @click="emit('close')" />

        <div class="sheet-content">
          <!-- Overflow Nav Destinations -->
          <nav class="overflow-nav">
            <button
              v-for="item in overflowItems"
              :key="item.path"
              class="overflow-nav-item"
              :class="{ active: isActive(item.path) }"
              @click="navigate(item.path)"
              type="button"
            >
              <component :is="item.icon" class="overflow-icon" :size="18" />
              <span class="overflow-label">{{ item.label }}</span>
            </button>
          </nav>

          <!-- Facility Switcher -->
          <div class="facility-switcher">
            <label class="facility-label">{{ t('nav.workingFacility') }}</label>
            <Select
              v-model="activeFacilityId"
              :options="facilityOptions"
              optionLabel="label"
              optionValue="value"
              class="facility-select"
            >
              <template #dropdownicon>
                <ChevronDown :size="14" />
              </template>
            </Select>
          </div>

          <!-- User Card and Sign Out -->
          <div class="user-card">
            <div class="user-avatar">{{ userInitials }}</div>
            <div class="user-info">
              <div class="user-name">{{ userNameDisplay }}</div>
              <div class="user-email">{{ userEmailDisplay }}</div>
            </div>
            <button class="sign-out-btn" :title="t('nav.signOut')" @click="handleSignOut" type="button">
              <LogOut :size="16" />
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.more-sheet-wrapper {
  position: relative;
  z-index: 1000;
}

.more-sheet-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  z-index: 1001;
}

.more-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.15);
  z-index: 1002;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  padding-bottom: calc(16px + env(safe-area-inset-bottom));
}

.sheet-drag-handle {
  width: 40px;
  height: 4px;
  background-color: var(--border-subtle);
  border-radius: 2px;
  margin: 12px auto 8px auto;
  cursor: pointer;
  flex-shrink: 0;
}

.sheet-content {
  overflow-y: auto;
  padding: 0 20px 8px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overflow-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.overflow-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: all 0.15s ease;
}

.overflow-nav-item:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
}

.overflow-nav-item.active {
  background-color: var(--accent-primary);
  color: #ffffff;
  font-weight: 600;
}

.overflow-icon {
  flex-shrink: 0;
}

.facility-switcher {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
}

.facility-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.facility-select {
  width: 100%;
  font-size: 13.5px !important;
  border-radius: 8px !important;
  background-color: var(--bg-surface-hover) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 10px;
  background-color: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  margin-top: 4px;
}

.user-avatar {
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
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sign-out-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.sign-out-btn:hover {
  color: var(--status-danger-color);
  background-color: rgba(244, 63, 94, 0.1);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}

@media (min-width: 769px) {
  .more-sheet-wrapper {
    display: none !important;
  }
}
</style>

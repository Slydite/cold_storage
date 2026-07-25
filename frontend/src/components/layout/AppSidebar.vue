<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Select from 'primevue/select'
import { useSidebar } from '../../composables/useSidebar'
import { useFacility } from '../../composables/useFacility'
import { useAuthStore } from '../../stores/auth'
import {
  LayoutDashboard,
  PackagePlus,
  Truck,
  Boxes,
  Receipt,
  FileText,
  Users,
  BarChart3,
  Settings,
  Snowflake,
  MoreVertical,
  ChevronDown
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { isOpen, close } = useSidebar()
const { facilities, selectedFacilityId, setSelectedFacilityId } = useFacility()
const authStore = useAuthStore()

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { label: 'GRN / Inward', icon: PackagePlus, path: '/grn' },
  { label: 'Delivery / Outward', icon: Truck, path: '/delivery' },
  { label: 'Inventory', icon: Boxes, path: '/inventory' },
  { label: 'Billing', icon: Receipt, path: '/billing' },
  { label: 'Invoicing', icon: FileText, path: '/invoicing' },
  { label: 'Parties', icon: Users, path: '/parties' },
  { label: 'Reports', icon: BarChart3, path: '/reports' },
  { label: 'Settings', icon: Settings, path: '/settings' }
]

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
  if (path === '/' && route.path === '/') return true
  if (path !== '/' && route.path.startsWith(path)) return true
  return false
}

const navigate = (path: string) => {
  close()
  router.push(path)
}
</script>

<template>
  <aside class="app-sidebar" :class="{ open: isOpen }">
    <!-- Brand Logo Header -->
    <div class="sidebar-header">
      <div class="logo-icon-wrapper">
        <Snowflake class="logo-icon" :size="24" />
      </div>
      <div class="brand-details">
        <h1 class="brand-name">Cold Storage</h1>
        <span class="brand-subtitle">Management System</span>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        @click="navigate(item.path)"
      >
        <component :is="item.icon" class="nav-icon" :size="18" />
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <!-- Pinned Bottom Footer Section -->
    <div class="sidebar-footer">
      <div class="facility-switcher">
        <label class="facility-label">Working Facility</label>
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

      <div class="user-card">
        <div class="user-avatar">{{ userInitials }}</div>
        <div class="user-info">
          <div class="user-name">{{ userNameDisplay }}</div>
          <div class="user-email">{{ userEmailDisplay }}</div>
        </div>
        <button class="user-menu-btn" title="User Settings">
          <MoreVertical :size="16" />
        </button>
      </div>

      <!-- Mountain/Landscape Artwork SVG -->
      <div class="sidebar-bottom-art">
        <svg viewBox="0 0 240 60" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M0 35L35 15L80 40L130 10L185 45L240 20V60H0V35Z" fill="url(#artGrad)" opacity="0.2" />
          <path d="M0 45L50 25L100 50L160 20L210 50L240 35V60H0V45Z" fill="url(#artGrad2)" opacity="0.3" />
          <defs>
            <linearGradient id="artGrad" x1="120" y1="10" x2="120" y2="60" gradientUnits="userSpaceOnUse">
              <stop stop-color="#8B5CF6"/>
              <stop offset="1" stop-color="#8B5CF6" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="artGrad2" x1="120" y1="20" x2="120" y2="60" gradientUnits="userSpaceOnUse">
              <stop stop-color="#A855F7"/>
              <stop offset="1" stop-color="#4C1D95" stop-opacity="0"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 100;
  transition: transform 0.25s ease, background-color 0.25s ease, border-color 0.25s ease;
}

.sidebar-header {
  padding: 20px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon-wrapper {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-details {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background-color: var(--accent-primary);
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}

.nav-icon {
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--bg-sidebar);
  position: relative;
  overflow: hidden;
}

.facility-switcher {
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 2;
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
  font-size: 12.5px !important;
  border-radius: 8px !important;
  background-color: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  z-index: 2;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email {
  font-size: 10.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-menu-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
}

.user-menu-btn:hover {
  color: var(--text-primary);
  background-color: var(--bg-surface-hover);
}

.sidebar-bottom-art {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  pointer-events: none;
  z-index: 1;
}

.sidebar-bottom-art svg {
  width: 100%;
  height: 100%;
}

@media (max-width: 768px) {
  .app-sidebar {
    transform: translateX(-100%);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
  }

  .app-sidebar.open {
    transform: translateX(0);
  }
}
</style>

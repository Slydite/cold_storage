<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Building, Layers, Package, Users, ChevronRight, ChevronLeft } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const sections = computed(() => [
  {
    path: '/settings/facility',
    label: t('settings.facilityManagement'),
    icon: Building
  },
  {
    path: '/settings/locations',
    label: t('settings.locationsTab'),
    icon: Layers
  },
  {
    path: '/settings/commodities',
    label: t('settings.commoditiesTab'),
    icon: Package
  },
  {
    path: '/settings/parties',
    label: t('nav.parties'),
    icon: Users
  },
  {
    path: '/settings/users',
    label: t('settings.userAccountsTab'),
    icon: Users
  }
])

const currentSectionTitle = computed(() => {
  const activeSection = sections.value.find(sec => route.path.startsWith(sec.path))
  return activeSection ? activeSection.label : ''
})

const handleDesktopRedirect = () => {
  if (window.innerWidth > 768 && route.path === '/settings') {
    router.replace('/settings/facility')
  }
}

onMounted(() => {
  handleDesktopRedirect()
})

watch(
  () => route.path,
  () => {
    handleDesktopRedirect()
  }
)
</script>

<template>
  <div class="page-container settings-page">
    
    <!-- DESKTOP VIEW (> 768px) -->
    <div class="desktop-settings">
      <header class="settings-header">
        <h2 class="page-title">{{ t('settings.settingsTitle') }}</h2>
        <p class="page-subtitle">{{ t('settings.settingsSubtitle') }}</p>
      </header>

      <div class="custom-tab-list">
        <RouterLink
          v-for="sec in sections"
          :key="sec.path"
          :to="sec.path"
          class="tab-item"
        >
          <component :is="sec.icon" :size="16" />
          <span>{{ sec.label }}</span>
        </RouterLink>
      </div>

      <div class="settings-content-pane">
        <RouterView />
      </div>
    </div>

    <!-- MOBILE VIEW (<= 768px) -->
    <div class="mobile-settings">
      <!-- Menu List (rendered when path is exactly /settings) -->
      <div v-if="route.path === '/settings'" class="mobile-menu-list">
        <header class="settings-header">
          <h2 class="page-title">{{ t('settings.settingsTitle') }}</h2>
          <p class="page-subtitle">{{ t('settings.settingsSubtitle') }}</p>
        </header>

        <div class="menu-items-group">
          <RouterLink
            v-for="sec in sections"
            :key="sec.path"
            :to="sec.path"
            class="menu-item-link"
          >
            <div class="menu-item-left">
              <component :is="sec.icon" :size="20" class="menu-icon" />
              <span>{{ sec.label }}</span>
            </div>
            <ChevronRight :size="18" class="chevron-icon" />
          </RouterLink>
        </div>
      </div>

      <!-- Child View Content (rendered when path is a sub-route, e.g., /settings/facility) -->
      <div v-else class="mobile-child-view">
        <div class="back-nav">
          <RouterLink to="/settings" class="back-link">
            <ChevronLeft :size="18" />
            <span>{{ t('common.back') }}</span>
          </RouterLink>
          <h3 class="current-section-title">{{ currentSectionTitle }}</h3>
        </div>
        
        <div class="mobile-content-pane">
          <RouterView />
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.settings-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Desktop Styles */
.desktop-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.custom-tab-list {
  display: flex;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 6px;
  box-shadow: var(--shadow-card);
  overflow-x: auto;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border: none;
  background: transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
  text-decoration: none;
}

.tab-item:hover {
  color: var(--text-primary);
  background: var(--bg-surface-hover);
}

.tab-item.router-link-active,
.tab-item.router-link-exact-active {
  color: #ffffff;
  background: var(--accent-primary);
}

.settings-content-pane {
  padding-top: 10px;
}

/* Mobile Styles */
.mobile-settings {
  display: none;
}

@media (max-width: 768px) {
  .desktop-settings {
    display: none;
  }
  
  .mobile-settings {
    display: flex;
    flex-direction: column;
    width: 100%;
  }

  .mobile-menu-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .menu-items-group {
    display: flex;
    flex-direction: column;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--shadow-card);
  }

  .menu-item-link {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    color: var(--text-primary);
    text-decoration: none;
    border-bottom: 1px solid var(--border-subtle);
    transition: background-color 0.15s ease;
    font-weight: 500;
    font-size: 14.5px;
  }

  .menu-item-link:last-child {
    border-bottom: none;
  }

  .menu-item-link:hover,
  .menu-item-link:active {
    background-color: var(--bg-surface-hover);
  }

  .menu-item-left {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .menu-icon {
    color: var(--accent-primary);
    flex-shrink: 0;
  }

  .chevron-icon {
    color: var(--text-secondary);
    opacity: 0.7;
  }

  .mobile-child-view {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .back-nav {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--accent-primary);
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    padding: 6px 12px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    box-shadow: var(--shadow-card);
    transition: all 0.15s ease;
  }

  .back-link:hover,
  .back-link:active {
    background: var(--bg-surface-hover);
    color: var(--accent-primary-hover);
  }

  .current-section-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .mobile-content-pane {
    width: 100%;
  }
}
</style>

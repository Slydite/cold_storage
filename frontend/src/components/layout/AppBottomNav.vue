<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  LayoutDashboard,
  PackagePlus,
  Truck,
  Boxes,
  MoreHorizontal
} from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'toggle-more'): void
}>()

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

// Short labels: a bottom-bar slot is ~64px wide at 360px, so the full sidebar
// labels ("Delivery / Outward", "निकासी पर्ची (DN)") would ellipsis away.
const primaryItems = computed(() => [
  { label: t('nav.dashboardShort'), icon: LayoutDashboard, path: '/' },
  { label: t('nav.grnShort'), icon: PackagePlus, path: '/grn' },
  { label: t('nav.deliveryShort'), icon: Truck, path: '/delivery' },
  { label: t('nav.inventoryShort'), icon: Boxes, path: '/inventory' }
])

const isActive = (path: string) => {
  if (path === '/' && route.path === '/') return true
  if (path !== '/' && route.path.startsWith(path)) return true
  return false
}

const isMoreActive = computed(() => {
  const overflowPaths = ['/billing', '/invoicing', '/reports', '/settings']
  return overflowPaths.some((path) => route.path.startsWith(path))
})

const navigate = (path: string) => {
  router.push(path)
}
</script>

<template>
  <nav class="bottom-nav">
    <button
      v-for="item in primaryItems"
      :key="item.path"
      class="bottom-nav-item"
      :class="{ active: isActive(item.path) }"
      @click="navigate(item.path)"
      type="button"
    >
      <component :is="item.icon" class="bottom-nav-icon" :size="20" />
      <span class="bottom-nav-label">{{ item.label }}</span>
    </button>
    <button
      class="bottom-nav-item"
      :class="{ active: isMoreActive }"
      @click="emit('toggle-more')"
      type="button"
    >
      <MoreHorizontal class="bottom-nav-icon" :size="20" />
      <span class="bottom-nav-label">{{ t('nav.more') }}</span>
    </button>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: none;
}

@media (max-width: 768px) {
  .bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: var(--bg-surface);
    border-top: 1px solid var(--border-subtle);
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom);
    height: calc(60px + env(safe-area-inset-bottom));
  }
}

.bottom-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 2px;
  min-width: 0;
  transition: color 0.15s ease;
}

.bottom-nav-item:hover {
  color: var(--text-primary);
}

.bottom-nav-item.active {
  color: var(--accent-primary);
}

.bottom-nav-icon {
  margin-bottom: 3px;
  flex-shrink: 0;
}

.bottom-nav-label {
  font-size: 10px;
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  padding: 0 4px;
}

.bottom-nav-item.active .bottom-nav-label {
  font-weight: 600;
}
</style>

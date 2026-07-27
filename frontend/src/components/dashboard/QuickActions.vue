<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Plus, Truck, FileCheck2, Calculator } from 'lucide-vue-next'

const router = useRouter()
const { t } = useI18n()

const quickActions = computed(() => [
  {
    id: 'newGrn',
    title: t('dashboard.newGrn'),
    subtitle: t('dashboard.recordInward'),
    icon: Plus,
    path: '/grn?action=create',
    badgeClass: 'badge-purple'
  },
  {
    id: 'newDelivery',
    title: t('dashboard.newDelivery'),
    subtitle: t('dashboard.recordOutward'),
    icon: Truck,
    path: '/delivery?action=create',
    badgeClass: 'badge-green'
  },
  {
    id: 'generateInvoice',
    title: t('dashboard.generateInvoice'),
    subtitle: t('dashboard.createGstInvoice'),
    icon: FileCheck2,
    path: '/invoicing?action=create',
    badgeClass: 'badge-blue'
  },
  {
    id: 'billingOverview',
    title: t('dashboard.billingOverview'),
    subtitle: t('dashboard.rentAccrualAndDue'),
    icon: Calculator,
    path: '/billing',
    badgeClass: 'badge-gold',
    hasArtwork: true
  }
])

const triggerQuickAction = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="quick-actions-section">
    <h3 class="section-title">{{ t('dashboard.quickActions') }}</h3>
    <div class="actions-grid">
      <button
        v-for="action in quickActions"
        :key="action.id"
        class="action-card-btn"
        :class="{ 'has-art-bg': action.hasArtwork }"
        @click="triggerQuickAction(action.path)"
        type="button"
      >
        <div class="action-icon-box" :class="action.badgeClass">
          <component :is="action.icon" :size="20" />
        </div>
        <div class="action-text">
          <span class="action-title">{{ action.title }}</span>
          <span class="action-subtitle">{{ action.subtitle }}</span>
        </div>

        <div v-if="action.hasArtwork" class="art-overlay-image">
          <img src="/warehouse_art.png" :alt="t('dashboard.warehouseArtwork')" class="art-img" />
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.quick-actions-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.action-card-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 22px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: all 0.15s ease;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.action-card-btn:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
  background-color: var(--bg-surface-hover);
}

.action-icon-box {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 2;
}

.badge-purple {
  background: var(--badge-violet-bg);
  color: var(--badge-violet-color);
}

.badge-green {
  background: var(--badge-green-bg);
  color: var(--badge-green-color);
}

.badge-blue {
  background: var(--badge-blue-bg);
  color: var(--badge-blue-color);
}

.badge-gold {
  background: rgba(245, 158, 11, 0.25);
  color: #F59E0B;
}

.action-text {
  display: flex;
  flex-direction: column;
  z-index: 2;
}

.action-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.action-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

.action-card-btn.has-art-bg {
  background: linear-gradient(135deg, var(--bg-surface) 30%, rgba(245, 158, 11, 0.15) 100%);
}

.art-overlay-image {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 140px;
  pointer-events: none;
  opacity: 0.35;
  mix-blend-mode: luminosity;
  overflow: hidden;
}

.art-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

@media (max-width: 1200px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>

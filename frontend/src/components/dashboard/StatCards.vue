<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from 'primevue/skeleton'
import { Package, Boxes, FileCheck2, Truck } from 'lucide-vue-next'
import { formatQty } from '../../utils/format'

const props = defineProps<{
  totalStock: number
  activeLots: number
  totalGrns: number
  totalDeliveryNotes: number
  loading: boolean
}>()

const stats = computed(() => [
  {
    title: 'Total Stock (MT)',
    value: formatQty(props.totalStock, 2),
    caption: 'Active inventory weight',
    badgeClass: 'badge-purple',
    icon: Package
  },
  {
    title: 'Active Lots',
    value: props.activeLots.toString(),
    caption: 'Lots in storage',
    badgeClass: 'badge-green',
    icon: Boxes
  },
  {
    title: 'Total GRNs',
    value: props.totalGrns.toString(),
    caption: 'Goods Receipt Notes',
    badgeClass: 'badge-blue',
    icon: FileCheck2
  },
  {
    title: 'Total Delivery Notes',
    value: props.totalDeliveryNotes.toString(),
    caption: 'Dispatched & Draft DNs',
    badgeClass: 'badge-red',
    icon: Truck
  }
])
</script>

<template>
  <div class="stats-grid">
    <div v-for="stat in stats" :key="stat.title" class="stat-card">
      <div class="stat-header">
        <span class="stat-title">{{ stat.title }}</span>
        <div class="stat-icon-circle" :class="stat.badgeClass">
          <component :is="stat.icon" :size="20" />
        </div>
      </div>
      <div class="stat-value">
        <Skeleton v-if="loading" width="60%" height="2rem" />
        <span v-else>{{ stat.value }}</span>
      </div>
      <div class="stat-trend-line">
        <span class="trend-context">{{ stat.caption }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-title {
  font-size: 13.5px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
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

.badge-red {
  background: var(--badge-red-bg);
  color: var(--badge-red-color);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 14px;
  letter-spacing: -0.5px;
  font-feature-settings: 'tnum';
  min-height: 42px;
  display: flex;
  align-items: center;
}

.stat-trend-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 12.5px;
}

.trend-context {
  color: var(--text-secondary);
  font-size: 12px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>

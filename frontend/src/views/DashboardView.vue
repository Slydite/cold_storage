<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDashboardStats } from '../composables/useDashboardStats'
import StatCards from '../components/dashboard/StatCards.vue'
import StockChartPanel from '../components/dashboard/StockChartPanel.vue'
import RecentActivitiesPanel from '../components/dashboard/RecentActivitiesPanel.vue'
import QuickActions from '../components/dashboard/QuickActions.vue'
import DashboardErrorBanner from '../components/dashboard/DashboardErrorBanner.vue'

const { t, te } = useI18n()

const {
  totalStock,
  activeLots,
  totalGrns,
  totalDeliveryNotes,
  recentActivities,
  stockByCommodity,
  stockByChamber,
  isLoading,
  isError,
  errorMessage,
  refetch
} = useDashboardStats()

const localizedErrorMessage = computed(() => {
  if (errorMessage.value && te(errorMessage.value)) {
    return t(errorMessage.value)
  }
  return errorMessage.value
})
</script>

<template>
  <div class="dashboard-page">
    <DashboardErrorBanner
      v-if="isError"
      :message="localizedErrorMessage"
      @retry="refetch"
    />

    <!-- Stat Cards Grid -->
    <StatCards
      :totalStock="totalStock"
      :activeLots="activeLots"
      :totalGrns="totalGrns"
      :totalDeliveryNotes="totalDeliveryNotes"
      :loading="isLoading"
    />

    <!-- Main Content Two-Column Grid -->
    <div class="dashboard-content-grid">
      <!-- Stock Breakdown Chart Card -->
      <StockChartPanel
        :stockByCommodity="stockByCommodity"
        :stockByChamber="stockByChamber"
        :loading="isLoading"
      />

      <!-- Recent Activities Card -->
      <RecentActivitiesPanel
        :activities="recentActivities"
        :loading="isLoading"
      />
    </div>

    <!-- Quick Actions Section -->
    <QuickActions />
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-content-grid {
  display: grid;
  grid-template-columns: 1.8fr 1fr;
  gap: 20px;
}

@media (max-width: 1200px) {
  .dashboard-content-grid {
    grid-template-columns: 1fr;
  }
}
</style>

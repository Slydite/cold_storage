<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from 'primevue/skeleton'
import { AlertCircle, RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useFacility } from '../composables/useFacility'
import { useInvoiceList } from '../composables/useInvoices'
import { useLotList } from '../composables/useLots'
import BillingMetrics from '../components/billing/BillingMetrics.vue'
import OutstandingInvoicesTable from '../components/billing/OutstandingInvoicesTable.vue'
import ActiveStockTable from '../components/billing/ActiveStockTable.vue'

const { t } = useI18n()
const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const invoicesQuery = useInvoiceList(facilityId)
const lotsQuery = useLotList(facilityId, computed(() => ({ inStockOnly: true })))

const invoices = computed(() => invoicesQuery.data.value || [])
const activeLots = computed(() => lotsQuery.data.value || [])

const outstandingInvoices = computed(() => {
  return invoices.value.filter((inv) => {
    const due = Number(inv.amount_due || 0)
    return due > 0 || inv.payment_status === 'UNPAID' || inv.payment_status === 'PARTIAL'
  })
})

const totalOutstandingAmount = computed(() => {
  return outstandingInvoices.value.reduce((sum, inv) => sum + Number(inv.amount_due || 0), 0)
})

const totalAccruingBags = computed(() => {
  return activeLots.value.reduce((sum, lot) => sum + (lot.remaining_qty || 0), 0)
})

const isLoading = computed(() => loadingFacility.value || invoicesQuery.isLoading.value || lotsQuery.isLoading.value)
const isError = computed(() => facilityError.value || invoicesQuery.isError.value || lotsQuery.isError.value)

const handleRetry = () => {
  refetchFacility()
  invoicesQuery.refetch()
  lotsQuery.refetch()
}
</script>

<template>
  <div class="billing-page page-container">
    <header class="page-header">
      <div>
        <h2 class="page-title">{{ t('billing.overviewTitle') }}</h2>
        <p class="page-subtitle">{{ t('billing.overviewSubtitle') }}</p>
      </div>
    </header>

    <!-- Metrics Bar -->
    <BillingMetrics
      :totalOutstandingAmount="totalOutstandingAmount"
      :outstandingCount="outstandingInvoices.length"
      :totalAccruingBags="totalAccruingBags"
      :activeLotsCount="activeLots.length"
    />

    <!-- Error State -->
    <div v-if="isError" class="state-card error-state">
      <AlertCircle :size="36" class="text-danger" />
      <h3>{{ t('billing.failedToLoadOverview') }}</h3>
      <p>{{ t('billing.failedToLoadSub') }}</p>
      <button type="button" class="btn-primary" @click="handleRetry">
        <RefreshCw :size="15" />
        <span>{{ t('common.retry') }}</span>
      </button>
    </div>

    <!-- Loading Skeleton -->
    <div v-else-if="isLoading" class="skeleton-container">
      <Skeleton height="200px" class="mb-4" />
      <Skeleton height="200px" />
    </div>

    <template v-else>
      <!-- Outstanding Invoices Section -->
      <OutstandingInvoicesTable :invoices="outstandingInvoices" />

      <!-- Active Stock Accruing Rent Section -->
      <ActiveStockTable :lots="activeLots" />
    </template>
  </div>
</template>

<style scoped>
.billing-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.text-danger {
  color: var(--status-danger-color);
}

.error-state {
  padding: 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
</style>

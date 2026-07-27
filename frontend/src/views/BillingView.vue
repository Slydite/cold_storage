<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'
import { Receipt, Warehouse, AlertCircle, RefreshCw } from 'lucide-vue-next'
import { useFacility } from '../composables/useFacility'
import { useInvoiceList } from '../composables/useInvoices'
import { useLotList } from '../composables/useLots'
import { formatCurrency, formatQty } from '../utils/format'

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

const getPaymentSeverity = (status?: string) => {
  switch (status) {
    case 'PAID':
      return 'success'
    case 'PARTIAL':
      return 'warn'
    case 'UNPAID':
    default:
      return 'danger'
  }
}
</script>

<template>
  <div class="billing-page page-container">
    <header class="page-header">
      <div>
        <h2 class="page-title">Billing & Rent Accrual Overview</h2>
        <p class="page-subtitle">Read-only overview of outstanding invoices and active stock currently accruing rent.</p>
      </div>
    </header>

    <!-- Metrics Bar -->
    <div class="metrics-grid">
      <div class="metric-card highlight-card">
        <div class="metric-icon-wrap">
          <Receipt :size="22" class="icon-accent" />
        </div>
        <div class="metric-content">
          <span class="metric-label">Total Outstanding Due</span>
          <strong class="metric-val text-danger">{{ formatCurrency(totalOutstandingAmount) }}</strong>
          <span class="metric-sub">{{ outstandingInvoices.length }} pending invoice(s)</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-wrap">
          <Warehouse :size="22" class="icon-secondary" />
        </div>
        <div class="metric-content">
          <span class="metric-label">Stock Accruing Rent</span>
          <strong class="metric-val">{{ formatQty(totalAccruingBags, 0) }} Units</strong>
          <span class="metric-sub">Across {{ activeLots.length }} active lot(s) in facility</span>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="isError" class="state-card error-state">
      <AlertCircle :size="36" class="text-danger" />
      <h3>Failed to load billing overview data</h3>
      <p>Could not load outstanding invoices or active stock.</p>
      <button type="button" class="btn-primary" @click="handleRetry">
        <RefreshCw :size="15" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Loading Skeleton -->
    <div v-else-if="isLoading" class="skeleton-container">
      <Skeleton height="200px" class="mb-4" />
      <Skeleton height="200px" />
    </div>

    <template v-else>
      <!-- Outstanding Invoices Section -->
      <div class="billing-section">
        <div class="section-header">
          <h3 class="section-title">Outstanding Unpaid Invoices</h3>
          <p class="section-desc">Tax invoices issued to clients with pending balance due.</p>
        </div>

        <div class="table-card">
          <div v-if="outstandingInvoices.length === 0" class="empty-section">
            <p>No outstanding invoices. All issued invoices have been settled.</p>
          </div>

          <DataTable
            v-else
            :value="outstandingInvoices"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="invoice_number" header="Invoice No.">
              <template #body="{ data }">
                <span class="code-link">{{ data.invoice_number }}</span>
              </template>
            </Column>

            <Column field="party_name" header="Party / Client">
              <template #body="{ data }">
                <strong>{{ data.party_name }}</strong>
              </template>
            </Column>

            <Column field="invoice_date" header="Invoice Date" />

            <Column field="total_amount" header="Total (₹)">
              <template #body="{ data }">
                <span class="num-val">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
              </template>
            </Column>

            <Column field="amount_paid" header="Paid (₹)">
              <template #body="{ data }">
                <span class="num-val text-success">{{ formatCurrency(Number(data.amount_paid || 0)) }}</span>
              </template>
            </Column>

            <Column field="amount_due" header="Amount Due (₹)">
              <template #body="{ data }">
                <strong class="num-val text-danger">{{ formatCurrency(Number(data.amount_due || 0)) }}</strong>
              </template>
            </Column>

            <Column field="payment_status" header="Payment Status">
              <template #body="{ data }">
                <Tag
                  :value="data.payment_status || 'UNPAID'"
                  :severity="getPaymentSeverity(data.payment_status)"
                />
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <!-- Active Stock Accruing Rent Section -->
      <div class="billing-section">
        <div class="section-header">
          <h3 class="section-title">Stock Currently Accruing Storage Rent</h3>
          <p class="section-desc">Goods currently stored in chambers accruing monthly rent until withdrawn on a Delivery Note.</p>
        </div>

        <div class="table-card">
          <div v-if="activeLots.length === 0" class="empty-section">
            <p>No active stock currently in storage.</p>
          </div>

          <DataTable
            v-else
            :value="activeLots"
            size="small"
            stripedRows
            paginator
            :rows="8"
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="lot_number" header="Lot No.">
              <template #body="{ data }">
                <span class="code-link">{{ data.lot_number }}</span>
              </template>
            </Column>

            <Column field="party_name" header="Party / Customer">
              <template #body="{ data }">
                <strong>{{ data.party_name || '—' }}</strong>
              </template>
            </Column>

            <Column field="commodity_name" header="Commodity" />

            <Column header="Location">
              <template #body="{ data }">
                <span>{{ data.location_display || [data.chamber_name || data.chamber, data.floor_name || data.floor].filter(Boolean).join(' / ') || '—' }}</span>
              </template>
            </Column>

            <Column field="inward_date" header="Inward Date" />

            <Column field="remaining_qty" header="Remaining Qty">
              <template #body="{ data }">
                <strong class="num-val">{{ formatQty(data.remaining_qty, 0) }} {{ data.commodity_unit || '' }}</strong>
              </template>
            </Column>

            <Column field="rent_rate_per_unit" header="Agreed Rent Rate">
              <template #body="{ data }">
                <span class="num-val">
                  {{ data.rent_rate_per_unit ? formatCurrency(Number(data.rent_rate_per_unit)) + ' / unit / mo' : '—' }}
                </span>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.metric-icon-wrap {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: var(--bg-surface-hover);
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-accent {
  color: var(--accent-primary);
}

.icon-secondary {
  color: var(--text-secondary);
}

.metric-content {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.metric-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 2px 0;
}

.metric-sub {
  font-size: 12px;
  color: var(--text-secondary);
}

.billing-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.empty-section {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.text-danger {
  color: var(--status-danger-color);
}

.text-success {
  color: var(--status-success-color);
}

.error-state {
  padding: 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

@media (max-width: 640px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>

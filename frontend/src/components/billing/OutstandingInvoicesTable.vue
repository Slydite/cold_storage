<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Download, Eye } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import InvoiceDetailDialog from '../invoicing/InvoiceDetailDialog.vue'
import type { InvoiceOutput } from '../../api/invoicing'

const props = defineProps<{
  invoices: InvoiceOutput[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const { t } = useI18n()

const searchQuery = ref('')
const selectedPaymentStatus = ref('')

const selectedInvoice = ref<InvoiceOutput | null>(null)
const showDetailDialog = ref(false)

function handleOpenDetail(invoice: InvoiceOutput) {
  selectedInvoice.value = invoice
  showDetailDialog.value = true
}

const paymentStatusOptions = computed(() => [
  { label: t('common.allStatuses'), value: '' },
  { label: t('status.unpaid'), value: 'UNPAID' },
  { label: t('status.partial'), value: 'PARTIAL' },
  { label: t('status.paid'), value: 'PAID' }
])

function buildDefaultFilters() {
  return {
    invoice_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    invoice_date: { value: null, matchMode: FilterMatchMode.CONTAINS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (searchQuery.value.trim() !== '') count++
  if (selectedPaymentStatus.value !== '') count++
  return count
})

const {
  filters,
  showFilterRow,
  activeFilterCount,
  hasActiveFilters,
  clearFilters,
  toggleFilterRow
} = useTableFilters(buildDefaultFilters, extraActiveCount)

const filteredInvoices = computed(() => {
  return props.invoices.filter((inv) => {
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim()
      const matchSearch =
        inv.invoice_number.toLowerCase().includes(q) ||
        inv.party_name.toLowerCase().includes(q)
      if (!matchSearch) return false
    }
    if (selectedPaymentStatus.value) {
      if (inv.payment_status !== selectedPaymentStatus.value) return false
    }
    return true
  })
})

function handleClearAll() {
  clearFilters()
  searchQuery.value = ''
  selectedPaymentStatus.value = ''
}

const handleExport = () => {
  const headers = [
    t('invoicing.invoiceNumber'),
    t('grn.party'),
    t('invoicing.invoiceDate'),
    t('invoicing.total'),
    t('invoicing.paid'),
    t('invoicing.due'),
    t('invoicing.paymentStatus')
  ]
  const rows = filteredInvoices.value.map((inv) => [
    inv.invoice_number,
    inv.party_name,
    inv.invoice_date,
    formatCurrency(Number(inv.total_amount || 0)),
    formatCurrency(Number(inv.amount_paid || 0)),
    formatCurrency(Number(inv.amount_due || 0)),
    inv.payment_status || '-'
  ])
  exportToCsv('outstanding_invoices.csv', headers, rows)
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
  <div class="billing-section">
    <div class="section-header">
      <h3 class="section-title">{{ t('billing.outstandingInvoicesTitle') }}</h3>
      <p class="section-desc">{{ t('billing.outstandingInvoicesDesc') }}</p>
    </div>

    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('invoicing.searchPlaceholder')"
            class="custom-search-input"
          />
        </div>
        <Select
          v-model="selectedPaymentStatus"
          :options="paymentStatusOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
        />
      </div>

      <div class="toolbar-actions">
        <button
          class="btn-outlined"
          :class="{ active: showFilterRow }"
          type="button"
          :aria-pressed="showFilterRow"
          @click="toggleFilterRow"
          title="Toggle inline column filters"
        >
          <Filter :size="15" />
          <span>{{ t('common.filter') }}</span>
          <span v-if="hasActiveFilters" class="filter-count-badge">{{ activeFilterCount }}</span>
        </button>
        <button
          class="btn-outlined"
          type="button"
          :disabled="!hasActiveFilters"
          @click="handleClearAll"
          title="Clear all active filters and search"
        >
          <FilterX :size="15" />
          <span>{{ t('common.clear') }}</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>{{ t('common.export') }}</span>
        </button>
      </div>
    </div>

    <div class="table-card">
      <div v-if="filteredInvoices.length === 0" class="empty-section">
        <p>{{ t('common.noRecordsFound') }}</p>
      </div>

      <template v-else>
        <div class="hide-on-mobile">
          <DataTable
            :value="filteredInvoices"
            v-model:filters="filters"
            :filterDisplay="showFilterRow ? 'row' : 'menu'"
            paginator
            :rows="10"
            :rowsPerPageOptions="[10, 25, 50]"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column :header="t('common.actions')" style="width: 80px">
              <template #body="{ data }">
                <button
                  class="icon-btn"
                  :title="t('common.details')"
                  type="button"
                  @click="handleOpenDetail(data)"
                >
                  <Eye :size="16" />
                </button>
              </template>
            </Column>

            <Column field="invoice_number" :header="t('invoicing.invoiceNumber')" sortable>
              <template #body="{ data }">
                <span class="code-link clickable" @click="handleOpenDetail(data)">{{ data.invoice_number }}</span>
              </template>
              <template #filter="{ filterModel, filterCallback }">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  :placeholder="t('common.filter')"
                  class="p-column-filter"
                  size="small"
                />
              </template>
            </Column>

            <Column field="party_name" :header="t('grn.party')" sortable>
              <template #body="{ data }">
                <strong>{{ data.party_name }}</strong>
              </template>
              <template #filter="{ filterModel, filterCallback }">
                <InputText
                  v-model="filterModel.value"
                  type="text"
                  @input="filterCallback()"
                  :placeholder="t('common.filter')"
                  class="p-column-filter"
                  size="small"
                />
              </template>
            </Column>

            <Column field="invoice_date" :header="t('invoicing.invoiceDate')" sortable>
              <template #filter="{ filterModel, filterCallback }">
                <DatePicker
                  v-model="filterModel.value"
                  @update:modelValue="(val) => { filterModel.value = formatDateFilter(val); filterCallback() }"
                  dateFormat="yy-mm-dd"
                  placeholder="YYYY-MM-DD"
                  class="p-column-filter"
                  size="small"
                  showClear
                />
              </template>
            </Column>

            <Column field="total_amount" :header="t('invoicing.total')">
              <template #body="{ data }">
                <span class="num-val">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
              </template>
            </Column>

            <Column field="amount_paid" :header="t('invoicing.paid')">
              <template #body="{ data }">
                <span class="num-val text-success">{{ formatCurrency(Number(data.amount_paid || 0)) }}</span>
              </template>
            </Column>

            <Column field="amount_due" :header="t('invoicing.due')">
              <template #body="{ data }">
                <strong class="num-val text-danger">{{ formatCurrency(Number(data.amount_due || 0)) }}</strong>
              </template>
            </Column>

            <Column field="payment_status" :header="t('invoicing.paymentStatus')" sortable>
              <template #body="{ data }">
                <Tag
                  :value="t(`status.${(data.payment_status || 'UNPAID').toLowerCase()}`)"
                  :severity="getPaymentSeverity(data.payment_status)"
                />
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- Mobile Card Layout -->
        <div class="mobile-list-cards show-on-mobile">
          <div v-for="data in filteredInvoices" :key="data.id" class="mobile-list-card">
            <div class="card-header clickable" @click="handleOpenDetail(data)">
              <span class="card-title">{{ data.invoice_number }}</span>
              <Tag
                :value="t(`status.${(data.payment_status || 'UNPAID').toLowerCase()}`)"
                :severity="getPaymentSeverity(data.payment_status)"
              />
            </div>
            <div class="card-body">
              <div class="card-row">
                <span class="card-label">{{ t('grn.party') }}:</span>
                <span class="card-value">{{ data.party_name }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">{{ t('invoicing.total') }}:</span>
                <span class="card-value num-val">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">{{ t('invoicing.due') }}:</span>
                <span class="card-value num-val text-danger">{{ formatCurrency(Number(data.amount_due || 0)) }}</span>
              </div>
            </div>
            <div class="card-actions">
              <button class="btn-outlined btn-sm" :title="t('common.details')" type="button" @click="handleOpenDetail(data)">
                <Eye :size="15" />
                <span>{{ t('common.details') }}</span>
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Detail Dialog -->
    <InvoiceDetailDialog
      v-model:visible="showDetailDialog"
      :invoice="selectedInvoice"
      @refresh="emit('refresh')"
    />
  </div>
</template>

<style scoped>
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
</style>

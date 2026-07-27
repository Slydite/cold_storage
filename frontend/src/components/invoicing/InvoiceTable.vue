<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Filter,
  FilterX,
  Download,
  Plus,
  AlertCircle,
  RefreshCw,
  FileText,
  FileCheck,
  XCircle,
  Printer,
  CreditCard,
  Eye
} from 'lucide-vue-next'
import { formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import { downloadPdf } from '../../utils/downloadPdf'
import InvoiceDetailDialog from './InvoiceDetailDialog.vue'
import RecordPaymentDialog from './RecordPaymentDialog.vue'
import type { InvoiceOutput } from '../../api/invoicing'

interface Props {
  invoices: InvoiceOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedStatus: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedStatus': [status: string]
  openGenerate: []
  retry: []
  post: [id: number]
  cancel: [id: number]
  refresh: []
}>()

const toast = useToast()
const downloadingId = ref<number | null>(null)
const selectedInvoiceForDetail = ref<InvoiceOutput | null>(null)
const showDetailDialog = ref(false)
const selectedInvoiceForPayment = ref<InvoiceOutput | null>(null)
const showPaymentDialog = ref(false)

const openDetail = (inv: InvoiceOutput) => {
  selectedInvoiceForDetail.value = inv
  showDetailDialog.value = true
}

const openPayment = (inv: InvoiceOutput) => {
  selectedInvoiceForPayment.value = inv
  showPaymentDialog.value = true
}

async function handleDownloadPdf(id: number, docNumber: string) {
  downloadingId.value = id
  try {
    await downloadPdf(`/api/invoices/${id}/pdf/`, `${docNumber}.pdf`)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'PDF Failed',
      detail: err instanceof Error ? err.message : 'Could not generate PDF',
      life: 5000
    })
  } finally {
    downloadingId.value = null
  }
}

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Posted', value: 'POSTED' },
  { label: 'Cancelled', value: 'CANCELLED' }
]

const statusFilterOptions = [
  { label: 'DRAFT', value: 'DRAFT' },
  { label: 'POSTED', value: 'POSTED' },
  { label: 'CANCELLED', value: 'CANCELLED' }
]

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

function buildDefaultFilters() {
  return {
    invoice_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    invoice_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (props.searchQuery && props.searchQuery.trim() !== '') count++
  if (props.selectedStatus && props.selectedStatus !== '') count++
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

function handleClearAll() {
  clearFilters()
  emit('update:searchQuery', '')
  emit('update:selectedStatus', '')
}

const handleExport = () => {
  const headers = ['Invoice No.', 'Invoice Date', 'Party', 'GSTIN', 'Total', 'Paid', 'Due', 'Doc Status', 'Payment Status']
  const rows = props.invoices.map((inv) => [
    inv.invoice_number,
    inv.invoice_date,
    inv.party_name,
    inv.party_gstin_snapshot || '—',
    formatCurrency(Number(inv.total_amount || 0)),
    formatCurrency(Number(inv.amount_paid || 0)),
    formatCurrency(Number(inv.amount_due || 0)),
    inv.status || '-',
    inv.payment_status || 'UNPAID'
  ])
  exportToCsv('invoices.csv', headers, rows)
}
</script>

<template>
  <div class="master-list-container">
    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            :value="searchQuery"
            @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
            type="text"
            placeholder="Search invoice no., party..."
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedStatus"
          @update:modelValue="emit('update:selectedStatus', $event)"
          :options="statusOptions"
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
          <span>Filters</span>
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
          <span>Clear Filters</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>Export CSV</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('openGenerate')">
          <Plus :size="16" />
          <span>Generate Invoices</span>
        </button>
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load invoices</h4>
      <p class="state-desc">{{ props.errorDetail || 'There was an issue connecting to the server. Please try again.' }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Explicit State 2: Skeleton Loading State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="56px" class="mb-2" v-for="i in 5" :key="i" />
    </div>

    <!-- Explicit State 3: Empty State -->
    <div v-else-if="props.invoices.length === 0" class="state-card empty-card">
      <FileText :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No Invoice records found</h4>
      <p class="state-desc">Generate tax invoices from uninvoiced stock withdrawals.</p>
      <button class="btn-primary" type="button" @click="emit('openGenerate')">
        <Plus :size="16" />
        <span>Generate Invoices</span>
      </button>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.invoices"
        v-model:filters="filters"
        :filterDisplay="showFilterRow ? 'row' : 'menu'"
        paginator
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        sortMode="multiple"
        removableSort
        size="small"
        stripedRows
        dataKey="id"
        responsiveLayout="scroll"
        class="custom-datatable"
      >
        <Column field="invoice_number" header="Invoice No." sortable>
          <template #body="{ data }">
            <span class="code-link cursor-pointer" @click="openDetail(data)">{{ data.invoice_number }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Invoice No."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="invoice_date" header="Date" sortable>
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

        <Column field="party_name" header="Party" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.party_name }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter party..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column header="Total (₹)" sortable field="total_amount">
          <template #body="{ data }">
            <span class="num-val font-bold">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
          </template>
        </Column>

        <Column header="Paid (₹)">
          <template #body="{ data }">
            <span class="num-val text-success">{{ formatCurrency(Number(data.amount_paid || 0)) }}</span>
          </template>
        </Column>

        <Column header="Amount Due (₹)">
          <template #body="{ data }">
            <strong class="num-val text-danger">{{ formatCurrency(Number(data.amount_due || 0)) }}</strong>
          </template>
        </Column>

        <Column field="payment_status" header="Payment Status" sortable>
          <template #body="{ data }">
            <Tag
              :value="data.payment_status || 'UNPAID'"
              :severity="getPaymentSeverity(data.payment_status)"
            />
          </template>
        </Column>

        <Column field="status" header="Doc Status" sortable>
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="{
                success: data.status === 'POSTED',
                warning: data.status === 'DRAFT',
                danger: data.status === 'CANCELLED'
              }"
            >
              {{ data.status }}
            </span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <Select
              v-model="filterModel.value"
              @change="filterCallback()"
              :options="statusFilterOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Status"
              class="p-column-filter"
              size="small"
              showClear
            />
          </template>
        </Column>

        <Column header="Actions">
          <template #body="{ data }">
            <div class="row-actions">
              <button
                class="icon-btn"
                title="View Invoice Detail"
                type="button"
                @click="openDetail(data)"
              >
                <Eye :size="16" />
              </button>

              <button
                v-if="data.payment_status !== 'PAID'"
                class="icon-btn highlight-hover"
                title="Record Payment"
                type="button"
                @click="openPayment(data)"
              >
                <CreditCard :size="16" />
              </button>

              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn"
                title="Post Invoice"
                type="button"
                @click="emit('post', data.id)"
              >
                <FileCheck :size="16" />
              </button>

              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn danger-hover"
                title="Cancel Invoice"
                type="button"
                @click="emit('cancel', data.id)"
              >
                <XCircle :size="16" />
              </button>

              <button
                class="icon-btn"
                title="PDF"
                aria-label="PDF"
                type="button"
                :disabled="downloadingId === data.id"
                @click="handleDownloadPdf(data.id, data.invoice_number)"
              >
                <Printer :size="16" />
              </button>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Detail Dialog -->
    <InvoiceDetailDialog
      v-model:visible="showDetailDialog"
      :invoice="selectedInvoiceForDetail"
      @refresh="emit('refresh')"
    />

    <!-- Record Payment Dialog -->
    <RecordPaymentDialog
      v-model:visible="showPaymentDialog"
      :invoice="selectedInvoiceForPayment"
      @success="emit('refresh')"
    />
  </div>
</template>

<style scoped>
.master-list-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.25s ease;
}

.font-bold {
  font-weight: 700;
}

.cursor-pointer {
  cursor: pointer;
}

.text-success {
  color: var(--status-success-color);
}

.text-danger {
  color: var(--status-danger-color);
}

.highlight-hover:hover {
  color: var(--accent-primary);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.state-icon {
  margin-bottom: 4px;
}

.state-icon.text-danger {
  color: var(--status-danger-color);
}

.state-icon.text-muted {
  color: var(--text-secondary);
}

.state-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.state-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 380px;
  margin-bottom: 8px;
}

.skeleton-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 20px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>

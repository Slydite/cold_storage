<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Filter,
  FilterX,
  Download,
  Plus,
  Eye,
  AlertCircle,
  RefreshCw,
  Receipt,
  FileCheck,
  XCircle,
  CreditCard,
  Printer
} from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()
const selectedInvoiceForDetail = ref<InvoiceOutput | null>(null)
const selectedInvoiceForPayment = ref<InvoiceOutput | null>(null)
const showDetailDialog = ref(false)
const showPaymentDialog = ref(false)
const downloadingId = ref<number | null>(null)

watch(() => props.invoices, (newInvoices) => {
  if (selectedInvoiceForDetail.value) {
    const updated = newInvoices.find(item => item.id === selectedInvoiceForDetail.value?.id)
    if (updated) {
      selectedInvoiceForDetail.value = updated
    }
  }
}, { deep: true })

async function handleDownloadPdf(id: number, docNumber: string) {
  downloadingId.value = id
  try {
    await downloadPdf(`/api/invoices/${id}/pdf/`, `${docNumber}.pdf`)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.pdfFailed'),
      detail: err instanceof Error ? err.message : t('common.pdfFailed'),
      life: 5000
    })
  } finally {
    downloadingId.value = null
  }
}

const statusOptions = computed(() => [
  { label: t('common.allStatuses'), value: '' },
  { label: t('status.posted'), value: 'POSTED' },
  { label: t('status.draft'), value: 'DRAFT' },
  { label: t('status.cancelled'), value: 'CANCELLED' }
])

function buildDefaultFilters() {
  return {
    invoice_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    invoice_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS },
    payment_status: { value: null, matchMode: FilterMatchMode.EQUALS }
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

function handleOpenDetail(inv: InvoiceOutput) {
  selectedInvoiceForDetail.value = inv
  showDetailDialog.value = true
}

function handleOpenPayment(inv: InvoiceOutput) {
  selectedInvoiceForPayment.value = inv
  showPaymentDialog.value = true
}

function handlePaymentSuccess() {
  emit('refresh')
}

const handleExport = () => {
  const headers = [
    t('invoicing.invoiceNumber'),
    t('invoicing.invoiceDate'),
    t('grn.party'),
    t('invoicing.total'),
    t('invoicing.paid'),
    t('invoicing.due'),
    t('invoicing.docStatus'),
    t('invoicing.paymentStatus')
  ]
  const rows = props.invoices.map((inv) => [
    inv.invoice_number,
    inv.invoice_date,
    inv.party_name,
    formatCurrency(Number(inv.total_amount || 0)),
    formatCurrency(Number(inv.amount_paid || 0)),
    formatCurrency(Number(inv.amount_due || 0)),
    inv.status || '-',
    inv.payment_status || '-'
  ])
  exportToCsv('invoices.csv', headers, rows)
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
            :placeholder="t('invoicing.searchPlaceholder')"
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
        <button class="btn-primary" type="button" @click="emit('openGenerate')">
          <Plus :size="16" />
          <span>{{ t('invoicing.generateInvoices') }}</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">{{ t('invoicing.failedToLoad') }}</h4>
      <p class="state-desc">{{ props.errorDetail || t('errors.network') }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>{{ t('common.retry') }}</span>
      </button>
    </div>

    <!-- Skeleton Loading State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="56px" class="mb-2" v-for="i in 5" :key="i" />
    </div>

    <!-- Empty State -->
    <div v-else-if="props.invoices.length === 0" class="state-card empty-card">
      <Receipt :size="40" class="state-icon text-muted" />
      <h4 class="state-title">{{ t('invoicing.noInvoicesFound') }}</h4>
      <p class="state-desc">{{ t('invoicing.noInvoicesDesc') }}</p>
      <button class="btn-primary" type="button" @click="emit('openGenerate')">
        <Plus :size="16" />
        <span>{{ t('invoicing.generateInvoices') }}</span>
      </button>
    </div>

    <!-- DataTable View & Mobile Cards -->
    <template v-else>
      <div class="table-card hide-on-mobile">
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
          <Column :header="t('common.actions')">
            <template #body="{ data }">
              <div class="row-actions">
                <button class="icon-btn" :title="t('common.details')" type="button" @click="handleOpenDetail(data)">
                  <Eye :size="16" />
                </button>

                <button
                  v-if="data.status === 'DRAFT'"
                  class="icon-btn"
                  :title="t('invoicing.postTooltip')"
                  type="button"
                  @click="emit('post', data.id)"
                >
                  <FileCheck :size="16" />
                </button>

                <button
                  v-if="data.status === 'DRAFT'"
                  class="icon-btn danger-hover"
                  :title="t('invoicing.cancelTooltip')"
                  type="button"
                  @click="emit('cancel', data.id)"
                >
                  <XCircle :size="16" />
                </button>

                <button
                  v-if="data.status === 'POSTED' && data.payment_status !== 'PAID'"
                  class="icon-btn success-hover"
                  :title="t('invoicing.recordPayment')"
                  type="button"
                  @click="handleOpenPayment(data)"
                >
                  <CreditCard :size="16" />
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

          <Column field="invoice_number" :header="t('invoicing.invoiceNumber')" sortable>
            <template #body="{ data }">
              <span class="code-link clickable" @click="handleOpenDetail(data)">{{ data.invoice_number }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText
                v-model="filterModel.value"
                type="text"
                @input="filterCallback()"
                placeholder="Filter..."
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

          <Column field="party_name" :header="t('grn.party')" sortable>
            <template #body="{ data }">
              <strong class="party-name">{{ data.party_name }}</strong>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText
                v-model="filterModel.value"
                type="text"
                @input="filterCallback()"
                placeholder="Filter..."
                class="p-column-filter"
                size="small"
              />
            </template>
          </Column>

          <Column field="total_amount" :header="t('invoicing.total')" sortable>
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

          <Column field="status" :header="t('invoicing.docStatus')" sortable>
            <template #body="{ data }">
              <Tag
                :value="t(`status.${(data.status || 'draft').toLowerCase()}`)"
                :disabled="false"
                :severity="data.status === 'POSTED' ? 'success' : data.status === 'CANCELLED' ? 'secondary' : 'warn'"
              />
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
        <div v-for="data in props.invoices" :key="data.id" class="mobile-list-card">
          <div class="card-header clickable" @click="handleOpenDetail(data)">
            <span class="card-title">{{ data.invoice_number }}</span>
            <div class="flex gap-2">
              <Tag
                :value="t(`status.${(data.status || 'draft').toLowerCase()}`)"
                :severity="data.status === 'POSTED' ? 'success' : data.status === 'CANCELLED' ? 'secondary' : 'warn'"
              />
              <Tag
                :value="t(`status.${(data.payment_status || 'UNPAID').toLowerCase()}`)"
                :severity="getPaymentSeverity(data.payment_status)"
              />
            </div>
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

            <button
              v-if="data.status === 'DRAFT'"
              class="btn-outlined btn-sm"
              :title="t('invoicing.postTooltip')"
              type="button"
              @click="emit('post', data.id)"
            >
              <FileCheck :size="15" />
              <span>{{ t('invoicing.postTooltip') }}</span>
            </button>

            <button
              v-if="data.status === 'DRAFT'"
              class="btn-outlined btn-sm danger-hover"
              :title="t('invoicing.cancelTooltip')"
              type="button"
              @click="emit('cancel', data.id)"
            >
              <XCircle :size="15" />
              <span>{{ t('invoicing.cancelTooltip') }}</span>
            </button>

            <button
              v-if="data.status === 'POSTED' && data.payment_status !== 'PAID'"
              class="btn-outlined btn-sm success-hover"
              :title="t('invoicing.recordPayment')"
              type="button"
              @click="handleOpenPayment(data)"
            >
              <CreditCard :size="15" />
              <span>{{ t('invoicing.recordPayment') }}</span>
            </button>

            <button
              class="btn-outlined btn-sm"
              title="PDF"
              aria-label="PDF"
              type="button"
              :disabled="downloadingId === data.id"
              @click="handleDownloadPdf(data.id, data.invoice_number)"
            >
              <Printer :size="15" />
              <span>{{ downloadingId === data.id ? '...' : 'PDF' }}</span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Detail Dialog -->
    <InvoiceDetailDialog
      v-model:visible="showDetailDialog"
      :invoice="selectedInvoiceForDetail"
      @recordPayment="handleOpenPayment"
      @refresh="emit('refresh')"
    />

    <!-- Record Payment Dialog -->
    <RecordPaymentDialog
      v-model:visible="showPaymentDialog"
      :invoice="selectedInvoiceForPayment"
      @success="handlePaymentSuccess"
    />
  </div>
</template>

<style scoped>
.code-link.clickable {
  cursor: pointer;
}
.master-list-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
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
.text-danger {
  color: var(--status-danger-color);
}
.text-success {
  color: var(--status-success-color);
}
.icon-btn.success-hover:hover {
  color: var(--status-success-color);
}
</style>

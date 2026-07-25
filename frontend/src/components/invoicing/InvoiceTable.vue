<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Download,
  Plus,
  AlertCircle,
  RefreshCw,
  FileText,
  FileCheck,
  XCircle,
  Printer
} from 'lucide-vue-next'
import { formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { InvoiceOutput } from '../../api/invoicing'

interface Props {
  invoices: InvoiceOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedStatus: string
  generatingPdfId?: number | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedStatus': [status: string]
  openGenerate: []
  retry: []
  post: [id: number]
  cancel: [id: number]
  generatePdf: [id: number]
}>()

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Posted', value: 'POSTED' },
  { label: 'Cancelled', value: 'CANCELLED' }
]

const filters = ref({
  invoice_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
  party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  invoice_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
  status: { value: null, matchMode: FilterMatchMode.EQUALS }
})

function resolvePdfUrl(url: string | null): string {
  if (!url) return '#'
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return url.startsWith('/') ? url : `/${url}`
}

const handleExport = () => {
  const headers = ['Invoice No.', 'Invoice Date', 'Party', 'GSTIN', 'Subtotal', 'GST', 'Total', 'Status']
  const rows = props.invoices.map((inv) => [
    inv.invoice_number,
    inv.invoice_date,
    inv.party_name,
    inv.party_gstin_snapshot || '—',
    formatCurrency(Number(inv.subtotal || 0)),
    formatCurrency(Number(inv.gst_amount || 0)),
    formatCurrency(Number(inv.total_amount || 0)),
    inv.status || '-'
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
      <p class="state-desc">Generate GST invoices from existing posted rent runs.</p>
      <button class="btn-primary" type="button" @click="emit('openGenerate')">
        <Plus :size="16" />
        <span>Generate GST Invoices</span>
      </button>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.invoices"
        v-model:filters="filters"
        filterDisplay="menu"
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
            <span class="code-link">{{ data.invoice_number }}</span>
          </template>
        </Column>

        <Column field="invoice_date" header="Date" sortable />

        <Column field="party_name" header="Party" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.party_name }}</span>
          </template>
        </Column>

        <Column field="party_gstin_snapshot" header="GSTIN">
          <template #body="{ data }">
            <span>{{ data.party_gstin_snapshot || '—' }}</span>
          </template>
        </Column>

        <Column header="Subtotal (₹)">
          <template #body="{ data }">
            <span class="num-val">{{ formatCurrency(Number(data.subtotal || 0)) }}</span>
          </template>
        </Column>

        <Column header="GST (₹)">
          <template #body="{ data }">
            <span class="num-val">{{ formatCurrency(Number(data.gst_amount || 0)) }}</span>
          </template>
        </Column>

        <Column header="Total (₹)" sortable field="total_amount">
          <template #body="{ data }">
            <span class="num-val">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
          </template>
        </Column>

        <Column field="status" header="Status" sortable>
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
        </Column>

        <Column header="Actions">
          <template #body="{ data }">
            <div class="row-actions">
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

              <a
                v-if="data.pdf_url"
                :href="resolvePdfUrl(data.pdf_url)"
                target="_blank"
                download
                class="icon-btn"
                title="Download PDF"
              >
                <Download :size="16" />
              </a>

              <button
                v-else
                class="icon-btn"
                title="Generate PDF"
                type="button"
                :disabled="props.generatingPdfId === data.id"
                @click="emit('generatePdf', data.id)"
              >
                <Printer :size="16" />
              </button>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
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

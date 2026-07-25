<script setup lang="ts">
import { ref } from 'vue'
import Select from 'primevue/select'
import { FileText, Download, Eye, AlertCircle, Truck, PackageCheck, Receipt } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { fetchReportJson, downloadReportCsv } from '../../composables/useReportExport'
import { formatCurrency } from '../../utils/format'

interface Props {
  title: string
  description: string
  endpoint: string
  reportType: 'grn' | 'dn' | 'invoice'
  facilityId?: number
}

const props = defineProps<Props>()
const toast = useToast()

const dateFrom = ref('')
const dateTo = ref('')
const selectedStatus = ref('')

const loadingJson = ref(false)
const downloadingCsv = ref(false)
const showPreview = ref(false)
const previewRows = ref<Record<string, unknown>[] | null>(null)
const errorDetail = ref<string | null>(null)

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Posted', value: 'POSTED' },
  { label: 'Cancelled', value: 'CANCELLED' }
]

function getIconComponent() {
  switch (props.reportType) {
    case 'grn':
      return PackageCheck
    case 'dn':
      return Truck
    case 'invoice':
      return Receipt
    default:
      return FileText
  }
}

function getFilename() {
  switch (props.reportType) {
    case 'grn':
      return 'grn_register.csv'
    case 'dn':
      return 'dn_register.csv'
    case 'invoice':
      return 'invoice_register.csv'
    default:
      return 'register.csv'
  }
}

async function handlePreview() {
  if (showPreview.value && previewRows.value) {
    showPreview.value = false
    return
  }

  loadingJson.value = true
  errorDetail.value = null
  try {
    const data = await fetchReportJson<Record<string, unknown>[]>(props.endpoint, {
      facility_id: props.facilityId,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined,
      status: selectedStatus.value || undefined
    })
    previewRows.value = Array.isArray(data) ? data : []
    showPreview.value = true
  } catch (err) {
    errorDetail.value = err instanceof Error ? err.message : 'Failed to load preview'
    toast.add({
      severity: 'error',
      summary: 'Preview Error',
      detail: errorDetail.value,
      life: 4000
    })
  } finally {
    loadingJson.value = false
  }
}

async function handleDownloadCsv() {
  downloadingCsv.value = true
  try {
    await downloadReportCsv(
      props.endpoint,
      {
        facility_id: props.facilityId,
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined,
        status: selectedStatus.value || undefined
      },
      getFilename()
    )
    toast.add({
      severity: 'success',
      summary: 'Export Started',
      detail: `${props.title} CSV downloaded.`,
      life: 3000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: err instanceof Error ? err.message : 'Failed to download report CSV',
      life: 4000
    })
  } finally {
    downloadingCsv.value = false
  }
}
</script>

<template>
  <div class="report-card">
    <div class="card-top">
      <div class="report-icon-box">
        <component :is="getIconComponent()" :size="24" />
      </div>
      <div class="title-area">
        <h4 class="rep-title">{{ title }}</h4>
        <p class="rep-desc">{{ description }}</p>
      </div>
    </div>

    <!-- Filters Row -->
    <div class="filters-row">
      <div class="filter-field">
        <label>Date From</label>
        <input type="date" v-model="dateFrom" class="date-input" />
      </div>

      <div class="filter-field">
        <label>Date To</label>
        <input type="date" v-model="dateTo" class="date-input" />
      </div>

      <div class="filter-field">
        <label>Status</label>
        <Select
          v-model="selectedStatus"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          class="status-select"
        />
      </div>
    </div>

    <div v-if="errorDetail" class="card-error">
      <AlertCircle :size="16" />
      <span>{{ errorDetail }}</span>
    </div>

    <!-- Inline Preview Table -->
    <div v-if="showPreview && previewRows" class="preview-container">
      <div class="preview-header">
        <span>Found <strong>{{ previewRows.length }}</strong> record(s)</span>
      </div>

      <div v-if="previewRows.length === 0" class="muted-text">
        No records matching selected criteria.
      </div>

      <table v-else class="mini-table">
        <thead>
          <tr v-if="reportType === 'grn'">
            <th>GRN No.</th>
            <th>Date</th>
            <th>Party</th>
            <th>Status</th>
          </tr>
          <tr v-else-if="reportType === 'dn'">
            <th>DN No.</th>
            <th>Date</th>
            <th>Party</th>
            <th>Status</th>
          </tr>
          <tr v-else-if="reportType === 'invoice'">
            <th>Invoice No.</th>
            <th>Date</th>
            <th>Party</th>
            <th>GSTIN</th>
            <th class="text-right">Total (₹)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in previewRows.slice(0, 5)" :key="idx">
            <template v-if="reportType === 'grn'">
              <td class="code-link">{{ String(row.grn_number || '-') }}</td>
              <td>{{ String(row.receipt_date || '-') }}</td>
              <td>{{ String(row.party_name || '-') }}</td>
              <td>
                <span class="status-pill" :class="{ success: row.status === 'POSTED', warning: row.status === 'DRAFT', danger: row.status === 'CANCELLED' }">
                  {{ String(row.status || '-') }}
                </span>
              </td>
            </template>

            <template v-else-if="reportType === 'dn'">
              <td class="code-link">{{ String(row.dn_number || '-') }}</td>
              <td>{{ String(row.dispatch_date || '-') }}</td>
              <td>{{ String(row.party_name || '-') }}</td>
              <td>
                <span class="status-pill" :class="{ success: row.status === 'POSTED', warning: row.status === 'DRAFT', danger: row.status === 'CANCELLED' }">
                  {{ String(row.status || '-') }}
                </span>
              </td>
            </template>

            <template v-else-if="reportType === 'invoice'">
              <td class="code-link">{{ String(row.invoice_number || '-') }}</td>
              <td>{{ String(row.invoice_date || '-') }}</td>
              <td>{{ String(row.party_name || '-') }}</td>
              <td>{{ String(row.party_gstin_snapshot || '—') }}</td>
              <td class="text-right num-val">{{ formatCurrency(Number(row.total_amount || 0)) }}</td>
              <td>
                <span class="status-pill" :class="{ success: row.status === 'POSTED', warning: row.status === 'DRAFT', danger: row.status === 'CANCELLED' }">
                  {{ String(row.status || '-') }}
                </span>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      <div v-if="previewRows.length > 5" class="preview-more">
        + {{ previewRows.length - 5 }} more records (download CSV for full register)
      </div>
    </div>

    <div class="card-bottom">
      <button
        class="btn-outlined"
        type="button"
        @click="handlePreview"
        :disabled="loadingJson"
      >
        <Eye :size="15" />
        <span>{{ loadingJson ? 'Loading...' : showPreview ? 'Hide Preview' : 'Preview' }}</span>
      </button>

      <button
        class="btn-primary"
        type="button"
        @click="handleDownloadCsv"
        :disabled="downloadingCsv"
      >
        <Download :size="15" />
        <span>{{ downloadingCsv ? 'Exporting...' : 'Download CSV' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.report-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.report-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.title-area {
  flex: 1;
}

.rep-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.rep-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.filters-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 110px;
}

.filter-field label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.date-input {
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 12.5px;
  font-family: inherit;

}

.date-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.status-select {
  font-size: 12.5px !important;
  border-radius: 8px !important;
}

.card-error {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--status-danger-bg);
  color: var(--status-danger-color);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12.5px;
}

.preview-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px;
}

.preview-header {
  font-size: 12px;
  color: var(--text-secondary);
}

.muted-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.mini-table th,
.mini-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.mini-table th {
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-surface);
}

.text-right {
  text-align: right;
}

.num-val {
  font-feature-settings: 'tnum';
  font-weight: 600;
}

.code-link {
  font-weight: 700;
  color: var(--accent-primary);
}

.preview-more {
  font-size: 11.5px;
  color: var(--text-secondary);
  text-align: center;
  margin-top: 4px;
}

.card-bottom {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: auto;
}
</style>

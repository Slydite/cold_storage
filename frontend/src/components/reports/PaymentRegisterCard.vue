<script setup lang="ts">
import { ref, computed } from 'vue'
import Select from 'primevue/select'
import { useI18n } from 'vue-i18n'
import { CreditCard, Download, Eye, AlertCircle } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { fetchReportJson, downloadReportCsv } from '../../composables/useReportExport'
import { formatCurrency } from '../../utils/format'
import { usePartyList } from '../../composables/useParties'
import type { PaymentRegisterResponse, PaymentRegisterOutput } from '../../api/generated/types.gen'

interface Props {
  title: string
  description: string
  endpoint: string
  facilityId?: number
}

const props = defineProps<Props>()
const { t } = useI18n()
const toast = useToast()

const dateFrom = ref('')
const dateTo = ref('')
const selectedPartyId = ref<number | ''>('')
const selectedMethod = ref('')

const loadingJson = ref(false)
const downloadingCsv = ref(false)
const showPreview = ref(false)
const previewRows = ref<PaymentRegisterOutput[] | null>(null)
const totalAmountCollected = ref<string>('0')
const errorDetail = ref<string | null>(null)

// Fetch parties for select filter
const partiesQuery = usePartyList(computed(() => props.facilityId))
const partyOptions = computed(() => [
  { label: t('common.allParties'), value: '' },
  ...(partiesQuery.data.value || []).map((p) => ({ label: p.name, value: p.id }))
])

const methodOptions = computed(() => [
  { label: t('reports.allMethods'), value: '' },
  { label: t('paymentMethod.CASH'), value: 'CASH' },
  { label: t('paymentMethod.BANK_TRANSFER'), value: 'BANK_TRANSFER' },
  { label: t('paymentMethod.CHEQUE'), value: 'CHEQUE' },
  { label: t('paymentMethod.UPI'), value: 'UPI' },
  { label: t('paymentMethod.OTHER'), value: 'OTHER' }
])

async function handlePreview() {
  if (showPreview.value && previewRows.value) {
    showPreview.value = false
    return
  }

  loadingJson.value = true
  errorDetail.value = null
  try {
    const data = await fetchReportJson<PaymentRegisterResponse>(props.endpoint, {
      facility_id: props.facilityId,
      party_id: selectedPartyId.value || undefined,
      method: selectedMethod.value || undefined,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined
    })
    previewRows.value = data.results ?? []
    totalAmountCollected.value = data.total_amount || '0'
    showPreview.value = true
  } catch (err) {
    errorDetail.value = err instanceof Error ? err.message : t('reports.failedToLoadPreview')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
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
        party_id: selectedPartyId.value || undefined,
        method: selectedMethod.value || undefined,
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined
      },
      'payment_register.csv'
    )
    toast.add({
      severity: 'success',
      summary: t('reports.exportStarted'),
      detail: t('reports.exportStartedDetail', { title: props.title }),
      life: 3000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.exportFailed'),
      detail: err instanceof Error ? err.message : t('common.exportFailed'),
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
        <CreditCard :size="24" />
      </div>
      <div class="title-area">
        <h4 class="rep-title">{{ title }}</h4>
        <p class="rep-desc">{{ description }}</p>
      </div>
    </div>

    <!-- Filters Row -->
    <div class="filters-row">
      <div class="filter-field">
        <label>{{ t('reports.dateFrom') }}</label>
        <input type="date" v-model="dateFrom" class="date-input" />
      </div>

      <div class="filter-field">
        <label>{{ t('reports.dateTo') }}</label>
        <input type="date" v-model="dateTo" class="date-input" />
      </div>

      <div class="filter-field">
        <label>{{ t('common.allParties') }}</label>
        <Select
          v-model="selectedPartyId"
          :options="partyOptions"
          optionLabel="label"
          optionValue="value"
          class="status-select"
          :placeholder="t('common.allParties')"
        />
      </div>

      <div class="filter-field">
        <label>{{ t('invoicing.paymentMethod') }}</label>
        <Select
          v-model="selectedMethod"
          :options="methodOptions"
          optionLabel="label"
          optionValue="value"
          class="status-select"
          :placeholder="t('invoicing.paymentMethod')"
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
        <span>{{ t('reports.foundRecords', { count: previewRows.length }) }}</span>
      </div>

      <!-- Prominent Server-Side Total collected -->
      <div class="total-collected-banner">
        <span>{{ t('common.totalAmount') }}:</span>
        <strong class="total-amount-val">{{ formatCurrency(Number(totalAmountCollected)) }}</strong>
      </div>

      <div v-if="previewRows.length === 0" class="muted-text">
        {{ t('reports.noRecordsMatching') }}
      </div>

      <table v-else class="mini-table">
        <thead>
          <tr>
            <th>{{ t('common.date') }}</th>
            <th>{{ t('invoicing.invoiceNumber') }}</th>
            <th>{{ t('grn.party') }}</th>
            <th>{{ t('invoicing.paymentMethod') }}</th>
            <th>{{ t('invoicing.transactionRefNo') }}</th>
            <th class="text-right">{{ t('common.amount') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in previewRows.slice(0, 5)" :key="idx">
            <td>{{ row.payment_date || '-' }}</td>
            <td class="code-link">{{ row.invoice_number || '-' }}</td>
            <td>{{ row.party_name || '-' }}</td>
            <td>{{ row.method_display || '-' }}</td>
            <td>{{ row.reference || '-' }}</td>
            <td class="text-right num-val">{{ formatCurrency(Number(row.amount || 0)) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="previewRows.length > 5" class="preview-more">
        {{ t('reports.moreRecords', { count: previewRows.length - 5 }) }}
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
        <span>{{ loadingJson ? t('common.loading') : showPreview ? t('common.hidePreview') : t('common.preview') }}</span>
      </button>

      <button
        class="btn-primary"
        type="button"
        @click="handleDownloadCsv"
        :disabled="downloadingCsv"
      >
        <Download :size="15" />
        <span>{{ downloadingCsv ? t('common.exporting') : t('common.downloadCsv') }}</span>
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
  width: 100%;
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

.total-collected-banner {
  background: var(--accent-primary-light);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border-subtle);
}

.total-amount-val {
  font-size: 15px;
  color: var(--accent-primary);
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

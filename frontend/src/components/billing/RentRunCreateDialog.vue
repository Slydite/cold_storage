<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useQuery } from '@tanstack/vue-query'
import { Calculator, ArrowLeft, AlertTriangle, Eye } from 'lucide-vue-next'
import { fetchCommodities } from '../../api/commodity'
import { fetchParties } from '../../api/party'
import { fetchChambers } from '../../api/location'
import { useRentRunForm } from '../../composables/useRentRunForm'
import { formatCurrency, formatQty } from '../../utils/format'
import type { RentRunOutput } from '../../api/billing'

interface Props {
  visible: boolean
  facilityId: number | undefined
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: [rentRun: RentRunOutput]
}>()

const facilityIdRef = computed(() => props.facilityId)

const commoditiesQuery = useQuery({
  queryKey: computed(() => ['commodities', props.facilityId]),
  queryFn: () => fetchCommodities({ facilityId: props.facilityId! }),
  enabled: computed(() => !!props.facilityId && props.visible)
})

const partiesQuery = useQuery({
  queryKey: computed(() => ['parties', props.facilityId]),
  queryFn: () => fetchParties({ facilityId: props.facilityId! }),
  enabled: computed(() => !!props.facilityId && props.visible)
})

const chambersQuery = useQuery({
  queryKey: computed(() => ['chambers', props.facilityId]),
  queryFn: () => fetchChambers({ facilityId: props.facilityId! }),
  enabled: computed(() => !!props.facilityId && props.visible)
})

const partyOptions = computed(() => {
  const list = (partiesQuery.data.value || []).map((p) => ({
    label: `${p.name} (${p.code})`,
    value: p.id
  }))
  return [{ label: 'All Parties', value: null }, ...list]
})

const commodityOptions = computed(() => {
  const list = (commoditiesQuery.data.value || []).map((c) => ({
    label: `${c.name} (${c.code})`,
    value: c.id
  }))
  return [{ label: 'All Commodities', value: null }, ...list]
})

const chamberOptions = computed(() => {
  const list = (chambersQuery.data.value || []).map((ch) => ({
    label: ch.name,
    value: ch.name
  }))
  return [{ label: 'All Chambers', value: '' }, ...list]
})

const {
  period_start,
  periodStartProps,
  period_end,
  periodEndProps,
  party_id,
  partyIdProps,
  commodity_id,
  commodityIdProps,
  chamber,
  chamberProps,
  min_billing_days,
  minBillingDaysProps,
  notes,
  notesProps,
  step,
  previewData,
  isPreviewing,
  isSubmitting,
  handlePreview,
  backToParameters,
  errors,
  submitForm,
  resetForm
} = useRentRunForm(facilityIdRef, (createdRun) => {
  emit('update:visible', false)
  emit('created', createdRun)
})

const hasMissingRateCards = computed(() => {
  return (previewData.value?.missing_rate_cards?.length ?? 0) > 0
})

const handleClose = () => {
  resetForm()
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="step === 1 ? 'Execute Rent Run - Step 1: Parameters' : 'Execute Rent Run - Step 2: Preview Results'"
    :style="{ width: step === 1 ? '540px' : '840px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <!-- STEP 1: PARAMETERS -->
    <div v-if="step === 1" class="form-dialog-body">
      <p class="dialog-hint">
        Specify billing parameters. Storage rent will be prorated by days stored. Click <strong>Preview Rent Run</strong> to review lot calculations and rate cards before committing.
      </p>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Period Start Date <span class="req">*</span></label>
          <DatePicker
            v-model="period_start"
            v-bind="periodStartProps"
            dateFormat="dd/mm/yy"
            showIcon
            class="w-full"
            :invalid="!!errors.period_start"
          />
          <small v-if="errors.period_start" class="field-error">{{ errors.period_start }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">Period End Date <span class="req">*</span></label>
          <DatePicker
            v-model="period_end"
            v-bind="periodEndProps"
            dateFormat="dd/mm/yy"
            showIcon
            class="w-full"
            :invalid="!!errors.period_end"
          />
          <small v-if="errors.period_end" class="field-error">{{ errors.period_end }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">Filter by Party</label>
          <Select
            v-model="party_id"
            v-bind="partyIdProps"
            :options="partyOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="All Parties"
            :loading="partiesQuery.isLoading.value"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Filter by Commodity</label>
          <Select
            v-model="commodity_id"
            v-bind="commodityIdProps"
            :options="commodityOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="All Commodities"
            :loading="commoditiesQuery.isLoading.value"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Filter by Chamber</label>
          <Select
            v-model="chamber"
            v-bind="chamberProps"
            :options="chamberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="All Chambers"
            :loading="chambersQuery.isLoading.value"
            class="w-full"
            editable
          />
        </div>

        <div class="form-group">
          <label class="form-label">Min Billing Days</label>
          <InputNumber
            v-model="min_billing_days"
            v-bind="minBillingDaysProps"
            :min="0"
            :max="365"
            placeholder="0"
            class="w-full"
            :invalid="!!errors.min_billing_days"
          />
          <small class="field-hint">Bill at least this many days per lot, regardless of actual storage duration.</small>
        </div>
      </div>

      <div class="form-group full-width">
        <label class="form-label">Notes / Remarks</label>
        <Textarea
          v-model="notes"
          v-bind="notesProps"
          rows="2"
          placeholder="Optional notes for this billing run..."
          class="w-full"
        />
      </div>
    </div>

    <!-- STEP 2: PREVIEW -->
    <div v-else-if="step === 2 && previewData" class="preview-dialog-body">
      <!-- Summary bar -->
      <div class="preview-summary-bar">
        <div class="summary-col">
          <span class="summary-meta-label">Total Lots Billed</span>
          <span class="summary-meta-val">{{ previewData.lines.length }} lot(s)</span>
        </div>
        <div class="summary-col">
          <span class="summary-meta-label">Missing Rate Cards</span>
          <span class="summary-meta-val" :class="{ 'text-danger': hasMissingRateCards }">
            {{ previewData.missing_rate_cards.length }}
          </span>
        </div>
        <div class="summary-col highlight-col">
          <span class="summary-meta-label">Grand Total Rent</span>
          <span class="summary-meta-val total-rent-val">{{ formatCurrency(Number(previewData.total_amount || 0)) }}</span>
        </div>
      </div>

      <!-- Missing Rate Cards Warning Block -->
      <div v-if="hasMissingRateCards" class="missing-cards-alert">
        <div class="alert-header">
          <AlertTriangle :size="18" class="alert-icon" />
          <span class="alert-title">These lots have no applicable rate card and will block the run</span>
        </div>
        <p class="alert-sub">Please create rate cards matching the commodity and weight category for the lots listed below:</p>
        <div class="missing-items-grid">
          <div v-for="item in previewData.missing_rate_cards" :key="item.lot_number" class="missing-item-chip">
            <span class="chip-lot">Lot #{{ item.lot_number }}</span>
            <span class="chip-detail">{{ item.commodity_name }} &bull; {{ item.weight_category }}</span>
          </div>
        </div>
      </div>

      <!-- Preview Lines Table -->
      <div class="table-card preview-table-container">
        <DataTable
          :value="previewData.lines"
          size="small"
          stripedRows
          responsiveLayout="scroll"
          scrollable
          scrollHeight="300px"
        >
          <Column field="lot_number" header="Lot No.">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number }}</span>
            </template>
          </Column>

          <Column field="commodity_name" header="Commodity" />

          <Column field="party_name" header="Party / Customer">
            <template #body="{ data }">
              <span class="party-name">{{ data.party_name }}</span>
            </template>
          </Column>

          <Column field="qty" header="Qty">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.qty, 0) }}</span>
            </template>
          </Column>

          <Column field="weight_category" header="Category" />

          <Column field="rate_per_bag_per_month" header="Rate">
            <template #body="{ data }">
              <span class="num-val">{{ formatCurrency(Number(data.rate_per_bag_per_month)) }}</span>
            </template>
          </Column>

          <Column field="rate_source" header="Rate Source">
            <template #body="{ data }">
              <span
                class="status-pill"
                :class="data.rate_source === 'PARTY' ? 'success' : 'info'"
              >
                {{ data.rate_source }}
              </span>
            </template>
          </Column>

          <Column field="days_stored" header="Days">
            <template #body="{ data }">
              <span class="num-val">{{ data.days_stored }}</span>
            </template>
          </Column>

          <Column field="amount" header="Amount (₹)">
            <template #body="{ data }">
              <span class="num-val line-amount">{{ formatCurrency(Number(data.amount)) }}</span>
            </template>
          </Column>
        </DataTable>
      </div>

      <p v-if="previewData.lines.length === 0" class="empty-preview-msg">
        No active lots matched the selected parameters for this period.
      </p>
    </div>

    <template #footer>
      <div class="dialog-footer-actions">
        <button v-if="step === 1" class="btn-text" type="button" @click="handleClose">Cancel</button>
        <button
          v-if="step === 1"
          class="btn-primary"
          type="button"
          :disabled="isPreviewing"
          @click="handlePreview"
        >
          <Eye :size="16" />
          <span>{{ isPreviewing ? 'Generating Preview...' : 'Preview Rent Run' }}</span>
        </button>

        <button v-if="step === 2" class="btn-outlined" type="button" @click="backToParameters">
          <ArrowLeft :size="15" />
          <span>Back to Parameters</span>
        </button>
        <button
          v-if="step === 2"
          class="btn-primary"
          type="button"
          :disabled="hasMissingRateCards || isSubmitting"
          @click="submitForm"
          :title="hasMissingRateCards ? 'Cannot create rent run while there are missing rate cards' : ''"
        >
          <Calculator :size="16" />
          <span>{{ isSubmitting ? 'Creating Run...' : 'Create Rent Run' }}</span>
        </button>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.form-dialog-body,
.preview-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

.dialog-hint {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.4;
  background: var(--bg-surface-hover);
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.full-width {
  grid-column: span 2;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.req {
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.field-error {
  color: var(--status-danger-color);
  font-size: 11.5px;
}

.field-hint {
  color: var(--text-secondary);
  font-size: 11.5px;
  line-height: 1.3;
}

.preview-summary-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 16px;
}

.summary-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.summary-meta-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.summary-meta-val {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-meta-val.text-danger {
  color: var(--status-danger-color);
}

.total-rent-val {
  font-size: 16px;
  color: var(--accent-primary);
}

.missing-cards-alert {
  background: var(--status-danger-bg);
  border: 1px solid var(--status-danger-color);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--status-danger-color);
}

.alert-title {
  font-size: 13px;
  font-weight: 700;
}

.alert-sub {
  font-size: 12px;
  color: var(--text-primary);
}

.missing-items-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.missing-item-chip {
  background: rgba(244, 63, 94, 0.12);
  border: 1px solid var(--status-danger-color);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  gap: 6px;
}

.chip-lot {
  font-weight: 700;
  color: var(--status-danger-color);
}

.chip-detail {
  color: var(--text-primary);
}

.preview-table-container {
  max-height: 320px;
  overflow-y: auto;
}

.line-amount {
  font-weight: 700;
  color: var(--text-primary);
}

.empty-preview-msg {
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 16px 0;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .full-width {
    grid-column: span 1;
  }
  .preview-summary-bar {
    grid-template-columns: 1fr;
  }
}
</style>

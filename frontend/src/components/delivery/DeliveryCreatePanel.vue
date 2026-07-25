<script setup lang="ts">
import { computed } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import { useConfirm } from 'primevue/useconfirm'
import { Plus, Trash2, FileCheck } from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { useDeliveryNoteForm } from '../../composables/useDeliveryNoteForm'
import { useLotList } from '../../composables/useLots'
import type { PartyOutput } from '../../api/party'

interface Props {
  facilityId: number | undefined
  parties: PartyOutput[]
  loadingParties?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  created: [dnNumber: string, status: string]
}>()

const confirm = useConfirm()

const facilityIdRef = computed(() => props.facilityId)

// Fetch in-stock lots for the facility
const lotsQuery = useLotList(
  facilityIdRef,
  computed(() => ({
    inStockOnly: true
  }))
)

const availableLots = computed(() => lotsQuery.data.value || [])

const {
  party_id,
  partyIdProps,
  dispatch_date,
  dispatchDateProps,
  vehicle_number,
  vehicleNoProps,
  driver_name,
  driverNameProps,
  remarks,
  remarksProps,
  lines,
  errors,
  addLineRow,
  removeLineRow,
  totalQty,
  getLotAvailable,
  getLineQtyError,
  submitForm,
  isSubmitting
} = useDeliveryNoteForm(facilityIdRef, availableLots, (dnNumber, status) => emit('created', dnNumber, status))

const lotSelectOptions = computed(() => {
  return availableLots.value
    .filter((lot) => lot.remaining_qty > 0)
    .map((lot) => {
      const unit = lot.commodity_unit ? lot.commodity_unit.toUpperCase() : 'UNITS'
      return {
        id: lot.id,
        label: `${lot.lot_number} - ${lot.commodity_name} (${lot.remaining_qty} ${unit} available)`
      }
    })
})

const formatAvailableText = (lotId: number | null): string => {
  if (lotId == null) return '-'
  const avail = getLotAvailable(lotId)
  if (avail == null) return '-'
  const lot = availableLots.value.find((l) => l.id === lotId)
  const unit = lot?.commodity_unit ? ` ${lot.commodity_unit.toUpperCase()}` : ''
  return `${formatQty(avail)}${unit}`
}

const handleSaveDraft = () => {
  submitForm('DRAFT')
}

const handleSaveAndPost = () => {
  confirm.require({
    message: 'Posting this Delivery Note will immediately withdraw stock from inventory. Do you want to proceed?',
    header: 'Confirm Stock Withdrawal',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Save & Post',
      severity: 'success'
    },
    accept: () => {
      submitForm('POSTED')
    }
  })
}
</script>

<template>
  <div class="detail-split-panel">
    <!-- Panel Header -->
    <div class="panel-topbar">
      <div class="breadcrumb-context">
        <span class="muted-crumb">Delivery / Outward</span>
        <span class="slash-crumb">></span>
        <span class="active-crumb">Create Delivery Note</span>
      </div>

      <div class="panel-actions">
        <button class="btn-text" type="button" @click="emit('close')">Cancel</button>
        <button
          class="btn-outlined"
          type="button"
          :disabled="isSubmitting"
          @click="handleSaveDraft"
        >
          Save Draft
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="handleSaveAndPost"
        >
          <FileCheck :size="16" />
          <span>Save & Post</span>
        </button>
      </div>
    </div>

    <!-- Panel Body -->
    <div class="panel-body">
      <!-- Header Grid Inputs -->
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Dispatch Date <span class="req">*</span></label>
          <DatePicker
            v-model="dispatch_date"
            v-bind="dispatchDateProps"
            dateFormat="dd/mm/yy"
            showIcon
            class="w-full"
            :invalid="!!errors.dispatch_date"
          />
          <small v-if="errors.dispatch_date" class="field-error">{{ errors.dispatch_date }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">DN No.</label>
          <InputText
            value="Auto (assigned on save)"
            disabled
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Customer / Party <span class="req">*</span></label>
          <Select
            v-model="party_id"
            v-bind="partyIdProps"
            :options="props.parties"
            optionLabel="name"
            optionValue="id"
            placeholder="Select Party"
            :loading="props.loadingParties"
            class="w-full"
            :invalid="!!errors.party_id"
          />
          <small v-if="errors.party_id" class="field-error">{{ errors.party_id }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">Vehicle No.</label>
          <InputText
            v-model="vehicle_number"
            v-bind="vehicleNoProps"
            placeholder="e.g. GJ 05 AB 1234"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Driver Name</label>
          <InputText
            v-model="driver_name"
            v-bind="driverNameProps"
            placeholder="Driver Name"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Remarks</label>
          <InputText
            v-model="remarks"
            v-bind="remarksProps"
            placeholder="Optional remarks"
            class="w-full"
          />
        </div>
      </div>

      <!-- Line Items Section -->
      <div class="items-section">
        <h4 class="section-subtitle">Delivery Items / Stock Withdrawal</h4>

        <div class="items-table-wrapper">
          <table class="items-table">
            <thead>
              <tr>
                <th width="40">#</th>
                <th>Available Lot <span class="req">*</span></th>
                <th width="150">Available Stock</th>
                <th width="140">Dispatch Qty <span class="req">*</span></th>
                <th width="50"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, idx) in lines" :key="idx">
                <td>{{ idx + 1 }}</td>
                <td>
                  <Select
                    v-model="line.lot_id"
                    :options="lotSelectOptions"
                    optionLabel="label"
                    optionValue="id"
                    placeholder="Select Available Lot"
                    :loading="lotsQuery.isLoading.value"
                    class="w-full input-sm-select"
                  />
                </td>
                <td class="num-align text-muted-val">
                  {{ formatAvailableText(line.lot_id) }}
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    v-model.number="line.qty"
                    class="p-inputtext p-component w-full input-sm num-align"
                    :class="{ 'p-invalid': !!getLineQtyError(idx) }"
                  />
                  <small v-if="getLineQtyError(idx)" class="field-error">{{ getLineQtyError(idx) }}</small>
                </td>
                <td>
                  <button
                    class="icon-btn danger-hover"
                    type="button"
                    @click="removeLineRow(idx)"
                    title="Remove line"
                  >
                    <Trash2 :size="15" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <button class="btn-outlined add-item-btn" type="button" @click="addLineRow">
          <Plus :size="15" />
          <span>Add Line Item</span>
        </button>
      </div>
    </div>

    <!-- Pinned Totals Summary Bar at Bottom -->
    <div class="panel-totals-bar">
      <div class="total-metric highlight-metric">
        <span class="metric-label">Total Dispatch Quantity</span>
        <span class="metric-value">{{ formatQty(totalQty) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-split-panel {
  flex: 1.5;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  position: sticky;
  top: 88px;
  overflow: hidden;
}

.panel-topbar {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-surface);
}

.breadcrumb-context {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}

.muted-crumb {
  color: var(--text-secondary);
  font-weight: 500;
}

.slash-crumb {
  color: var(--text-secondary);
}

.active-crumb {
  color: var(--text-primary);
  font-weight: 700;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
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
  margin-top: 2px;
  display: block;
}

.items-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.items-table-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.items-table th {
  background: var(--bg-page);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.items-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: top;
}

.input-sm {
  font-size: 12px !important;
  padding: 6px 8px !important;
  border-radius: 6px !important;
}

.input-sm-select {
  font-size: 12px !important;
}

.num-align {
  text-align: right;
}

.text-muted-val {
  color: var(--text-secondary);
  font-weight: 600;
  padding-top: 12px;
  font-feature-settings: "tnum";
}

.add-item-btn {
  align-self: flex-start;
  font-size: 12.5px;
  padding: 7px 14px;
}

.panel-totals-bar {
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-sidebar);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 36px;
}

.total-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.metric-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  font-feature-settings: "tnum";
}

.highlight-metric .metric-value {
  color: var(--accent-primary);
  font-size: 20px;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

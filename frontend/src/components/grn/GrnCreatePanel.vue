<script setup lang="ts">
import { computed } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import { Plus, Trash2, FileCheck } from 'lucide-vue-next'
import { formatQty, formatCurrency } from '../../utils/format'
import { useGrnForm } from '../../composables/useGrnForm'
import type { PartyOutput } from '../../api/party'
import type { CommodityOutput } from '../../api/commodity'

interface Props {
  facilityId: number | undefined
  parties: PartyOutput[]
  commodities: CommodityOutput[]
  loadingParties?: boolean
  loadingCommodities?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  created: [grnNumber: string, status: string]
}>()

const chamberSelectOptions = [
  { label: 'Chamber A', value: 'Chamber A' },
  { label: 'Chamber B', value: 'Chamber B' },
  { label: 'Chamber C', value: 'Chamber C' }
]

const facilityIdRef = computed(() => props.facilityId)

const {
  party_id,
  partyIdProps,
  receipt_date,
  receiptDateProps,
  vehicle_number,
  vehicleNoProps,
  driver_name,
  driverNameProps,
  remarks,
  remarksProps,
  items,
  errors,
  addItemRow,
  removeItemRow,
  totalNetWeight,
  totalAmount,
  submitForm,
  isSubmitting
} = useGrnForm(facilityIdRef, (grnNumber, status) => emit('created', grnNumber, status))
</script>

<template>
  <div class="detail-split-panel">
    <!-- Panel Header -->
    <div class="panel-topbar">
      <div class="breadcrumb-context">
        <span class="muted-crumb">GRN / Inward</span>
        <span class="slash-crumb">></span>
        <span class="active-crumb">Create GRN</span>
      </div>

      <div class="panel-actions">
        <button class="btn-text" type="button" @click="emit('close')">Cancel</button>
        <button
          class="btn-outlined"
          type="button"
          :disabled="isSubmitting"
          @click="submitForm('DRAFT')"
        >
          Save Draft
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="submitForm('POSTED')"
        >
          <FileCheck :size="16" />
          <span>Save GRN</span>
        </button>
      </div>
    </div>

    <!-- Panel Form Scrollable Body -->
    <div class="panel-body">
      <!-- Header Grid Inputs -->
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">GRN Date <span class="req">*</span></label>
          <DatePicker
            v-model="receipt_date"
            v-bind="receiptDateProps"
            dateFormat="dd/mm/yy"
            showIcon
            class="w-full"
            :invalid="!!errors.receipt_date"
          />
          <small v-if="errors.receipt_date" class="field-error">{{ errors.receipt_date }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">GRN No.</label>
          <InputText
            value="Auto (generated on save)"
            disabled
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Supplier / Party <span class="req">*</span></label>
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
          <label class="form-label">Driver Name</label>
          <InputText
            v-model="driver_name"
            v-bind="driverNameProps"
            placeholder="Driver Name"
            class="w-full"
          />
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
          <label class="form-label">Remarks</label>
          <InputText
            v-model="remarks"
            v-bind="remarksProps"
            placeholder="Optional remarks"
            class="w-full"
          />
        </div>
      </div>

      <!-- Items Editable Section -->
      <div class="items-section">
        <h4 class="section-subtitle">Items / Products Inward</h4>

        <div class="items-table-wrapper">
          <table class="items-table">
            <thead>
              <tr>
                <th width="40">#</th>
                <th>Commodity / Product <span class="req">*</span></th>
                <th width="140">Chamber</th>
                <th width="100">Qty (Units) <span class="req">*</span></th>
                <th width="120">Unit Wt (MT)</th>
                <th width="120">Rate / Unit (₹)</th>
                <th width="110">Amount (₹)</th>
                <th width="50"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in items" :key="idx">
                <td>{{ idx + 1 }}</td>
                <td>
                  <Select
                    v-model="item.commodity_id"
                    :options="props.commodities"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Select Item"
                    :loading="props.loadingCommodities"
                    class="w-full input-sm-select"
                  />
                </td>
                <td>
                  <Select
                    v-model="item.chamber"
                    :options="chamberSelectOptions"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full input-sm-select"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    v-model.number="item.initial_qty"
                    class="p-inputtext p-component w-full input-sm num-align"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    min="0"
                    v-model.number="item.unit_weight"
                    class="p-inputtext p-component w-full input-sm num-align"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    v-model.number="item.rent_rate_per_unit"
                    class="p-inputtext p-component w-full input-sm num-align"
                  />
                </td>
                <td class="amount-cell">
                  {{ formatCurrency((item.initial_qty || 0) * (item.rent_rate_per_unit || 0)) }}
                </td>
                <td>
                  <button
                    class="icon-btn danger-hover"
                    type="button"
                    @click="removeItemRow(idx)"
                    title="Remove item"
                  >
                    <Trash2 :size="15" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <button class="btn-outlined add-item-btn" type="button" @click="addItemRow">
          <Plus :size="15" />
          <span>Add Item</span>
        </button>
      </div>
    </div>

    <!-- Pinned Totals Summary Bar at Bottom -->
    <div class="panel-totals-bar">
      <div class="total-metric">
        <span class="metric-label">Total Net Weight (MT)</span>
        <span class="metric-value">{{ formatQty(totalNetWeight) }}</span>
      </div>

      <div class="total-metric highlight-metric">
        <span class="metric-label">Total Amount (₹)</span>
        <span class="metric-value">{{ formatCurrency(totalAmount) }}</span>
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

.amount-cell {
  font-weight: 700;
  color: var(--text-primary);
  text-align: right;
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

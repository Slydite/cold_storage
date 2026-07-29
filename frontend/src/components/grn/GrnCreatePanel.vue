<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import DatePicker from 'primevue/datepicker'
import { Plus, Trash2, FileCheck } from 'lucide-vue-next'
import { formatQty, formatCurrency } from '../../utils/format'
import { useGrnForm } from '../../composables/useGrnForm'
import { useChamberList, useFloorList, useBlockList } from '../../composables/useLocations'
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

const { t } = useI18n()
const facilityIdRef = computed(() => props.facilityId)

// Fetch locations for cascading dropdowns
const { data: chambers } = useChamberList({ facilityId: facilityIdRef })
const { data: floors } = useFloorList({ facilityId: facilityIdRef })
const { data: blocks } = useBlockList({ facilityId: facilityIdRef })

const chamberOptions = computed(() => {
  if (!chambers.value) return []
  return chambers.value.map((c) => ({ label: c.name, value: c.id }))
})

const getFloorsForChamber = (chamberId: number | null | undefined) => {
  if (!floors.value || !chamberId) return []
  return floors.value.filter((f) => f.chamber_id === chamberId).map((f) => ({ label: f.name, value: f.id }))
}

const getBlocksForFloor = (floorId: number | null | undefined, chamberId: number | null | undefined) => {
  if (!blocks.value || !floorId) return []
  let res = blocks.value
  if (chamberId) res = res.filter((b) => b.chamber_id === chamberId)
  res = res.filter((b) => b.floor_id === floorId)
  return res.map((b) => ({ label: b.name, value: b.id }))
}

const chargeModeOptions = computed(() => [
  { label: t('chargeMode.FLAT'), value: 'FLAT' },
  { label: t('chargeMode.PER_UNIT'), value: 'PER_UNIT' }
])

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
  loading_charge_mode,
  loading_charge,
  loadingChargeProps,
  loading_unloading_rate_per_bag,
  loadingRateProps,
  items,
  errors,
  addItemRow,
  removeItemRow,
  totalNetWeight,
  totalQty,
  computedReceivingChargeEstimate,
  submitForm,
  isSubmitting
} = useGrnForm(facilityIdRef, (grnNumber, status) => emit('created', grnNumber, status))

const onCommodityChange = (itemIdx: number, commId: number | null) => {
  if (!commId) return
  const comm = props.commodities.find((c) => c.id === commId)
  const item = items.value[itemIdx]
  if (item && comm && comm.unit) {
    item.unit = comm.unit
  }
}

// Clear the child selections when a parent location changes. Without this the
// stale floor/block ids survive - the dropdowns re-filter and *look* empty, but
// the old ids are still submitted, and the backend rejects the GRN with
// "Floor with ID x does not belong to chamber y". That 400 is what the owner hit.
const onChamberChange = (itemIdx: number) => {
  const item = items.value[itemIdx]
  if (!item) return
  item.floor_id = null
  item.block_id = null
}

const onFloorChange = (itemIdx: number) => {
  const item = items.value[itemIdx]
  if (!item) return
  item.block_id = null
}
</script>

<template>
  <div class="detail-split-panel">
    <!-- Panel Header -->
    <div class="panel-topbar">
      <div class="breadcrumb-context">
        <span class="muted-crumb">{{ t('nav.grn') }}</span>
        <span class="slash-crumb">></span>
        <span class="active-crumb">{{ t('grn.createNewGrn') }}</span>
      </div>

      <div class="panel-actions">
        <button class="btn-text" type="button" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button
          class="btn-outlined"
          type="button"
          :disabled="isSubmitting"
          @click="submitForm('DRAFT')"
        >
          {{ t('common.saveDraft') }}
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="submitForm('POSTED')"
        >
          <FileCheck :size="16" />
          <span>{{ t('grn.saveGrn') }}</span>
        </button>
      </div>
    </div>

    <!-- Panel Form Scrollable Body -->
    <div class="panel-body">
      <!-- Header Grid Inputs -->
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">{{ t('common.date') }} <span class="req">*</span></label>
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
          <label class="form-label">{{ t('grn.grnNumber') }}</label>
          <InputText
            :value="t('grn.autoGenerated')"
            disabled
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('grn.supplierParty') }} <span class="req">*</span></label>
          <Select
            v-model="party_id"
            v-bind="partyIdProps"
            :options="props.parties"
            optionLabel="name"
            optionValue="id"
            :placeholder="t('parties.title')"
            :loading="props.loadingParties"
            class="w-full"
            :invalid="!!errors.party_id"
          />
          <small v-if="errors.party_id" class="field-error">{{ errors.party_id }}</small>
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('grn.driverName') }}</label>
          <InputText
            v-model="driver_name"
            v-bind="driverNameProps"
            :placeholder="t('grn.driverName')"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('grn.vehicle') }}</label>
          <InputText
            v-model="vehicle_number"
            v-bind="vehicleNoProps"
            placeholder="e.g. GJ 05 AB 1234"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label class="form-label">{{ t('common.remarks') }}</label>
          <InputText
            v-model="remarks"
            v-bind="remarksProps"
            :placeholder="t('common.remarks')"
            class="w-full"
          />
        </div>
      </div>

      <!-- Receiving Charge Section -->
      <div class="charge-section-card">
        <div class="charge-header">
          <h4 class="section-subtitle">{{ t('grn.loadingUnloadingCharge') }}</h4>
          <span class="charge-help">{{ t('grn.loadingUnloadingHelp') }}</span>
        </div>

        <div class="charge-controls">
          <div class="form-group">
            <label class="form-label">{{ t('grn.chargeMode') }}</label>
            <SelectButton
              v-model="loading_charge_mode"
              :options="chargeModeOptions"
              optionLabel="label"
              optionValue="value"
              :allowEmpty="false"
              class="w-full"
            />
          </div>

          <div v-if="loading_charge_mode === 'FLAT'" class="form-group">
            <label class="form-label">{{ t('grn.flatLoadingUnloadingCharge') }}</label>
            <InputText
              v-model="loading_charge"
              v-bind="loadingChargeProps"
              placeholder="e.g. 500.00"
              class="w-full"
            />
          </div>

          <div v-else class="form-group">
            <label class="form-label">{{ t('grn.loadingUnloadingRatePerUnit') }}</label>
            <InputText
              v-model="loading_unloading_rate_per_bag"
              v-bind="loadingRateProps"
              placeholder="e.g. 5.00"
              class="w-full"
            />
          </div>

          <div class="form-group est-display">
            <label class="form-label">{{ t('grn.estimatedLoadingUnloadingCharge') }}</label>
            <span class="est-value">{{ formatCurrency(computedReceivingChargeEstimate) }}</span>
          </div>
        </div>
      </div>

      <!-- Items Editable Section -->
      <div class="items-section">
        <h4 class="section-subtitle">{{ t('grn.itemsInward') }}</h4>

        <div class="items-table-wrapper hide-on-mobile">
          <table class="items-table">
            <colgroup>
              <col style="width: 35px;" />
              <col style="width: 170px;" />
              <col style="width: 115px;" />
              <col style="width: 130px;" />
              <col style="width: 120px;" />
              <col style="width: 120px;" />
              <col style="width: 95px;" />
              <col style="width: 95px;" />
              <col style="width: 95px;" />
              <col style="width: 115px;" />
              <col style="width: 48px;" />
            </colgroup>
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('grn.commodityProduct') }} <span class="req">*</span></th>
                <th>{{ t('inventory.lotNo') }}</th>
                <th>{{ t('grn.chamber') }}</th>
                <th>{{ t('grn.floor') }}</th>
                <th>{{ t('grn.block') }}</th>
                <th>{{ t('common.quantity') }} <span class="req">*</span></th>
                <th>{{ t('common.unit') }}</th>
                <th>{{ t('common.weight') }} (MT)</th>
                <th>{{ t('common.rate') }} / unit / month (₹)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in items" :key="idx">
                <td>{{ idx + 1 }}</td>
                <td>
                  <Select
                    v-model="item.commodity_id"
                    @change="onCommodityChange(idx, item.commodity_id)"
                    :options="props.commodities"
                    optionLabel="name"
                    optionValue="id"
                    :placeholder="t('common.select')"
                    :loading="props.loadingCommodities"
                    class="w-full input-sm-select"
                  />
                </td>
                <td>
                  <div class="lot-no-cell">
                    <span v-if="item.lot_number_loading" class="lot-loading">
                      <i class="pi pi-spin pi-spinner text-muted mr-1"></i>
                      <span>{{ t('grn.reserving') }}</span>
                    </span>
                    <span v-else class="lot-code">
                      {{ item.lot_number || '—' }}
                    </span>
                  </div>
                </td>
                <td>
                  <Select
                    v-model="item.chamber_id"
                    @update:modelValue="onChamberChange(idx)"
                    :options="chamberOptions"
                    optionLabel="label"
                    optionValue="value"
                    :placeholder="t('grn.chamber')"
                    showClear
                    class="w-full input-sm-select"
                  />
                </td>
                <td>
                  <Select
                    v-model="item.floor_id"
                    @update:modelValue="onFloorChange(idx)"
                    :options="getFloorsForChamber(item.chamber_id)"
                    optionLabel="label"
                    optionValue="value"
                    :placeholder="!item.chamber_id ? t('grn.selectChamberFirst') : t('grn.floor')"
                    :disabled="!item.chamber_id"
                    showClear
                    class="w-full input-sm-select"
                  />
                </td>
                <td>
                  <Select
                    v-model="item.block_id"
                    :options="getBlocksForFloor(item.floor_id, item.chamber_id)"
                    optionLabel="label"
                    optionValue="value"
                    :placeholder="!item.floor_id ? t('grn.selectFloorFirst') : t('grn.block')"
                    :disabled="!item.floor_id"
                    showClear
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
                    type="text"
                    v-model="item.unit"
                    placeholder="Bags"
                    class="p-inputtext p-component w-full input-sm"
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
                    placeholder="Rate"
                    class="p-inputtext p-component w-full input-sm num-align"
                  />
                </td>
                <td>
                  <button
                    class="icon-btn danger-hover"
                    type="button"
                    @click="removeItemRow(idx)"
                    :title="t('common.delete')"
                  >
                    <Trash2 :size="15" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile Card Layout -->
        <div class="mobile-items-cards show-on-mobile">
          <div class="mobile-item-card" v-for="(item, idx) in items" :key="idx">
            <div class="card-header">
              <div class="card-header-left">
                <span class="card-index">#{{ idx + 1 }}</span>
                <div class="lot-no-cell">
                  <span class="card-label-lot">{{ t('inventory.lotNo') }}:</span>
                  <span v-if="item.lot_number_loading" class="lot-loading">
                    <i class="pi pi-spin pi-spinner text-muted mr-1"></i>
                    <span>{{ t('grn.reserving') }}</span>
                  </span>
                  <span v-else class="lot-code">
                    {{ item.lot_number || '—' }}
                  </span>
                </div>
              </div>
              <button
                class="icon-btn danger-hover"
                type="button"
                @click="removeItemRow(idx)"
                :title="t('common.delete')"
              >
                <Trash2 :size="15" />
              </button>
            </div>

            <div class="card-body-grid">
              <div class="card-field full-width">
                <label class="card-field-label">{{ t('grn.commodityProduct') }} <span class="req">*</span></label>
                <Select
                  v-model="item.commodity_id"
                  @change="onCommodityChange(idx, item.commodity_id)"
                  :options="props.commodities"
                  optionLabel="name"
                  optionValue="id"
                  :placeholder="t('common.select')"
                  :loading="props.loadingCommodities"
                  class="w-full input-sm-select"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('grn.chamber') }}</label>
                <Select
                  v-model="item.chamber_id"
                  @update:modelValue="onChamberChange(idx)"
                  :options="chamberOptions"
                  optionLabel="label"
                  optionValue="value"
                  :placeholder="t('grn.chamber')"
                  showClear
                  class="w-full input-sm-select"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('grn.floor') }}</label>
                <Select
                  v-model="item.floor_id"
                  @update:modelValue="onFloorChange(idx)"
                  :options="getFloorsForChamber(item.chamber_id)"
                  optionLabel="label"
                  optionValue="value"
                  :placeholder="!item.chamber_id ? t('grn.selectChamberFirst') : t('grn.floor')"
                  :disabled="!item.chamber_id"
                  showClear
                  class="w-full input-sm-select"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('grn.block') }}</label>
                <Select
                  v-model="item.block_id"
                  :options="getBlocksForFloor(item.floor_id, item.chamber_id)"
                  optionLabel="label"
                  optionValue="value"
                  :placeholder="!item.floor_id ? t('grn.selectFloorFirst') : t('grn.block')"
                  :disabled="!item.floor_id"
                  showClear
                  class="w-full input-sm-select"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('common.quantity') }} <span class="req">*</span></label>
                <input
                  type="number"
                  min="1"
                  v-model.number="item.initial_qty"
                  class="p-inputtext p-component w-full input-sm"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('common.unit') }}</label>
                <input
                  type="text"
                  v-model="item.unit"
                  placeholder="Bags"
                  class="p-inputtext p-component w-full input-sm"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('common.weight') }} (MT)</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  v-model.number="item.unit_weight"
                  class="p-inputtext p-component w-full input-sm"
                />
              </div>

              <div class="card-field">
                <label class="card-field-label">{{ t('common.rate') }} / unit / month (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model.number="item.rent_rate_per_unit"
                  placeholder="Rate"
                  class="p-inputtext p-component w-full input-sm"
                />
              </div>
            </div>
          </div>
        </div>

        <button class="btn-outlined add-item-btn" type="button" @click="addItemRow">
          <Plus :size="15" />
          <span>{{ t('grn.addItem') }}</span>
        </button>
      </div>
    </div>

    <!-- Pinned Totals Summary Bar at Bottom -->
    <div class="panel-totals-bar">
      <div class="total-metric">
        <span class="metric-label">{{ t('grn.totalQtyUnits') }}</span>
        <span class="metric-value">{{ formatQty(totalQty, 0) }}</span>
      </div>

      <div class="total-metric highlight-metric">
        <span class="metric-label">{{ t('grn.totalNetWeightMt') }}</span>
        <span class="metric-value">{{ formatQty(totalNetWeight) }}</span>
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
  height: calc(100dvh - 120px);
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
  gap: 20px;
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
.charge-section-card {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.charge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.charge-help {
  font-size: 12px;
  color: var(--text-secondary);
}
.charge-controls {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  gap: 16px;
  align-items: end;
}
.est-display {
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 8px 12px;
}
.est-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent-primary);
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
  overflow-x: auto;
}
.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  min-width: 1150px;
  table-layout: fixed;
}
.items-table th {
  background: var(--bg-page);
  padding: 10px 8px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
  white-space: normal;
  word-break: break-word;
  line-height: 1.2;
  max-height: 2.4em;
  overflow: hidden;
  text-overflow: ellipsis;
}
.items-table td {
  padding: 6px 8px;
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
.lot-no-cell {
  display: flex;
  align-items: center;
  font-family: monospace;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
}
.lot-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
  font-family: var(--font-family);
}
.lot-code {
  background: var(--bg-page);
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px dashed var(--border-subtle);
  font-feature-settings: "tnum";
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
@media (min-width: 769px) {
  .show-on-mobile {
    display: none !important;
  }
}
@media (max-width: 900px) {
  .detail-split-panel {
    position: fixed;
    inset: 0;
    z-index: 1000;
    width: 100%;
    max-width: none;
    height: 100vh;
    height: 100dvh;
    border: none;
    border-radius: 0;
  }
}
@media (max-width: 768px) {
  .hide-on-mobile {
    display: none !important;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .charge-controls {
    grid-template-columns: 1fr;
  }
  .panel-topbar {
    flex-wrap: wrap;
    gap: 12px;
  }
  .panel-actions {
    width: 100%;
    justify-content: flex-end;
  }
  .panel-totals-bar {
    justify-content: space-between;
    gap: 16px;
  }
  .mobile-items-cards {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .mobile-item-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 10px;
  }
  .card-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
    overflow: hidden;
  }
  .card-index {
    font-weight: 700;
    font-size: 13px;
    color: var(--accent-primary);
    flex-shrink: 0;
  }
  .card-label-lot {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-right: 4px;
  }
  .card-body-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .card-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .card-field.full-width {
    grid-column: span 2;
  }
  .card-field-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
  }
}
</style>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { Trash2, Plus, SlidersHorizontal, ArrowUpRight, ArrowDownRight } from 'lucide-vue-next'
import { formatQty, formatCurrency } from '../../utils/format'
import { addLotRateChange, deleteLotRateChange } from '../../api/lot'
import type { LotOutput, LotRateChange } from '../../api/generated/types.gen'
import StockAdjustmentDialog from './StockAdjustmentDialog.vue'

const props = defineProps<{
  visible: boolean
  lot: LotOutput | null
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  refresh: []
  'view-grn': [grnId: number]
}>()

const { t } = useI18n()
const toast = useToast()

const showAdjustStock = ref(false)
const showAddRateChange = ref(false)
const isSubmittingRate = ref(false)
const rateChangeToDelete = ref<LotRateChange | null>(null)
const showDeleteConfirm = ref(false)
const deletingRate = ref(false)

// Sorting and merging rate changes
const rateHistory = computed(() => {
  if (!props.lot) return []
  const initial = {
    id: 0,
    lot_id: props.lot.id,
    rate_per_unit: props.lot.rent_rate_per_unit || '0.00',
    effective_from: props.lot.inward_date,
    note: t('inventory.intakeRate'),
    entered_by_username: 'system',
    is_initial: true
  }

  const changes = (props.lot.rate_changes || []).map((rc) => ({
    id: rc.id,
    lot_id: rc.lot_id,
    rate_per_unit: rc.rate_per_unit,
    effective_from: rc.effective_from,
    note: rc.note || '—',
    entered_by_username: rc.entered_by_username || '—',
    is_initial: false
  }))

  const sortedChanges = changes.sort(
    (a, b) => new Date(a.effective_from).getTime() - new Date(b.effective_from).getTime()
  )

  return [initial, ...sortedChanges]
})

const sortedAdjustments = computed(() => {
  if (!props.lot?.adjustments) return []
  return [...props.lot.adjustments].sort(
    (a, b) => new Date(b.adjustment_date).getTime() - new Date(a.adjustment_date).getTime()
  )
})

// Add Rate Change validation schema
const rateValidationSchema = computed(() => {
  return toTypedSchema(
    z.object({
      rate_per_unit: z
        .string({ message: t('validation.rateRequired') })
        .refine((v) => v !== '' && !isNaN(Number(v)) && Number(v) >= 0, {
          message: t('validation.rateNotNegative')
        }),
      effective_from: z.date({ message: t('validation.effectiveDateRequired') }),
      note: z.string().optional()
    })
  )
})

const { handleSubmit: handleRateSubmit, errors: rateErrors, defineField: defineRateField, resetForm: resetRateForm } = useForm({
  validationSchema: rateValidationSchema,
  initialValues: {
    rate_per_unit: '',
    effective_from: new Date(),
    note: ''
  }
})

const [rate_per_unit, ratePerUnitProps] = defineRateField('rate_per_unit')
const [effective_from, effectiveFromProps] = defineRateField('effective_from')
const [rateNote, rateNoteProps] = defineRateField('note')

watch(
  () => showAddRateChange.value,
  (newVal) => {
    if (newVal) {
      resetRateForm({
        values: {
          rate_per_unit: '',
          effective_from: new Date(),
          note: ''
        }
      })
    }
  }
)

const handleClose = () => {
  emit('update:visible', false)
}

const onRateSubmit = handleRateSubmit(async (formValues) => {
  if (!props.lot) return
  isSubmittingRate.value = true
  try {
    const yyyy = formValues.effective_from.getFullYear()
    const mm = String(formValues.effective_from.getMonth() + 1).padStart(2, '0')
    const dd = String(formValues.effective_from.getDate()).padStart(2, '0')
    const formattedDate = `${yyyy}-${mm}-${dd}`

    await addLotRateChange(props.lot.id, {
      rate_per_unit: formValues.rate_per_unit,
      effective_from: formattedDate,
      note: formValues.note || undefined
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('inventory.rateSuccess'),
      life: 5000
    })
    showAddRateChange.value = false
    emit('refresh')
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('inventory.rateFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 7000
    })
  } finally {
    isSubmittingRate.value = false
  }
})

const confirmDeleteRate = (rc: LotRateChange) => {
  rateChangeToDelete.value = rc
  showDeleteConfirm.value = true
}

const handleDeleteRate = async () => {
  if (!props.lot || !rateChangeToDelete.value) return
  deletingRate.value = true
  try {
    await deleteLotRateChange(props.lot.id, rateChangeToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('inventory.deleteRateChangeSuccess'),
      life: 5000
    })
    showDeleteConfirm.value = false
    rateChangeToDelete.value = null
    emit('refresh')
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('inventory.deleteRateChangeFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 7000
    })
  } finally {
    deletingRate.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="props.lot ? `${t('inventory.lots')} - ${props.lot.lot_number}` : t('common.details')"
    :style="{ width: '850px', maxWidth: '95vw' }"
    @hide="handleClose"
  >
    <div v-if="props.lot" class="lot-detail-body">
      <!-- Summary Info Card -->
      <div class="info-card">
        <div class="info-item">
          <span class="info-label">{{ t('inventory.lotNo') }}</span>
          <span class="info-val code-link doc-number">{{ props.lot.lot_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('grn.grnNumber') }}</span>
          <span class="info-val code-link clickable doc-number" @click="emit('view-grn', props.lot.grn_id)">{{ props.lot.grn_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('inventory.party') }}</span>
          <span class="info-val party-name">{{ props.lot.party_name }} ({{ props.lot.party_code }})</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('inventory.itemProduct') }}</span>
          <span class="info-val">{{ props.lot.commodity_name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('inventory.location') }}</span>
          <span class="info-val">{{ props.lot.location_display || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('inventory.inDate') }}</span>
          <span class="info-val">{{ props.lot.inward_date }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('inventory.inQty') }}</span>
          <span class="info-val num-val">{{ formatQty(props.lot.initial_qty) }}</span>
        </div>
        <div class="info-item highlight-qty">
          <span class="info-label">{{ t('inventory.remainingQty') }}</span>
          <span class="info-val num-val total-val">{{ formatQty(props.lot.remaining_qty) }}</span>
        </div>
        <div class="info-item highlight-rate">
          <span class="info-label">{{ t('common.rate') }}</span>
          <span class="info-val num-val rate-val">
            {{ props.lot.rent_rate_per_unit ? formatCurrency(Number(props.lot.rent_rate_per_unit)) : '—' }} / {{ t('common.unit').toLowerCase() }}
          </span>
        </div>
      </div>

      <!-- Action Buttons Row -->
      <div class="action-buttons-row">
        <button class="btn-outlined" type="button" @click="showAdjustStock = true">
          <SlidersHorizontal :size="15" />
          <span>{{ t('inventory.adjustStock') }}</span>
        </button>
        <button class="btn-primary" type="button" @click="showAddRateChange = true">
          <Plus :size="15" />
          <span>{{ t('inventory.addRateChange') }}</span>
        </button>
      </div>

      <!-- Rate History Section -->
      <div class="history-section">
        <h4 class="section-subtitle">{{ t('inventory.rateHistoryTitle') }}</h4>
        <div class="table-container">
          <DataTable :value="rateHistory" size="small" stripedRows responsiveLayout="scroll">
            <Column style="width: 70px" :header="t('common.actions')">
              <template #body="{ data }">
                <button
                  v-if="!data.is_initial"
                  class="btn-trash icon-btn"
                  type="button"
                  :title="t('inventory.deleteRateChangeConfirmHeader')"
                  @click="confirmDeleteRate(data)"
                >
                  <Trash2 :size="14" />
                </button>
                <span v-else class="system-badge">{{ t('common.initial') }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.effectiveFrom')">
              <template #body="{ data }">
                <span>{{ data.effective_from }}</span>
              </template>
            </Column>
            <Column :header="t('common.rate')">
              <template #body="{ data }">
                <strong class="num-val">
                  {{ formatCurrency(Number(data.rate_per_unit)) }}
                </strong>
              </template>
            </Column>
            <Column :header="t('inventory.adjustmentNote')">
              <template #body="{ data }">
                <span>{{ data.note }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.adjustedBy')">
              <template #body="{ data }">
                <span class="username-val">{{ data.entered_by_username }}</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <!-- Adjustment History Section -->
      <div class="history-section">
        <h4 class="section-subtitle">{{ t('inventory.historyTitle') }}</h4>
        <div class="table-container">
          <DataTable :value="sortedAdjustments" size="small" stripedRows responsiveLayout="scroll" paginator :rows="5">
            <Column :header="t('inventory.date')">
              <template #body="{ data }">
                <span>{{ data.adjustment_date }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.adjustmentReason')">
              <template #body="{ data }">
                <span class="status-pill warning">{{ t(`inventory.reasonEnum.${data.reason}`) }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.beforeAfter')">
              <template #body="{ data }">
                <span class="num-val">{{ formatQty(data.qty_before) }}</span>
                <span class="arrow-indicator">➔</span>
                <span class="num-val text-bold">{{ formatQty(data.qty_after) }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.deltaQty')">
              <template #body="{ data }">
                <div class="flex items-center gap-1">
                  <ArrowUpRight v-if="data.qty_delta > 0" :size="14" class="text-success" />
                  <ArrowDownRight v-else-if="data.qty_delta < 0" :size="14" class="text-danger" />
                  <span
                    class="num-val"
                    :class="{ 'text-success': data.qty_delta > 0, 'text-danger': data.qty_delta < 0 }"
                  >
                    {{ data.qty_delta > 0 ? '+' : '' }}{{ formatQty(data.qty_delta) }}
                  </span>
                </div>
              </template>
            </Column>
            <Column :header="t('inventory.adjustmentNote')">
              <template #body="{ data }">
                <span>{{ data.note || '—' }}</span>
              </template>
            </Column>
            <Column :header="t('inventory.adjustedBy')">
              <template #body="{ data }">
                <span class="username-val">{{ data.adjusted_by_username || '—' }}</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Add Rate Change Dialog (Nested) -->
    <Dialog
      v-model:visible="showAddRateChange"
      modal
      :header="t('inventory.addRateChange')"
      :style="{ width: '420px', maxWidth: '90vw' }"
    >
      <form @submit="onRateSubmit" class="dialog-form-body">
        <p class="form-help-text">
          Make sure to select the correct date when the rate <strong>takes effect</strong>. The rate change will be applied from this date onward.
        </p>

        <!-- New Rate Field -->
        <div class="form-group">
          <label class="form-label">{{ t('inventory.newRate') }} <span class="req">*</span></label>
          <InputText
            v-model="rate_per_unit"
            v-bind="ratePerUnitProps"
            type="text"
            class="w-full"
            placeholder="0.00"
            :invalid="!!rateErrors.rate_per_unit"
          />
          <small v-if="rateErrors.rate_per_unit" class="field-error">{{ rateErrors.rate_per_unit }}</small>
        </div>

        <!-- Effective Date Field -->
        <div class="form-group">
          <label class="form-label">{{ t('inventory.effectiveFrom') }} <span class="req">*</span></label>
          <DatePicker
            v-model="effective_from"
            v-bind="effectiveFromProps"
            dateFormat="dd/mm/yy"
            showIcon
            class="w-full"
            :invalid="!!rateErrors.effective_from"
          />
          <small v-if="rateErrors.effective_from" class="field-error">{{ rateErrors.effective_from }}</small>
        </div>

        <!-- Note Field -->
        <div class="form-group">
          <label class="form-label">{{ t('inventory.rateNote') }}</label>
          <InputText
            v-model="rateNote"
            v-bind="rateNoteProps"
            type="text"
            class="w-full"
            :invalid="!!rateErrors.note"
          />
          <small v-if="rateErrors.note" class="field-error">{{ rateErrors.note }}</small>
        </div>

        <div class="dialog-actions-footer">
          <button class="btn-outlined" type="button" @click="showAddRateChange = false" :disabled="isSubmittingRate">
            {{ t('common.cancel') }}
          </button>
          <button class="btn-primary" type="submit" :disabled="isSubmittingRate">
            <i v-if="isSubmittingRate" class="pi pi-spin pi-spinner mr-1"></i>
            <span>{{ t('common.save') }}</span>
          </button>
        </div>
      </form>
    </Dialog>

    <!-- Delete Rate Change Confirmation -->
    <Dialog
      v-model:visible="showDeleteConfirm"
      modal
      :header="t('inventory.deleteRateChangeConfirmHeader')"
      :style="{ width: '400px', maxWidth: '90vw' }"
    >
      <div class="dialog-form-body">
        <p>{{ t('inventory.deleteRateChangeConfirmMessage') }}</p>
        <div class="dialog-actions-footer">
          <button class="btn-outlined" type="button" @click="showDeleteConfirm = false" :disabled="deletingRate">
            {{ t('common.cancel') }}
          </button>
          <button class="btn-danger btn-primary" type="button" @click="handleDeleteRate" :disabled="deletingRate">
            <i v-if="deletingRate" class="pi pi-spin pi-spinner mr-1"></i>
            <span>{{ t('common.delete') }}</span>
          </button>
        </div>
      </div>
    </Dialog>

    <!-- Stock Adjustment Dialog -->
    <StockAdjustmentDialog
      v-model:visible="showAdjustStock"
      :lot="props.lot"
      @success="emit('refresh')"
    />
  </Dialog>
</template>

<style scoped>
.lot-detail-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 8px;
}

.info-card {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.info-val {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.total-val {
  color: var(--accent-primary);
  font-size: 16px;
}

.rate-val {
  color: var(--accent-primary);
  font-size: 15px;
}

.highlight-qty,
.highlight-rate {
  background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.04);
  border-radius: 6px;
  padding: 2px 6px;
}

.action-buttons-row {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 4px;
}

.history-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.table-container {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-surface);
}

.system-badge {
  font-size: 11px;
  background: var(--bg-surface-active);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.arrow-indicator {
  margin: 0 8px;
  color: var(--text-secondary);
}

.text-bold {
  font-weight: 700;
}

.dialog-form-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.form-help-text {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: 4px;
}

.req {
  color: var(--status-danger-color, #ef4444);
}

.field-error {
  color: var(--status-danger-color, #ef4444);
  font-size: 12px;
  margin-top: 2px;
}

.dialog-actions-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.btn-trash {
  color: var(--status-danger-color, #ef4444);
}

.btn-trash:hover {
  background: rgba(239, 68, 68, 0.08);
}

.btn-danger {
  background: var(--status-danger-color, #ef4444);
  border-color: var(--status-danger-color, #ef4444);
  color: #white;
}

.btn-danger:hover {
  background: #dc2626;
}

.mr-1 {
  margin-right: 4px;
}

.text-success {
  color: #22c55e;
}

.text-danger {
  color: #ef4444;
}

.username-val {
  font-family: monospace;
  font-weight: 600;
}

@media (max-width: 640px) {
  .info-card {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { bulkRateChangeLots } from '../../api/lot'
import type { PartyOutput } from '../../api/generated/types.gen'

const props = defineProps<{
  visible: boolean
  facilityId: number | undefined
  parties: PartyOutput[]
  commodities: { label: string; value: number }[]
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: []
}>()

const { t } = useI18n()
const toast = useToast()
const isSubmitting = ref(false)

// State for showing results
const results = ref<{
  applied_count: number
  skipped_count: number
  skipped_details: Array<{ lot_id: number; lot_number: string; reason: string }>
} | null>(null)

const validationSchema = computed(() => {
  return toTypedSchema(
    z.object({
      rate_per_unit: z
        .string({ message: t('validation.rateRequired') })
        .refine((v) => v !== '' && !isNaN(Number(v)) && Number(v) >= 0, {
          message: t('validation.rateNotNegative')
        }),
      effective_from: z.date({ message: t('validation.effectiveDateRequired') }),
      note: z.string().optional(),
      commodity_id: z.number().nullable().optional(),
      party_id: z.number().nullable().optional()
    })
  )
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema,
  initialValues: {
    rate_per_unit: '',
    effective_from: new Date(),
    note: '',
    commodity_id: null as number | null,
    party_id: null as number | null
  }
})

const [rate_per_unit, ratePerUnitProps] = defineField('rate_per_unit')
const [effective_from, effectiveFromProps] = defineField('effective_from')
const [note, noteProps] = defineField('note')
const [commodity_id, commodityIdProps] = defineField('commodity_id')
const [party_id, partyIdProps] = defineField('party_id')

const partyOptions = computed(() => [
  { label: t('inventory.allParties'), value: null },
  ...props.parties.map((p) => ({ label: `${p.name} (${p.code})`, value: p.id }))
])

const commodityOptions = computed(() => [
  { label: t('inventory.allCommodities'), value: null },
  ...props.commodities
])

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      resetForm({
        values: {
          rate_per_unit: '',
          effective_from: new Date(),
          note: '',
          commodity_id: null,
          party_id: null
        }
      })
      results.value = null
    }
  }
)

const handleClose = () => {
  emit('update:visible', false)
}

const onSubmit = handleSubmit(async (formValues) => {
  if (!props.facilityId) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('errors.facilityIdUnavailable'),
      life: 4000
    })
    return
  }

  isSubmitting.value = true
  try {
    const yyyy = formValues.effective_from.getFullYear()
    const mm = String(formValues.effective_from.getMonth() + 1).padStart(2, '0')
    const dd = String(formValues.effective_from.getDate()).padStart(2, '0')
    const formattedDate = `${yyyy}-${mm}-${dd}`

    const response = await bulkRateChangeLots({
      facility_id: props.facilityId,
      rate_per_unit: formValues.rate_per_unit,
      effective_from: formattedDate,
      note: formValues.note || undefined,
      commodity_id: formValues.commodity_id || undefined,
      party_id: formValues.party_id || undefined
    })

    results.value = response
    emit('success')
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('inventory.rateFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 7000
    })
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="results ? t('inventory.bulkRateChangeResults') : t('inventory.bulkRateChange')"
    :style="{ width: '550px', maxWidth: '90vw' }"
    @hide="handleClose"
  >
    <!-- Results View -->
    <div v-if="results" class="results-container">
      <div class="summary-metrics">
        <div class="metric-card success">
          <span class="metric-label">{{ t('inventory.appliedLotsCount', { count: '' }).replace(': ', '') }}</span>
          <span class="metric-value">{{ results.applied_count }}</span>
        </div>
        <div class="metric-card warning">
          <span class="metric-label">{{ t('inventory.skippedLotsCount', { count: '' }).replace(': ', '') }}</span>
          <span class="metric-value">{{ results.skipped_count }}</span>
        </div>
      </div>

      <div v-if="results.skipped_details && results.skipped_details.length > 0" class="skipped-details-section">
        <h4 class="details-title">{{ t('inventory.skippedReasons') }}</h4>
        <div class="reasons-table-wrapper">
          <DataTable :value="results.skipped_details" size="small" stripedRows responsiveLayout="scroll" paginator :rows="5">
            <Column field="lot_number" :header="t('inventory.lotNo')">
              <template #body="{ data }">
                <span class="code-link">{{ data.lot_number }}</span>
              </template>
            </Column>
            <Column field="reason" :header="t('common.remarks')">
              <template #body="{ data }">
                <span class="text-danger-custom">{{ data.reason }}</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <div class="dialog-actions-footer">
        <button class="btn-primary" type="button" @click="handleClose">
          {{ t('common.close') }}
        </button>
      </div>
    </div>

    <!-- Form View -->
    <form v-else @submit="onSubmit" class="dialog-form-body">
      <p class="form-help-text">
        {{ t('inventory.bulkRateChangeDesc') }}
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
          :invalid="!!errors.rate_per_unit"
        />
        <small v-if="errors.rate_per_unit" class="field-error">{{ errors.rate_per_unit }}</small>
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
          :invalid="!!errors.effective_from"
        />
        <small v-if="errors.effective_from" class="field-error">{{ errors.effective_from }}</small>
      </div>

      <!-- Commodity Filter Field -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.commodityFilter') }}</label>
        <Select
          v-model="commodity_id"
          v-bind="commodityIdProps"
          :options="commodityOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
          :placeholder="t('inventory.allCommodities')"
          :invalid="!!errors.commodity_id"
        />
        <small v-if="errors.commodity_id" class="field-error">{{ errors.commodity_id }}</small>
      </div>

      <!-- Party Filter Field -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.partyFilter') }}</label>
        <Select
          v-model="party_id"
          v-bind="partyIdProps"
          :options="partyOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
          filter
          :placeholder="t('inventory.allParties')"
          :invalid="!!errors.party_id"
        />
        <small v-if="errors.party_id" class="field-error">{{ errors.party_id }}</small>
      </div>

      <!-- Note Field -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.rateNote') }}</label>
        <InputText
          v-model="note"
          v-bind="noteProps"
          type="text"
          class="w-full"
          :invalid="!!errors.note"
        />
        <small v-if="errors.note" class="field-error">{{ errors.note }}</small>
      </div>

      <div class="dialog-actions-footer">
        <button class="btn-outlined" type="button" @click="handleClose" :disabled="isSubmitting">
          {{ t('common.cancel') }}
        </button>
        <button class="btn-primary" type="submit" :disabled="isSubmitting">
          <i v-if="isSubmitting" class="pi pi-spin pi-spinner mr-1"></i>
          <span>{{ t('inventory.applyBulkChange') }}</span>
        </button>
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
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

.mr-1 {
  margin-right: 4px;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 8px;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
}

.metric-card.success {
  background: rgba(34, 197, 94, 0.05);
  border-color: rgba(34, 197, 94, 0.2);
}

.metric-card.warning {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.2);
}

.metric-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
}

.skipped-details-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.details-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.reasons-table-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
}

.text-danger-custom {
  color: var(--status-danger-color, #ef4444);
  font-weight: 500;
}
</style>

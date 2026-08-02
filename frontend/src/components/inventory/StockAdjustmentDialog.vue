<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { adjustLotStock } from '../../api/lot'
import type { LotOutput, ReasonEnum } from '../../api/generated/types.gen'

const props = defineProps<{
  visible: boolean
  lot: LotOutput | null
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: []
}>()

const { t } = useI18n()
const toast = useToast()
const isSubmitting = ref(false)

const reasonOptions = computed(() => [
  { label: t('inventory.reasonEnum.NOT_FOUND'), value: 'NOT_FOUND' },
  { label: t('inventory.reasonEnum.SPOILAGE'), value: 'SPOILAGE' },
  { label: t('inventory.reasonEnum.COUNT_CORRECTION'), value: 'COUNT_CORRECTION' },
  { label: t('inventory.reasonEnum.FOUND_EXTRA'), value: 'FOUND_EXTRA' },
  { label: t('inventory.reasonEnum.MIGRATION_OPENING_BALANCE'), value: 'MIGRATION_OPENING_BALANCE' },
  { label: t('inventory.reasonEnum.OTHER'), value: 'OTHER' }
])

const validationSchema = computed(() => {
  return toTypedSchema(
    z.object({
      counted_qty: z.number({ message: t('validation.required') })
        .min(0, t('validation.countedQtyNotNegative')),
      reason: z.enum(['NOT_FOUND', 'SPOILAGE', 'COUNT_CORRECTION', 'FOUND_EXTRA', 'MIGRATION_OPENING_BALANCE', 'OTHER'], {
        message: t('validation.required')
      }),
      note: z.string().optional(),
      adjustment_date: z.date({ message: t('validation.required') })
    }).superRefine((data, ctx) => {
      if (data.reason === 'OTHER' && (!data.note || data.note.trim() === '')) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('validation.noteRequiredForOther'),
          path: ['note']
        })
      }
    })
  )
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema,
  initialValues: {
    counted_qty: undefined as number | undefined,
    reason: undefined as ReasonEnum | undefined,
    note: '',
    adjustment_date: new Date()
  }
})

const [counted_qty, countedQtyProps] = defineField('counted_qty')
const [reason, reasonProps] = defineField('reason')
const [note, noteProps] = defineField('note')
const [adjustment_date, adjustmentDateProps] = defineField('adjustment_date')

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      resetForm({
        values: {
          counted_qty: props.lot ? props.lot.remaining_qty : undefined,
          reason: undefined,
          note: '',
          adjustment_date: new Date()
        }
      })
    }
  }
)

const delta = computed(() => {
  if (counted_qty.value === undefined || counted_qty.value === null) return 0
  return Number(counted_qty.value) - (props.lot?.remaining_qty || 0)
})

const handleClose = () => {
  emit('update:visible', false)
}

const onSubmit = handleSubmit(async (formValues) => {
  if (!props.lot) return
  isSubmitting.value = true
  try {
    const yyyy = formValues.adjustment_date.getFullYear()
    const mm = String(formValues.adjustment_date.getMonth() + 1).padStart(2, '0')
    const dd = String(formValues.adjustment_date.getDate()).padStart(2, '0')
    const formattedDate = `${yyyy}-${mm}-${dd}`

    await adjustLotStock(props.lot.id, {
      new_qty: formValues.counted_qty,
      reason: formValues.reason,
      note: formValues.note || undefined,
      adjustment_date: formattedDate
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('inventory.adjustSuccess'),
      life: 5000
    })
    emit('success')
    handleClose()
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('inventory.adjustFailed'),
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
    :header="props.lot ? t('inventory.adjustStockDialog', { number: props.lot.lot_number }) : t('inventory.adjustStock')"
    :style="{ width: '500px', maxWidth: '90vw' }"
    @hide="handleClose"
  >
    <form @submit="onSubmit" class="dialog-form-body">
      <div v-if="props.lot" class="lot-brief-info">
        <div class="brief-item">
          <span class="brief-label">{{ t('inventory.itemProduct') }}:</span>
          <span class="brief-val">{{ props.lot.commodity_name }}</span>
        </div>
        <div class="brief-item">
          <span class="brief-label">{{ t('inventory.party') }}:</span>
          <span class="brief-val">{{ props.lot.party_name }}</span>
        </div>
      </div>

      <!-- Counted Qty Field -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.countedQty') }} <span class="req">*</span></label>
        <InputText
          :modelValue="counted_qty !== undefined ? String(counted_qty) : ''"
          @update:modelValue="val => counted_qty = val !== '' ? Number(val) : undefined"
          v-bind="countedQtyProps"
          type="number"
          min="0"
          class="w-full"
          :invalid="!!errors.counted_qty"
        />
        <small v-if="errors.counted_qty" class="field-error">{{ errors.counted_qty }}</small>
      </div>

      <!-- Live Delta Preview Box -->
      <div class="delta-box" :class="{ removed: delta < 0, added: delta > 0 }">
        <span class="delta-label">{{ t('inventory.currentQty') }}: <strong>{{ props.lot?.remaining_qty }}</strong></span>
        <span class="delta-arrow">➔</span>
        <span class="delta-label">{{ t('inventory.countedQty') }}: <strong>{{ counted_qty !== undefined ? counted_qty : '—' }}</strong></span>
        <div class="delta-badge-wrapper">
          <span v-if="delta < 0" class="delta-badge removed">
            {{ t('inventory.bagsRemoved', { count: Math.abs(delta) }) }}
          </span>
          <span v-else-if="delta > 0" class="delta-badge added">
            {{ t('inventory.bagsAdded', { count: delta }) }}
          </span>
          <span v-else class="delta-badge neutral">
            {{ t('inventory.bagsNoChange') }}
          </span>
        </div>
      </div>

      <!-- Reason Select Field -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.adjustmentReason') }} <span class="req">*</span></label>
        <Select
          v-model="reason"
          v-bind="reasonProps"
          :options="reasonOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
          :placeholder="t('inventory.adjustmentReason')"
          :invalid="!!errors.reason"
        />
        <small v-if="errors.reason" class="field-error">{{ errors.reason }}</small>
      </div>

      <!-- Adjustment Date DatePicker -->
      <div class="form-group">
        <label class="form-label">{{ t('inventory.adjustmentDate') }} <span class="req">*</span></label>
        <DatePicker
          v-model="adjustment_date"
          v-bind="adjustmentDateProps"
          dateFormat="dd/mm/yy"
          showIcon
          class="w-full"
          :invalid="!!errors.adjustment_date"
        />
        <small v-if="errors.adjustment_date" class="field-error">{{ errors.adjustment_date }}</small>
      </div>

      <!-- Note Field -->
      <div class="form-group">
        <label class="form-label">
          {{ t('inventory.adjustmentNote') }}
          <span v-if="reason === 'OTHER'" class="req">*</span>
        </label>
        <InputText
          v-model="note"
          v-bind="noteProps"
          type="text"
          class="w-full"
          :invalid="!!errors.note"
          :placeholder="reason === 'OTHER' ? t('validation.required') : ''"
        />
        <small v-if="errors.note" class="field-error">{{ errors.note }}</small>
      </div>

      <div class="dialog-actions-footer">
        <button class="btn-outlined" type="button" @click="handleClose" :disabled="isSubmitting">
          {{ t('common.cancel') }}
        </button>
        <button class="btn-primary" type="submit" :disabled="isSubmitting">
          <i v-if="isSubmitting" class="pi pi-spin pi-spinner mr-1"></i>
          <span>{{ t('common.save') }}</span>
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

.lot-brief-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 12px;
}

.brief-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brief-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.brief-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
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

.req {
  color: var(--status-danger-color, #ef4444);
}

.field-error {
  color: var(--status-danger-color, #ef4444);
  font-size: 12px;
  margin-top: 2px;
}

.delta-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s ease;
}

.delta-box.removed {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.25);
}

.delta-box.added {
  background: rgba(34, 197, 94, 0.05);
  border-color: rgba(34, 197, 94, 0.25);
}

.delta-label {
  font-size: 13px;
  color: var(--text-primary);
}

.delta-arrow {
  color: var(--text-secondary);
  font-weight: bold;
}

.delta-badge-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
  margin-top: 4px;
}

.delta-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 12px;
  text-transform: uppercase;
}

.delta-badge.removed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.delta-badge.added {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.delta-badge.neutral {
  background: var(--bg-surface-active);
  color: var(--text-secondary);
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
</style>

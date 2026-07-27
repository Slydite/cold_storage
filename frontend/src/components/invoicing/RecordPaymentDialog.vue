<script setup lang="ts">
import { watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import { useI18n } from 'vue-i18n'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import { useCreateInvoicePayment } from '../../composables/useInvoices'
import { formatCurrency } from '../../utils/format'
import type { InvoiceOutput } from '../../api/invoicing'
import type { MethodEnum } from '../../api/generated/types.gen'

interface Props {
  visible: boolean
  invoice: InvoiceOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: []
}>()

const { t } = useI18n()
const toast = useToast()
const createPaymentMutation = useCreateInvoicePayment()

const paymentMethodOptions = computed(() => [
  { label: t('paymentMethod.BANK_TRANSFER'), value: 'BANK_TRANSFER' },
  { label: t('paymentMethod.UPI'), value: 'UPI' },
  { label: t('paymentMethod.CASH'), value: 'CASH' },
  { label: t('paymentMethod.CHEQUE'), value: 'CHEQUE' },
  { label: t('paymentMethod.OTHER'), value: 'OTHER' }
])

const paymentSchema = computed(() =>
  z.object({
    amount: z.number().min(0.01, t('validation.paymentAmountMin')),
    payment_date: z
      .date()
      .nullable()
      .refine((v): v is Date => v != null, { message: t('validation.paymentDateRequired') }),
    method: z.enum(['CASH', 'BANK_TRANSFER', 'CHEQUE', 'UPI', 'OTHER'], {
      message: t('validation.methodRequired')
    }),
    reference: z.string().optional(),
    notes: z.string().optional()
  })
)

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(paymentSchema.value)),
  initialValues: {
    amount: 0,
    payment_date: new Date(),
    method: 'BANK_TRANSFER' as MethodEnum,
    reference: '',
    notes: ''
  }
})

const [amount, amountProps] = defineField('amount')
const [payment_date, paymentDateProps] = defineField('payment_date')
const [method, methodProps] = defineField('method')
const [reference, refProps] = defineField('reference')
const [notes, notesProps] = defineField('notes')

watch(
  () => props.visible,
  (newVal) => {
    if (newVal && props.invoice) {
      const due = Number(props.invoice.amount_due || props.invoice.total_amount || 0)
      resetForm({
        values: {
          amount: due > 0 ? due : 0,
          payment_date: new Date(),
          method: 'BANK_TRANSFER',
          reference: '',
          notes: ''
        }
      })
    }
  }
)

const onSubmit = handleSubmit(async (values) => {
  if (!props.invoice) return

  const yyyy = values.payment_date.getFullYear()
  const mm = String(values.payment_date.getMonth() + 1).padStart(2, '0')
  const dd = String(values.payment_date.getDate()).padStart(2, '0')
  const formattedDate = `${yyyy}-${mm}-${dd}`

  try {
    await createPaymentMutation.mutateAsync({
      invoiceId: props.invoice.id,
      body: {
        amount: String(values.amount),
        payment_date: formattedDate,
        method: values.method,
        reference: values.reference || undefined,
        notes: values.notes || undefined
      }
    })

    toast.add({
      severity: 'success',
      summary: t('invoicing.paymentRecordedSummary'),
      detail: t('invoicing.paymentRecordedDetail', { amount: formatCurrency(values.amount), number: props.invoice.invoice_number }),
      life: 3000
    })

    emit('success')
    emit('update:visible', false)
  } catch (err) {
    const msg = err instanceof Error ? err.message : t('invoicing.recordPaymentFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="t('invoicing.recordPaymentHeader', { number: invoice?.invoice_number || '' })"
    :style="{ width: '450px' }"
  >
    <form v-if="invoice" @submit.prevent="onSubmit" class="dialog-form">
      <div class="summary-due-card">
        <div class="due-item">
          <span class="label">{{ t('common.totalAmount') }}:</span>
          <span class="val font-bold">{{ formatCurrency(Number(invoice.total_amount || 0)) }}</span>
        </div>
        <div class="due-item">
          <span class="label">{{ t('common.amountPaid') }}:</span>
          <span class="val text-success">{{ formatCurrency(Number(invoice.amount_paid || 0)) }}</span>
        </div>
        <div class="due-item">
          <span class="label">{{ t('common.amountDue') }}:</span>
          <span class="val text-danger font-bold">{{ formatCurrency(Number(invoice.amount_due || 0)) }}</span>
        </div>
      </div>

      <div class="form-group">
        <label for="pay-amount">{{ t('invoicing.paymentAmount') }} <span class="required">*</span></label>
        <InputNumber
          id="pay-amount"
          v-model="amount"
          v-bind="amountProps"
          :min="0.01"
          mode="decimal"
          :minFractionDigits="2"
          :maxFractionDigits="2"
          class="w-full"
          :class="{ 'p-invalid': errors.amount }"
        />
        <span v-if="errors.amount" class="field-error">{{ errors.amount }}</span>
      </div>

      <div class="form-group">
        <label for="pay-date">{{ t('invoicing.paymentDate') }} <span class="required">*</span></label>
        <DatePicker
          id="pay-date"
          v-model="payment_date"
          v-bind="paymentDateProps"
          dateFormat="dd/mm/yy"
          showIcon
          class="w-full"
          :invalid="!!errors.payment_date"
        />
        <span v-if="errors.payment_date" class="field-error">{{ errors.payment_date }}</span>
      </div>

      <div class="form-group">
        <label for="pay-method">{{ t('invoicing.paymentMethod') }} <span class="required">*</span></label>
        <Select
          id="pay-method"
          v-model="method"
          v-bind="methodProps"
          :options="paymentMethodOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
        />
      </div>

      <div class="form-group">
        <label for="pay-ref">{{ t('invoicing.transactionRefNo') }}</label>
        <InputText
          id="pay-ref"
          v-model="reference"
          v-bind="refProps"
          :placeholder="t('invoicing.transactionRefNo')"
          class="w-full"
        />
      </div>

      <div class="form-group">
        <label for="pay-notes">{{ t('invoicing.notes') }}</label>
        <InputText
          id="pay-notes"
          v-model="notes"
          v-bind="notesProps"
          :placeholder="t('invoicing.notes')"
          class="w-full"
        />
      </div>

      <div class="dialog-actions">
        <button
          type="button"
          class="btn-outlined"
          @click="emit('update:visible', false)"
          :disabled="createPaymentMutation.isPending.value"
        >
          {{ t('common.cancel') }}
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="createPaymentMutation.isPending.value"
        >
          {{ createPaymentMutation.isPending.value ? t('invoicing.recording') : t('common.save') }}
        </button>
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 8px;
}

.summary-due-card {
  display: flex;
  justify-content: space-between;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  padding: 12px;
  border-radius: 8px;
  font-size: 12.5px;
}

.due-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.due-item .label {
  font-size: 11px;
  color: var(--text-secondary);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--status-danger-color);
}

.field-error {
  font-size: 12px;
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.font-bold {
  font-weight: 700;
}

.text-success {
  color: var(--status-success-color);
  font-weight: 600;
}

.text-danger {
  color: var(--status-danger-color);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

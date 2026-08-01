<script setup lang="ts">
import { watch, computed, toRef } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import { useI18n } from 'vue-i18n'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import { useAdjustInvoice } from '../../composables/useInvoices'
import { formatCurrency } from '../../utils/format'
import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
import type { InvoiceOutput, DocumentTypeEnum } from '../../api/invoicing'

interface Props {
  visible: boolean
  invoice: InvoiceOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: []
}>()

const visibleRef = toRef(props, 'visible')
useHistoryDismiss(visibleRef, () => {
  emit('update:visible', false)
})

const { t } = useI18n()
const toast = useToast()
const adjustInvoiceMutation = useAdjustInvoice()

const documentTypeOptions = computed(() => [
  { label: t('invoicing.taxInvoice'), value: 'TAX_INVOICE' },
  { label: t('invoicing.billOfSupply'), value: 'BILL_OF_SUPPLY' }
])

const adjustSchema = computed(() =>
  z.object({
    discount_amount: z
      .string()
      .nullable()
      .optional()
      .refine(
        (val) => {
          if (!val) return true
          const num = Number(val)
          return !isNaN(num) && num >= 0
        },
        { message: t('validation.discountNegative') }
      )
      .refine(
        (val) => {
          if (!val || !props.invoice) return true
          const num = Number(val)
          const subtotal = Number(props.invoice.subtotal || 0)
          return num <= subtotal
        },
        { message: t('validation.discountExceedsSubtotal') }
      ),
    discount_reason: z.string().optional(),
    cgst_rate: z
      .string()
      .nullable()
      .optional()
      .refine(
        (val) => {
          if (!val) return true
          const num = Number(val)
          return !isNaN(num) && num >= 0
        },
        { message: t('validation.rateNotNegative') }
      ),
    sgst_rate: z
      .string()
      .nullable()
      .optional()
      .refine(
        (val) => {
          if (!val) return true
          const num = Number(val)
          return !isNaN(num) && num >= 0
        },
        { message: t('validation.rateNotNegative') }
      ),
    igst_rate: z
      .string()
      .nullable()
      .optional()
      .refine(
        (val) => {
          if (!val) return true
          const num = Number(val)
          return !isNaN(num) && num >= 0
        },
        { message: t('validation.rateNotNegative') }
      ),
    place_of_supply: z.string().optional(),
    document_type: z.enum(['TAX_INVOICE', 'BILL_OF_SUPPLY']),
    is_reverse_charge: z.boolean().optional(),
    exemption_reason: z.string().optional()
  })
)

const { handleSubmit, errors, defineField, resetForm, values: formValues } = useForm({
  validationSchema: computed(() => toTypedSchema(adjustSchema.value)),
  initialValues: {
    discount_amount: '0',
    discount_reason: '',
    cgst_rate: '0',
    sgst_rate: '0',
    igst_rate: '0',
    place_of_supply: '',
    document_type: 'TAX_INVOICE' as DocumentTypeEnum,
    is_reverse_charge: false,
    exemption_reason: ''
  }
})

const [discount_amount, discountAmountProps] = defineField('discount_amount')
const [discount_reason, discountReasonProps] = defineField('discount_reason')
const [cgst_rate, cgstRateProps] = defineField('cgst_rate')
const [sgst_rate, sgstRateProps] = defineField('sgst_rate')
const [igst_rate, igstRateProps] = defineField('igst_rate')
const [place_of_supply, placeOfSupplyProps] = defineField('place_of_supply')
const [document_type, documentTypeProps] = defineField('document_type')
const [is_reverse_charge, isReverseChargeProps] = defineField('is_reverse_charge')
const [exemption_reason, exemptionReasonProps] = defineField('exemption_reason')

watch(
  () => props.visible,
  (newVal) => {
    if (newVal && props.invoice) {
      resetForm({
        values: {
          discount_amount: props.invoice.discount_amount ?? '0',
          discount_reason: props.invoice.discount_reason ?? '',
          cgst_rate: props.invoice.cgst_rate ?? '0',
          sgst_rate: props.invoice.sgst_rate ?? '0',
          igst_rate: props.invoice.igst_rate ?? '0',
          place_of_supply: props.invoice.place_of_supply ?? '',
          document_type: props.invoice.document_type ?? 'TAX_INVOICE',
          is_reverse_charge: props.invoice.is_reverse_charge ?? false,
          exemption_reason: props.invoice.exemption_reason ?? ''
        }
      })
    }
  },
  { immediate: true }
)

const previewTaxableValue = computed(() => {
  if (!props.invoice) return 0
  const subtotal = Number(props.invoice.subtotal || 0)
  const discount = Number(formValues.discount_amount || 0)
  return Math.max(0, subtotal - discount)
})

const previewCgstAmount = computed(() => {
  if (formValues.document_type === 'BILL_OF_SUPPLY') return 0
  const rate = Number(formValues.cgst_rate || 0)
  return Math.round(previewTaxableValue.value * rate) / 100
})

const previewSgstAmount = computed(() => {
  if (formValues.document_type === 'BILL_OF_SUPPLY') return 0
  const rate = Number(formValues.sgst_rate || 0)
  return Math.round(previewTaxableValue.value * rate) / 100
})

const previewIgstAmount = computed(() => {
  if (formValues.document_type === 'BILL_OF_SUPPLY') return 0
  const rate = Number(formValues.igst_rate || 0)
  return Math.round(previewTaxableValue.value * rate) / 100
})

const previewTotalAmount = computed(() => {
  const taxable = previewTaxableValue.value
  if (formValues.document_type === 'BILL_OF_SUPPLY') {
    return taxable
  }
  return taxable + previewCgstAmount.value + previewSgstAmount.value + previewIgstAmount.value
})

const onSubmit = handleSubmit(async (values) => {
  if (!props.invoice) return

  try {
    await adjustInvoiceMutation.mutateAsync({
      id: props.invoice.id,
      body: {
        discount_amount: values.discount_amount || '0.00',
        discount_reason: values.discount_reason || '',
        cgst_rate: values.cgst_rate || '0.00',
        sgst_rate: values.sgst_rate || '0.00',
        igst_rate: values.igst_rate || '0.00',
        place_of_supply: values.place_of_supply || '',
        document_type: values.document_type,
        is_reverse_charge: values.is_reverse_charge ?? false,
        exemption_reason: values.exemption_reason || ''
      }
    })

    toast.add({
      severity: 'success',
      summary: t('invoicing.adjustSuccessSummary'),
      detail: t('invoicing.adjustSuccessDetail'),
      life: 3000
    })

    emit('success')
    emit('update:visible', false)
  } catch (err) {
    const msg = err instanceof Error ? err.message : t('invoicing.adjustFailedSummary')
    toast.add({
      severity: 'error',
      summary: t('invoicing.adjustFailedSummary'),
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
    :header="t('invoicing.adjustInvoiceDialogHeader', { number: invoice?.invoice_number || '' })"
    :style="{ width: '550px', maxWidth: '95vw' }"
  >
    <form v-if="invoice" @submit.prevent="onSubmit" class="dialog-form">
      <!-- Live Preview -->
      <div class="preview-banner">
        <div class="preview-title">{{ t('invoicing.previewTitle') }}</div>
        <div class="preview-grid">
          <div class="preview-item">
            <span class="p-label">{{ t('common.subtotal') }}:</span>
            <span class="p-val font-semibold">{{ formatCurrency(Number(invoice.subtotal || 0)) }}</span>
          </div>

          <div class="preview-item text-danger" v-if="Number(formValues.discount_amount || 0) > 0">
            <span class="p-label">{{ t('invoicing.discountAmount') }}:</span>
            <span class="p-val">-{{ formatCurrency(Number(formValues.discount_amount || 0)) }}</span>
          </div>

          <div class="preview-item">
            <span class="p-label">{{ t('invoicing.taxableValue') }}:</span>
            <span class="p-val font-bold">{{ formatCurrency(previewTaxableValue) }}</span>
          </div>

          <template v-if="formValues.document_type === 'TAX_INVOICE'">
            <div class="preview-item" v-if="previewCgstAmount > 0">
              <span class="p-label">{{ t('invoicing.cgstAmountLabel', { rate: formValues.cgst_rate || '0' }) }}:</span>
              <span class="p-val">{{ formatCurrency(previewCgstAmount) }}</span>
            </div>
            <div class="preview-item" v-if="previewSgstAmount > 0">
              <span class="p-label">{{ t('invoicing.sgstAmountLabel', { rate: formValues.sgst_rate || '0' }) }}:</span>
              <span class="p-val">{{ formatCurrency(previewSgstAmount) }}</span>
            </div>
            <div class="preview-item" v-if="previewIgstAmount > 0">
              <span class="p-label">{{ t('invoicing.igstAmountLabel', { rate: formValues.igst_rate || '0' }) }}:</span>
              <span class="p-val">{{ formatCurrency(previewIgstAmount) }}</span>
            </div>
          </template>

          <div class="preview-item grand-total-preview">
            <span class="p-label">{{ t('common.grandTotal') }}:</span>
            <span class="p-val grand-val font-bold">{{ formatCurrency(previewTotalAmount) }}</span>
          </div>
        </div>
      </div>

      <!-- Fields Grid -->
      <div class="form-grid">
        <div class="form-group">
          <label for="inv-doc-type">{{ t('invoicing.documentType') }} <span class="required">*</span></label>
          <Select
            id="inv-doc-type"
            v-model="document_type"
            v-bind="documentTypeProps"
            :options="documentTypeOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="inv-place-supply">{{ t('invoicing.placeOfSupply') }}</label>
          <InputText
            id="inv-place-supply"
            v-model="place_of_supply"
            v-bind="placeOfSupplyProps"
            placeholder="e.g. 24-Gujarat"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="inv-discount">{{ t('invoicing.discountAmount') }}</label>
          <InputText
            id="inv-discount"
            v-model="discount_amount"
            v-bind="discountAmountProps"
            placeholder="0.00"
            class="w-full"
            :class="{ 'p-invalid': errors.discount_amount }"
          />
          <span v-if="errors.discount_amount" class="field-error">{{ errors.discount_amount }}</span>
        </div>

        <div class="form-group">
          <label for="inv-discount-reason">{{ t('invoicing.discountReason') }}</label>
          <InputText
            id="inv-discount-reason"
            v-model="discount_reason"
            v-bind="discountReasonProps"
            placeholder="e.g. Volume discount"
            class="w-full"
          />
        </div>

        <template v-if="formValues.document_type === 'TAX_INVOICE'">
          <div class="form-group">
            <label for="inv-cgst">{{ t('invoicing.cgstRate') }}</label>
            <InputText
              id="inv-cgst"
              v-model="cgst_rate"
              v-bind="cgstRateProps"
              placeholder="0.00"
              class="w-full"
              :class="{ 'p-invalid': errors.cgst_rate }"
            />
            <span v-if="errors.cgst_rate" class="field-error">{{ errors.cgst_rate }}</span>
          </div>

          <div class="form-group">
            <label for="inv-sgst">{{ t('invoicing.sgstRate') }}</label>
            <InputText
              id="inv-sgst"
              v-model="sgst_rate"
              v-bind="sgstRateProps"
              placeholder="0.00"
              class="w-full"
              :class="{ 'p-invalid': errors.sgst_rate }"
            />
            <span v-if="errors.sgst_rate" class="field-error">{{ errors.sgst_rate }}</span>
          </div>

          <div class="form-group span-2">
            <label for="inv-igst">{{ t('invoicing.igstRate') }}</label>
            <InputText
              id="inv-igst"
              v-model="igst_rate"
              v-bind="igstRateProps"
              placeholder="0.00"
              class="w-full"
              :class="{ 'p-invalid': errors.igst_rate }"
            />
            <span v-if="errors.igst_rate" class="field-error">{{ errors.igst_rate }}</span>
          </div>
        </template>

        <div v-if="formValues.document_type === 'BILL_OF_SUPPLY'" class="form-group span-2">
          <label for="inv-exemption">{{ t('invoicing.exemptionReason') }}</label>
          <InputText
            id="inv-exemption"
            v-model="exemption_reason"
            v-bind="exemptionReasonProps"
            placeholder="e.g. Exempt under agricultural produce storage"
            class="w-full"
          />
        </div>

        <div class="form-group checkbox-group span-2">
          <Checkbox id="inv-rev-charge" v-model="is_reverse_charge" v-bind="isReverseChargeProps" :binary="true" />
          <label for="inv-rev-charge">{{ t('invoicing.reverseCharge') }}</label>
        </div>
      </div>

      <div class="dialog-actions">
        <button
          type="button"
          class="btn-outlined"
          @click="emit('update:visible', false)"
          :disabled="adjustInvoiceMutation.isPending.value"
        >
          {{ t('common.cancel') }}
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="adjustInvoiceMutation.isPending.value"
        >
          {{ adjustInvoiceMutation.isPending.value ? t('common.loading') : t('common.save') }}
        </button>
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.preview-banner {
  background: var(--bg-surface-hover);
  border: 1px dashed var(--border-strong);
  border-radius: 10px;
  padding: 14px;
}

.preview-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 16px;
  font-size: 12.5px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.p-label {
  color: var(--text-secondary);
}

.p-val {
  color: var(--text-primary);
}

.text-danger {
  color: var(--status-danger-color);
}

.grand-total-preview {
  grid-column: span 2;
  border-top: 1px solid var(--border-strong);
  padding-top: 8px;
  margin-top: 4px;
  font-size: 14px;
}

.grand-val {
  color: var(--text-primary);
  font-size: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.span-2 {
  grid-column: span 2;
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

.checkbox-group {
  display: flex;
  flex-direction: row !important;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.checkbox-group label {
  cursor: pointer;
  user-select: none;
}

.w-full {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

<script setup lang="ts">
import { ref, toRef } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { Trash2, CreditCard, Printer, Mail, Sliders } from 'lucide-vue-next'
import { formatCurrency, formatQty } from '../../utils/format'
import { useDeleteInvoicePayment } from '../../composables/useInvoices'
import { downloadPdf } from '../../utils/downloadPdf'
import { emailInvoice } from '../../api/invoicing'
import { EMAIL_TO_CLIENT_ENABLED } from '../../config/features'
import RecordPaymentDialog from './RecordPaymentDialog.vue'
import AdjustInvoiceDialog from './AdjustInvoiceDialog.vue'
import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
import type { InvoiceOutput } from '../../api/invoicing'
import type { PaymentOutput } from '../../api/generated/types.gen'

interface Props {
  visible: boolean
  invoice: InvoiceOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  refresh: []
}>()

const visibleRef = toRef(props, 'visible')
useHistoryDismiss(visibleRef, () => {
  emit('update:visible', false)
})

const { t } = useI18n()
const confirm = useConfirm()
const toast = useToast()
const deletePaymentMutation = useDeleteInvoicePayment()

const showRecordPayment = ref(false)
const showAdjustDialog = ref(false)
const downloadingPdf = ref(false)
const emailing = ref(false)

function formatDateTime(d?: string | null): string {
  if (!d) return t('common.never')
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d || ''
  }
}

async function handleDownloadPdf() {
  if (!props.invoice) return
  downloadingPdf.value = true
  try {
    await downloadPdf(`/api/invoices/${props.invoice.id}/pdf/`, `${props.invoice.invoice_number}.pdf`)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.pdfFailed'),
      detail: err instanceof Error ? err.message : t('common.pdfFailed'),
      life: 5000
    })
  } finally {
    downloadingPdf.value = false
  }
}

async function handleEmailToClient() {
  if (!props.invoice) return
  emailing.value = true
  try {
    await emailInvoice(props.invoice.id)
    toast.add({
      severity: 'success',
      summary: t('common.emailSentSuccess'),
      detail: t('common.emailSentSuccessDetail'),
      life: 5000
    })
    emit('refresh')
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : t('errors.generic')
    if (message.includes('Failed to send email')) {
      toast.add({
        severity: 'error',
        summary: t('common.emailSendFailed'),
        detail: t('common.emailSendFailedDetail', { error: message }),
        life: 7000
      })
    } else {
      toast.add({
        severity: 'warn',
        summary: t('common.error'),
        detail: message,
        life: 5000
      })
    }
  } finally {
    emailing.value = false
  }
}


const getPaymentSeverity = (status?: string) => {
  switch (status) {
    case 'PAID':
      return 'success'
    case 'PARTIAL':
      return 'warn'
    case 'UNPAID':
    default:
      return 'danger'
  }
}

const handleDeletePayment = (payment: PaymentOutput) => {
  if (!props.invoice) return

  confirm.require({
    message: t('invoicing.deletePaymentMessage', { amount: formatCurrency(Number(payment.amount)) }),
    header: t('invoicing.deletePaymentHeader'),
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: t('common.cancel'),
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: t('invoicing.deletePayment'),
      severity: 'danger'
    },
    accept: async () => {
      try {
        await deletePaymentMutation.mutateAsync({
          invoiceId: props.invoice!.id,
          paymentId: payment.id
        })
        toast.add({
          severity: 'success',
          summary: t('invoicing.paymentDeletedSummary'),
          detail: t('invoicing.paymentDeletedDetail'),
          life: 3000
        })
        emit('refresh')
      } catch (err) {
        const msg = err instanceof Error ? err.message : t('errors.generic')
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail: msg,
          life: 5000
        })
      }
    }
  })
}
</script>

<template>
  <div>
    <Dialog
      :visible="visible"
      @update:visible="emit('update:visible', $event)"
      modal
      :header="t('invoicing.invoiceDetails', { number: invoice?.invoice_number || '' })"
      :style="{ width: '750px', maxWidth: '95vw' }"
    >
      <div v-if="invoice" class="invoice-detail-body">
        <!-- Prominent Document Title and Reverse Charge indicator -->
        <div
          class="document-type-banner"
          :class="invoice.document_type === 'TAX_INVOICE' ? 'tax-invoice' : 'bill-supply'"
        >
          <div class="banner-title">
            {{ invoice.document_type === 'TAX_INVOICE' ? t('invoicing.taxInvoice') : t('invoicing.billOfSupply') }}
          </div>
          <Tag
            v-if="invoice.is_reverse_charge"
            severity="danger"
            :value="t('invoicing.reverseCharge')"
            class="reverse-charge-tag"
          />
        </div>

        <!-- Metadata Grid -->
        <div class="meta-card">
          <div class="meta-grid">
            <div class="meta-item">
              <span class="label">{{ t('delivery.customerParty') }}</span>
              <strong class="val">{{ invoice.party_name || `${t('grn.party')} #${invoice.party_id}` }}</strong>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('invoicing.invoiceDate') }}</span>
              <span class="val">{{ invoice.invoice_date }}</span>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('invoicing.paymentStatus') }}</span>
              <div>
                <Tag
                  :value="invoice.payment_status ? t(`status.${invoice.payment_status}`) : t('status.UNPAID')"
                  :severity="getPaymentSeverity(invoice.payment_status)"
                />
              </div>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('invoicing.financialYear') }}</span>
              <span class="val">{{ invoice.financial_year }}</span>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('invoicing.placeOfSupply') }}</span>
              <span class="val">{{ invoice.place_of_supply || '—' }}</span>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('common.amountPaid') }}</span>
              <span class="val text-success text-lg">{{ formatCurrency(Number(invoice.amount_paid || 0)) }}</span>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('common.amountDue') }}</span>
              <strong class="val text-danger text-lg">{{ formatCurrency(Number(invoice.amount_due || 0)) }}</strong>
            </div>

            <div class="meta-item">
              <span class="label">{{ t('common.lastEmailed') }}</span>
              <span class="val">{{ formatDateTime(invoice.last_emailed_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Invoice Line Items Table -->
        <div class="section-container">
          <h4 class="section-title">{{ t('invoicing.billedLineItems') }}</h4>
          <DataTable
            :value="invoice.lines || []"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="description" :header="t('common.description')">
              <template #body="{ data }">
                <span>{{ data.description }}</span>
              </template>
            </Column>
            <Column field="quantity" :header="t('common.quantity')">
              <template #body="{ data }">
                <span class="num-val">
                  {{ data.quantity !== null && data.quantity !== undefined ? `${formatQty(data.quantity, 0)}${data.unit ? ' ' + data.unit : ''}` : '-' }}
                </span>
              </template>
            </Column>
            <Column field="rate_per_unit" :header="t('common.perUnitRate')">
              <template #body="{ data }">
                <span class="num-val">
                  {{ data.rate_per_unit !== null && data.rate_per_unit !== undefined ? formatCurrency(Number(data.rate_per_unit)) : '-' }}
                </span>
              </template>
            </Column>
            <Column field="amount" :header="t('common.subtotalRs')">
              <template #body="{ data }">
                <strong class="num-val">{{ formatCurrency(Number(data.amount || 0)) }}</strong>
              </template>
            </Column>
          </DataTable>

          <!-- Totals Block -->
          <div class="totals-wrapper">
            <div class="totals-card">
              <div class="totals-row">
                <span class="totals-label">{{ t('common.subtotal') }}</span>
                <span class="totals-val">{{ formatCurrency(Number(invoice.subtotal || 0)) }}</span>
              </div>
              
              <div v-if="Number(invoice.discount_amount || 0) !== 0" class="totals-row discount-row">
                <span class="totals-label">
                  {{ t('invoicing.discountAmount') }}
                  <small class="discount-reason" v-if="invoice.discount_reason">({{ invoice.discount_reason }})</small>
                </span>
                <span class="totals-val">-{{ formatCurrency(Number(invoice.discount_amount)) }}</span>
              </div>
              
              <div class="totals-row taxable-row">
                <span class="totals-label">{{ t('invoicing.taxableValue') }}</span>
                <span class="totals-val">{{ formatCurrency(Number(invoice.taxable_value || 0)) }}</span>
              </div>
              
              <!-- Tax Rows (only if NOT Bill of Supply) -->
              <template v-if="invoice.document_type !== 'BILL_OF_SUPPLY'">
                <div v-if="Number(invoice.cgst_amount || 0) !== 0" class="totals-row">
                  <span class="totals-label">{{ t('invoicing.cgstAmountLabel', { rate: invoice.cgst_rate || '0' }) }}</span>
                  <span class="totals-val">{{ formatCurrency(Number(invoice.cgst_amount)) }}</span>
                </div>
                <div v-if="Number(invoice.sgst_amount || 0) !== 0" class="totals-row">
                  <span class="totals-label">{{ t('invoicing.sgstAmountLabel', { rate: invoice.sgst_rate || '0' }) }}</span>
                  <span class="totals-val">{{ formatCurrency(Number(invoice.sgst_amount)) }}</span>
                </div>
                <div v-if="Number(invoice.igst_amount || 0) !== 0" class="totals-row">
                  <span class="totals-label">{{ t('invoicing.igstAmountLabel', { rate: invoice.igst_rate || '0' }) }}</span>
                  <span class="totals-val">{{ formatCurrency(Number(invoice.igst_amount)) }}</span>
                </div>
              </template>
              
              <!-- Exemption Reason (on Bill of Supply if present) -->
              <div v-if="invoice.document_type === 'BILL_OF_SUPPLY' && invoice.exemption_reason" class="totals-row exemption-row">
                <span class="totals-label">{{ t('invoicing.exemptionReason') }}</span>
                <span class="totals-val text-sm font-normal">{{ invoice.exemption_reason }}</span>
              </div>
              
              <hr class="totals-separator" />
              
              <div class="totals-row grand-total-row">
                <span class="totals-label">{{ t('common.grandTotal') }}</span>
                <span class="totals-val grand-total-val">{{ formatCurrency(Number(invoice.total_amount || 0)) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Payment History Table -->
        <div class="section-container">
          <div class="section-header">
            <h4 class="section-title">{{ t('invoicing.paymentReceiptsHistory') }}</h4>
            <button
              v-if="invoice.payment_status !== 'PAID'"
              type="button"
              class="btn-primary btn-sm"
              @click="showRecordPayment = true"
            >
              <CreditCard :size="14" />
              <span>{{ t('invoicing.recordPayment') }}</span>
            </button>
          </div>

          <div v-if="!invoice.payments || invoice.payments.length === 0" class="empty-payments">
            <p>{{ t('invoicing.noPaymentReceipts') }}</p>
          </div>

          <DataTable
            v-else
            :value="invoice.payments"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="payment_date" :header="t('common.date')">
              <template #body="{ data }">
                <span>{{ data.payment_date }}</span>
              </template>
            </Column>

            <Column field="method" :header="t('invoicing.paymentMethod')">
              <template #body="{ data }">
                <span class="badge-subtle">{{ data.method ? t(`paymentMethod.${data.method}`) : t('paymentMethod.CASH') }}</span>
              </template>
            </Column>

            <Column field="reference" :header="t('invoicing.transactionRefNo')">
              <template #body="{ data }">
                <span>{{ data.reference || '—' }}</span>
              </template>
            </Column>

            <Column field="amount" :header="t('invoicing.paymentAmount')">
              <template #body="{ data }">
                <strong class="num-val text-success">{{ formatCurrency(Number(data.amount || 0)) }}</strong>
              </template>
            </Column>

            <Column :header="t('common.actions')" style="width: 70px" alignFrozen="right">
              <template #body="{ data }">
                <button
                  type="button"
                  class="icon-btn danger-hover"
                  :title="t('invoicing.deletePayment')"
                  @click="handleDeletePayment(data)"
                >
                  <Trash2 :size="15" />
                </button>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <div class="pdf-action-group">
            <button
              v-if="invoice?.status === 'DRAFT'"
              class="btn-primary"
              type="button"
              @click="showAdjustDialog = true"
            >
              <Sliders :size="15" />
              <span>{{ t('invoicing.adjustInvoice') }}</span>
            </button>
            <button
              v-if="invoice"
              class="btn-outlined"
              type="button"
              title="PDF"
              aria-label="PDF"
              :disabled="downloadingPdf"
              @click="handleDownloadPdf"
            >
              <Printer :size="15" />
              <span>PDF</span>
            </button>
            <button
              v-if="EMAIL_TO_CLIENT_ENABLED && invoice"
              class="btn-outlined"
              type="button"
              :disabled="!invoice.party_email || emailing"
              :title="!invoice.party_email ? t('common.noClientEmailTooltip') : t('common.emailToClient')"
              @click="handleEmailToClient"
            >
              <Mail :size="15" />
              <span>{{ emailing ? t('common.loading') : t('common.emailToClient') }}</span>
            </button>
          </div>
          <button class="btn-outlined" type="button" @click="emit('update:visible', false)">{{ t('common.close') }}</button>
        </div>
      </template>
    </Dialog>

    <!-- Record Payment Dialog -->
    <RecordPaymentDialog
      v-model:visible="showRecordPayment"
      :invoice="invoice"
      @success="emit('refresh')"
    />

    <!-- Adjust Invoice Dialog -->
    <AdjustInvoiceDialog
      v-model:visible="showAdjustDialog"
      :invoice="invoice"
      @success="emit('refresh')"
    />
  </div>
</template>

<style scoped>
.invoice-detail-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 8px;
}

.meta-card {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 16px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item .label {
  font-size: 11.5px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.meta-item .val {
  font-size: 13.5px;
  color: var(--text-primary);
}

.text-lg {
  font-size: 16px !important;
  font-weight: 700;
}

.text-success {
  color: var(--status-success-color);
}

.text-danger {
  color: var(--status-danger-color);
}

.section-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-sm {
  font-size: 12px;
  padding: 6px 12px;
}

.empty-payments {
  padding: 18px;
  background: var(--bg-page);
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.document-type-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-strong);
}

.document-type-banner.tax-invoice {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.3);
}

.document-type-banner.tax-invoice .banner-title {
  color: #10b981;
  font-weight: 700;
  font-size: 16px;
}

.document-type-banner.bill-supply {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.3);
}

.document-type-banner.bill-supply .banner-title {
  color: #3b82f6;
  font-weight: 700;
  font-size: 16px;
}

.reverse-charge-tag {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.totals-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.totals-card {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 16px;
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.totals-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.totals-label {
  font-weight: 500;
}

.totals-val {
  font-weight: 600;
  color: var(--text-primary);
}

.discount-row {
  color: var(--status-danger-color);
}
.discount-row .totals-val {
  color: var(--status-danger-color);
}
.discount-reason {
  font-size: 11px;
  color: var(--text-secondary);
  display: block;
}

.taxable-row {
  border-top: 1px dashed var(--border-strong);
  border-bottom: 1px dashed var(--border-strong);
  padding: 6px 0;
  margin: 4px 0;
}
.taxable-row .totals-val {
  font-weight: 700;
}

.exemption-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 6px;
  background: var(--bg-page);
  border-radius: 6px;
  border: 1px solid var(--border-strong);
}

.totals-separator {
  border: 0;
  border-top: 1px solid var(--border-strong);
  margin: 4px 0;
}

.grand-total-row {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 700;
}

.grand-total-val {
  font-size: 18px;
  color: var(--text-primary);
}

.badge-subtle {
  font-size: 12px;
  background: var(--bg-page);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .meta-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.pdf-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

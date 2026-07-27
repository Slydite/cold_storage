<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { Trash2, CreditCard } from 'lucide-vue-next'
import { formatCurrency, formatQty } from '../../utils/format'
import { useDeleteInvoicePayment } from '../../composables/useInvoices'
import RecordPaymentDialog from './RecordPaymentDialog.vue'
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

const confirm = useConfirm()
const toast = useToast()
const deletePaymentMutation = useDeleteInvoicePayment()

const showRecordPayment = ref(false)

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
    message: `Are you sure you want to delete payment of ${formatCurrency(Number(payment.amount))}?`,
    header: 'Confirm Payment Deletion',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Delete Payment',
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
          summary: 'Payment Deleted',
          detail: 'Payment deleted successfully',
          life: 3000
        })
        emit('refresh')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to delete payment'
        toast.add({
          severity: 'error',
          summary: 'Error',
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
      :header="`Invoice Details: ${invoice?.invoice_number || ''}`"
      :style="{ width: '750px', maxWidth: '95vw' }"
    >
      <div v-if="invoice" class="invoice-detail-body">
        <!-- Metadata Grid -->
        <div class="meta-card">
          <div class="meta-grid">
            <div class="meta-item">
              <span class="label">Party / Customer</span>
              <strong class="val">{{ invoice.party_name || 'Party #' + invoice.party_id }}</strong>
            </div>

            <div class="meta-item">
              <span class="label">Invoice Date</span>
              <span class="val">{{ invoice.invoice_date }}</span>
            </div>

            <div class="meta-item">
              <span class="label">Payment Status</span>
              <div>
                <Tag
                  :value="invoice.payment_status || 'UNPAID'"
                  :severity="getPaymentSeverity(invoice.payment_status)"
                />
              </div>
            </div>

            <div class="meta-item">
              <span class="label">Total Amount</span>
              <strong class="val text-lg">{{ formatCurrency(Number(invoice.total_amount || 0)) }}</strong>
            </div>

            <div class="meta-item">
              <span class="label">Amount Paid</span>
              <span class="val text-success text-lg">{{ formatCurrency(Number(invoice.amount_paid || 0)) }}</span>
            </div>

            <div class="meta-item">
              <span class="label">Amount Due</span>
              <strong class="val text-danger text-lg">{{ formatCurrency(Number(invoice.amount_due || 0)) }}</strong>
            </div>
          </div>
        </div>

        <!-- Invoice Line Items Table -->
        <div class="section-container">
          <h4 class="section-title">Invoice Billed Line Items</h4>
          <DataTable
            :value="invoice.lines || []"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="description" header="Description">
              <template #body="{ data }">
                <span>{{ data.description || 'Rent / Charge Line' }}</span>
              </template>
            </Column>
            <Column field="quantity" header="Qty">
              <template #body="{ data }">
                <span class="num-val">{{ formatQty(data.quantity || 0, 0) }}</span>
              </template>
            </Column>
            <Column field="unit_price" header="Rate (₹)">
              <template #body="{ data }">
                <span class="num-val">{{ formatCurrency(Number(data.unit_price || 0)) }}</span>
              </template>
            </Column>
            <Column field="amount" header="Subtotal (₹)">
              <template #body="{ data }">
                <strong class="num-val">{{ formatCurrency(Number(data.amount || 0)) }}</strong>
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- Payment History Table -->
        <div class="section-container">
          <div class="section-header">
            <h4 class="section-title">Payment Receipts History</h4>
            <button
              v-if="invoice.payment_status !== 'PAID'"
              type="button"
              class="btn-primary btn-sm"
              @click="showRecordPayment = true"
            >
              <CreditCard :size="14" />
              <span>Record Payment</span>
            </button>
          </div>

          <div v-if="!invoice.payments || invoice.payments.length === 0" class="empty-payments">
            <p>No payment receipts recorded for this invoice yet.</p>
          </div>

          <DataTable
            v-else
            :value="invoice.payments"
            size="small"
            stripedRows
            responsiveLayout="scroll"
            class="custom-datatable"
          >
            <Column field="payment_date" header="Date">
              <template #body="{ data }">
                <span>{{ data.payment_date }}</span>
              </template>
            </Column>

            <Column field="method" header="Method">
              <template #body="{ data }">
                <span class="badge-subtle">{{ data.method || 'CASH' }}</span>
              </template>
            </Column>

            <Column field="reference_number" header="Reference No.">
              <template #body="{ data }">
                <span>{{ data.reference_number || '—' }}</span>
              </template>
            </Column>

            <Column field="amount" header="Amount (₹)">
              <template #body="{ data }">
                <strong class="num-val text-success">{{ formatCurrency(Number(data.amount || 0)) }}</strong>
              </template>
            </Column>

            <Column header="Actions" style="width: 70px" alignFrozen="right">
              <template #body="{ data }">
                <button
                  type="button"
                  class="icon-btn danger-hover"
                  title="Delete Payment"
                  @click="handleDeletePayment(data)"
                >
                  <Trash2 :size="15" />
                </button>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>
    </Dialog>

    <!-- Record Payment Dialog -->
    <RecordPaymentDialog
      v-model:visible="showRecordPayment"
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
  border: 1px solid var(--border-subtle);
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
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
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
</style>

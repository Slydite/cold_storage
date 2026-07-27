<script setup lang="ts">
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useI18n } from 'vue-i18n'
import { formatCurrency } from '../../utils/format'
import type { InvoiceOutput } from '../../api/invoicing'

defineProps<{
  invoices: InvoiceOutput[]
}>()

const { t } = useI18n()

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
</script>

<template>
  <div class="billing-section">
    <div class="section-header">
      <h3 class="section-title">{{ t('billing.outstandingInvoicesTitle') }}</h3>
      <p class="section-desc">{{ t('billing.outstandingInvoicesDesc') }}</p>
    </div>

    <div class="table-card">
      <div v-if="invoices.length === 0" class="empty-section">
        <p>{{ t('billing.noOutstandingInvoices') }}</p>
      </div>

      <DataTable
        v-else
        :value="invoices"
        size="small"
        stripedRows
        responsiveLayout="scroll"
        class="custom-datatable"
      >
        <Column field="invoice_number" :header="t('invoicing.invoiceNumber')">
          <template #body="{ data }">
            <span class="code-link">{{ data.invoice_number }}</span>
          </template>
        </Column>

        <Column field="party_name" :header="t('grn.party')">
          <template #body="{ data }">
            <strong>{{ data.party_name }}</strong>
          </template>
        </Column>

        <Column field="invoice_date" :header="t('invoicing.invoiceDate')" />

        <Column field="total_amount" :header="t('invoicing.total')">
          <template #body="{ data }">
            <span class="num-val">{{ formatCurrency(Number(data.total_amount || 0)) }}</span>
          </template>
        </Column>

        <Column field="amount_paid" :header="t('invoicing.paid')">
          <template #body="{ data }">
            <span class="num-val text-success">{{ formatCurrency(Number(data.amount_paid || 0)) }}</span>
          </template>
        </Column>

        <Column field="amount_due" :header="t('invoicing.due')">
          <template #body="{ data }">
            <strong class="num-val text-danger">{{ formatCurrency(Number(data.amount_due || 0)) }}</strong>
          </template>
        </Column>

        <Column field="payment_status" :header="t('invoicing.paymentStatus')">
          <template #body="{ data }">
            <Tag
              :value="t(`status.${(data.payment_status || 'UNPAID').toLowerCase()}`)"
              :severity="getPaymentSeverity(data.payment_status)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.billing-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.empty-section {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.text-danger {
  color: var(--status-danger-color);
}

.text-success {
  color: var(--status-success-color);
}
</style>

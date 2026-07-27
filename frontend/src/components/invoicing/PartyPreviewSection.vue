<script setup lang="ts">
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { formatCurrency, formatQty } from '../../utils/format'
import type { InvoicePreviewPartyOutput, InvoicePreviewLineOutput } from '../../api/invoicing'

defineProps<{
  party: InvoicePreviewPartyOutput
}>()
</script>

<template>
  <div class="party-preview-section">
    <div class="party-header">
      <h4 class="party-title">{{ party.party_name }}</h4>
      <span class="party-code-badge">{{ party.party_code }}</span>
    </div>

    <div class="table-scroll-container">
      <DataTable
        :value="party.lines"
        size="small"
        stripedRows
        class="custom-datatable"
      >
        <Column field="description" header="Description">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <span class="line-description">{{ data.description }}</span>
          </template>
        </Column>

        <Column field="lot_number" header="Lot">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <span>{{ data.lot_number ?? '—' }}</span>
          </template>
        </Column>

        <Column field="commodity_name" header="Commodity">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <span>{{ data.commodity_name ?? '—' }}</span>
          </template>
        </Column>

        <Column field="qty" header="Qty">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <span>{{ data.qty != null ? formatQty(data.qty, 0) : '—' }}</span>
          </template>
        </Column>

        <Column field="days_stored" header="Days Stored">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <span>{{ data.days_stored != null ? data.days_stored : '—' }}</span>
          </template>
        </Column>

        <Column field="amount" header="Amount">
          <template #body="{ data }: { data: InvoicePreviewLineOutput }">
            <strong class="num-val">{{ formatCurrency(Number(data.amount)) }}</strong>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="party-totals-card">
      <div class="total-row">
        <span class="total-label">Subtotal</span>
        <span class="total-val">{{ formatCurrency(Number(party.subtotal)) }}</span>
      </div>
      <div class="total-row">
        <span class="total-label">GST ({{ party.gst_rate }}%)</span>
        <span class="total-val">{{ formatCurrency(Number(party.gst_amount)) }}</span>
      </div>
      <div class="total-row grand-total">
        <span class="total-label">Total Amount</span>
        <strong class="total-val text-primary-val">{{ formatCurrency(Number(party.total_amount)) }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.party-preview-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 14px;
}

.party-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.party-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.party-code-badge {
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
}

.table-scroll-container {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.line-description {
  font-weight: 500;
  color: var(--text-primary);
}

.num-val {
  font-family: var(--font-mono, inherit);
}

.party-totals-card {
  display: flex;
  flex-direction: column;
  align-self: flex-end;
  width: 100%;
  max-width: 280px;
  gap: 6px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
}

.total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
}

.total-row.grand-total {
  border-top: 1px dashed var(--border-subtle);
  padding-top: 6px;
  margin-top: 2px;
  color: var(--text-primary);
  font-weight: 700;
}

.text-primary-val {
  color: var(--accent-primary, #059669);
  font-size: 14px;
}

@media (max-width: 480px) {
  .party-totals-card {
    max-width: 100%;
  }
}
</style>

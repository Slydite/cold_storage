<script setup lang="ts">
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Download } from 'lucide-vue-next'
import { formatCurrency, formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { RentRunOutput } from '../../api/billing'

interface Props {
  visible: boolean
  rentRun: RentRunOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
}>()

const handleClose = () => {
  emit('update:visible', false)
}

const handleExportLines = () => {
  if (!props.rentRun || !props.rentRun.lines) return
  const headers = [
    'Lot No.',
    'Commodity',
    'Customer / Party',
    'Quantity',
    'Weight Category',
    'Days Stored',
    'Monthly Rate (₹)',
    'Line Amount (₹)'
  ]
  const rows = props.rentRun.lines.map((line) => [
    line.lot_number,
    line.commodity_name,
    line.party_name,
    line.qty,
    line.weight_category,
    line.days_stored,
    formatCurrency(Number(line.rate_per_bag_per_month)),
    formatCurrency(Number(line.amount))
  ])
  exportToCsv(`rent_run_${props.rentRun.id}_lines.csv`, headers, rows)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="props.rentRun ? `Rent Run Details #${props.rentRun.id}` : 'Rent Run Details'"
    :style="{ width: '820px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div v-if="props.rentRun" class="detail-dialog-body">
      <!-- Summary Bar -->
      <div class="summary-card">
        <div class="summary-item">
          <span class="summary-label">Billing Period</span>
          <span class="summary-val">{{ props.rentRun.period_start }} &rarr; {{ props.rentRun.period_end }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Execution Date</span>
          <span class="summary-val">{{ props.rentRun.run_date }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Status</span>
          <span
            class="status-pill"
            :class="{
              success: props.rentRun.status === 'POSTED',
              warning: props.rentRun.status === 'DRAFT',
              danger: props.rentRun.status === 'CANCELLED'
            }"
          >
            {{ props.rentRun.status }}
          </span>
        </div>
        <div class="summary-item highlight-summary">
          <span class="summary-label">Total Amount</span>
          <span class="summary-val total-val">{{ formatCurrency(Number(props.rentRun.total_amount)) }}</span>
        </div>
      </div>

      <!-- Lines Section -->
      <div class="lines-header">
        <h4 class="lines-title">Line Items Billed ({{ props.rentRun.lines ? props.rentRun.lines.length : 0 }})</h4>
        <button class="btn-outlined btn-sm" type="button" @click="handleExportLines">
          <Download :size="14" />
          <span>Export Lines CSV</span>
        </button>
      </div>

      <div class="table-card">
        <DataTable
          :value="props.rentRun.lines || []"
          size="small"
          stripedRows
          responsiveLayout="scroll"
          paginator
          :rows="8"
        >
          <Column field="lot_number" header="Lot No.">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number }}</span>
            </template>
          </Column>

          <Column field="commodity_name" header="Commodity" />

          <Column field="party_name" header="Party / Customer">
            <template #body="{ data }">
              <span class="party-name">{{ data.party_name }}</span>
            </template>
          </Column>

          <Column field="qty" header="Qty">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.qty, 0) }}</span>
            </template>
          </Column>

          <Column field="weight_category" header="Category" />

          <Column field="days_stored" header="Days">
            <template #body="{ data }">
              <span class="num-val">{{ data.days_stored }}</span>
            </template>
          </Column>

          <Column field="rate_per_bag_per_month" header="Monthly Rate">
            <template #body="{ data }">
              <span class="num-val">{{ formatCurrency(Number(data.rate_per_bag_per_month)) }}</span>
            </template>
          </Column>

          <Column field="amount" header="Amount (₹)">
            <template #body="{ data }">
              <span class="num-val line-amount">{{ formatCurrency(Number(data.amount)) }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-actions">
        <button class="btn-outlined" type="button" @click="handleClose">Close</button>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.detail-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

.summary-card {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.summary-val {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.total-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent-primary);
}

.lines-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.lines-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.line-amount {
  font-weight: 700;
  color: var(--text-primary);
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
}

@media (max-width: 640px) {
  .summary-card {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

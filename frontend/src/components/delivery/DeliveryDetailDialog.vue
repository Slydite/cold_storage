<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Download, Printer } from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { DeliveryNoteOutput } from '../../api/delivery'

interface Props {
  visible: boolean
  deliveryNote: DeliveryNoteOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
}>()

const handleClose = () => {
  emit('update:visible', false)
}

const totalQty = computed(() => {
  if (!props.deliveryNote?.lines) return 0
  return props.deliveryNote.lines.reduce((sum, line) => sum + (line.qty || 0), 0)
})

const handleExportLines = () => {
  if (!props.deliveryNote || !props.deliveryNote.lines) return
  const headers = ['Lot No.', 'Commodity', 'Qty', 'Balance After']
  const rows = props.deliveryNote.lines.map((line) => [
    line.lot_number || '—',
    line.commodity_name || '—',
    line.qty,
    line.balance_after !== null && line.balance_after !== undefined ? line.balance_after : '—'
  ])
  exportToCsv(`delivery_${props.deliveryNote.dn_number}_lines.csv`, headers, rows)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="props.deliveryNote ? `Delivery Note Details - ${props.deliveryNote.dn_number}` : 'Delivery Note Details'"
    :style="{ width: '820px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div v-if="props.deliveryNote" class="detail-dialog-body">
      <!-- Summary / Header Grid -->
      <div class="info-card">
        <div class="info-item">
          <span class="info-label">DN Number</span>
          <span class="info-val code-link">{{ props.deliveryNote.dn_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Dispatch Date</span>
          <span class="info-val">{{ props.deliveryNote.dispatch_date || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Status</span>
          <div>
            <span
              class="status-pill"
              :class="{
                success: props.deliveryNote.status === 'POSTED',
                warning: props.deliveryNote.status === 'DRAFT',
                danger: props.deliveryNote.status === 'CANCELLED'
              }"
            >
              {{ props.deliveryNote.status || '—' }}
            </span>
          </div>
        </div>
        <div class="info-item">
          <span class="info-label">Party</span>
          <span class="info-val party-name">
            {{ props.deliveryNote.party_name ? `${props.deliveryNote.party_name}${props.deliveryNote.party_code ? ` (${props.deliveryNote.party_code})` : ''}` : '—' }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">Vehicle No.</span>
          <span class="info-val">{{ props.deliveryNote.vehicle_number || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Driver Name</span>
          <span class="info-val">{{ props.deliveryNote.driver_name || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Transporter</span>
          <span class="info-val">{{ props.deliveryNote.transporter || '—' }}</span>
        </div>
        <div class="info-item highlight-summary">
          <span class="info-label">Total Qty</span>
          <span class="info-val total-val num-val">{{ formatQty(totalQty, 0) }}</span>
        </div>
      </div>

      <!-- Remarks if present -->
      <div v-if="props.deliveryNote.remarks" class="remarks-box">
        <span class="info-label">Remarks:</span>
        <span class="remarks-text">{{ props.deliveryNote.remarks }}</span>
      </div>

      <!-- Line Items Section -->
      <div class="lines-header">
        <h4 class="lines-title">Dispatched Items ({{ props.deliveryNote.lines ? props.deliveryNote.lines.length : 0 }})</h4>
        <button class="btn-outlined btn-sm" type="button" @click="handleExportLines">
          <Download :size="14" />
          <span>Export CSV</span>
        </button>
      </div>

      <div class="table-card">
        <DataTable
          :value="props.deliveryNote.lines || []"
          size="small"
          stripedRows
          responsiveLayout="scroll"
          paginator
          :rows="8"
        >
          <Column field="lot_number" header="Lot No.">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number || '—' }}</span>
            </template>
          </Column>

          <Column field="commodity_name" header="Commodity">
            <template #body="{ data }">
              <span>{{ data.commodity_name || '—' }}</span>
            </template>
          </Column>

          <Column field="qty" header="Qty">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.qty, 0) }}</span>
            </template>
          </Column>

          <Column header="Balance After">
            <template #body="{ data }">
              <span class="num-val">
                {{ data.balance_after !== null && data.balance_after !== undefined ? formatQty(data.balance_after, 0) : '—' }}
              </span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="pdf-action-group">
          <a
            v-if="props.deliveryNote"
            :href="`/api/delivery-notes/${props.deliveryNote.id}/pdf/`"
            target="_blank"
            rel="noopener"
            class="btn-primary"
            title="PDF"
            aria-label="PDF"
          >
            <Printer :size="15" />
            <span>PDF</span>
          </a>
        </div>
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

.info-card {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px 16px;
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
  font-size: 15px;
  font-weight: 700;
  color: var(--accent-primary);
}

.remarks-box {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  display: flex;
  gap: 8px;
}

.remarks-text {
  color: var(--text-primary);
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

@media (max-width: 640px) {
  .info-card {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

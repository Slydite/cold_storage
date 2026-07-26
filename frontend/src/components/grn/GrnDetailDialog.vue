<script setup lang="ts">
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Download, Printer } from 'lucide-vue-next'
import { formatCurrency, formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { GrnOutput } from '../../api/grn'

interface Props {
  visible: boolean
  grn: GrnOutput | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
}>()

const handleClose = () => {
  emit('update:visible', false)
}

const handleExportLots = () => {
  if (!props.grn || !props.grn.lots) return
  const headers = [
    'Commodity',
    'Lot No.',
    'Chamber',
    'Floor',
    'Initial Qty',
    'Remaining Qty',
    'Unit Weight',
    'Special Remarks'
  ]
  const rows = props.grn.lots.map((lot) => [
    lot.commodity_name || '—',
    lot.lot_number || '—',
    lot.chamber_name || lot.chamber || '—',
    lot.floor_name || lot.floor || '—',
    lot.initial_qty,
    lot.remaining_qty,
    lot.unit_weight ? `${lot.unit_weight} kg` : '—',
    lot.special_remarks || '—'
  ])
  exportToCsv(`grn_${props.grn.grn_number}_lots.csv`, headers, rows)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="props.grn ? `GRN Details - ${props.grn.grn_number}` : 'GRN Details'"
    :style="{ width: '880px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div v-if="props.grn" class="detail-dialog-body">
      <!-- Header Info Grid -->
      <div class="info-card">
        <div class="info-item">
          <span class="info-label">GRN Number</span>
          <span class="info-val code-link">{{ props.grn.grn_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Receipt Date</span>
          <span class="info-val">{{ props.grn.receipt_date || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Status</span>
          <div>
            <span
              class="status-pill"
              :class="{
                success: props.grn.status === 'POSTED',
                warning: props.grn.status === 'DRAFT',
                danger: props.grn.status === 'CANCELLED'
              }"
            >
              {{ props.grn.status || '—' }}
            </span>
          </div>
        </div>
        <div class="info-item">
          <span class="info-label">Party</span>
          <span class="info-val party-name">
            {{ props.grn.party_name ? `${props.grn.party_name}${props.grn.party_code ? ` (${props.grn.party_code})` : ''}` : '—' }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">Vehicle No.</span>
          <span class="info-val">{{ props.grn.vehicle_number || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Driver Name</span>
          <span class="info-val">{{ props.grn.driver_name || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Transporter</span>
          <span class="info-val">{{ props.grn.transporter || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Bill No.</span>
          <span class="info-val">{{ props.grn.bill_no || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Bilty No.</span>
          <span class="info-val">{{ props.grn.bilty_no || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Inward Time</span>
          <span class="info-val">{{ props.grn.inward_time || '—' }}</span>
        </div>
      </div>

      <!-- Charges Block -->
      <div class="charges-card">
        <h4 class="section-subtitle">Rates & Charges</h4>
        <div class="charges-grid">
          <div class="info-item">
            <span class="info-label">Preservation Rate</span>
            <span class="info-val num-val">
              {{ props.grn.preservation_rate_per_bag_per_month ? formatCurrency(Number(props.grn.preservation_rate_per_bag_per_month)) + ' / bag / mo' : '—' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">Loading/Unloading Rate</span>
            <span class="info-val num-val">
              {{ props.grn.loading_unloading_rate_per_bag ? formatCurrency(Number(props.grn.loading_unloading_rate_per_bag)) + ' / bag' : '—' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">Loading Charge</span>
            <span class="info-val num-val">
              {{ props.grn.loading_charge ? formatCurrency(Number(props.grn.loading_charge)) : '—' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Remarks if present -->
      <div v-if="props.grn.remarks" class="remarks-box">
        <span class="info-label">Remarks:</span>
        <span class="remarks-text">{{ props.grn.remarks }}</span>
      </div>

      <!-- Lots Section -->
      <div class="lines-header">
        <h4 class="lines-title">Inward Lots ({{ props.grn.lots ? props.grn.lots.length : 0 }})</h4>
        <button class="btn-outlined btn-sm" type="button" @click="handleExportLots">
          <Download :size="14" />
          <span>Export CSV</span>
        </button>
      </div>

      <div class="table-card">
        <DataTable
          :value="props.grn.lots || []"
          size="small"
          stripedRows
          responsiveLayout="scroll"
          paginator
          :rows="8"
        >
          <Column field="commodity_name" header="Commodity">
            <template #body="{ data }">
              <span>{{ data.commodity_name || '—' }}</span>
            </template>
          </Column>

          <Column field="lot_number" header="Lot No.">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number || '—' }}</span>
            </template>
          </Column>

          <Column header="Chamber">
            <template #body="{ data }">
              <span>{{ data.chamber_name || data.chamber || '—' }}</span>
            </template>
          </Column>

          <Column header="Floor">
            <template #body="{ data }">
              <span>{{ data.floor_name || data.floor || '—' }}</span>
            </template>
          </Column>

          <Column field="initial_qty" header="Initial Qty">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.initial_qty, 0) }}</span>
            </template>
          </Column>

          <Column field="remaining_qty" header="Remaining">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.remaining_qty, 0) }}</span>
            </template>
          </Column>

          <Column field="unit_weight" header="Unit Wt">
            <template #body="{ data }">
              <span>{{ data.unit_weight ? `${data.unit_weight} kg` : '—' }}</span>
            </template>
          </Column>

          <Column field="special_remarks" header="Remarks">
            <template #body="{ data }">
              <span>{{ data.special_remarks || '—' }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="pdf-action-group">
          <a
            v-if="props.grn"
            :href="`/api/grns/${props.grn.id}/pdf/`"
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

.charges-card {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-subtitle {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.charges-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
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
  .charges-grid {
    grid-template-columns: repeat(1, 1fr);
  }
}
</style>

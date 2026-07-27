<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { Printer } from 'lucide-vue-next'
import { formatCurrency, formatQty } from '../../utils/format'
import { downloadPdf } from '../../utils/downloadPdf'
import { exportToCsv } from '../../utils/csvExport'
import type { GrnOutput } from '../../api/grn'

const props = defineProps<{
  visible: boolean
  grn: GrnOutput | null
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
}>()

const toast = useToast()
const { t } = useI18n()
const downloadingPdf = ref(false)

async function handleDownloadPdf() {
  if (!props.grn) return
  downloadingPdf.value = true
  try {
    await downloadPdf(`/api/grns/${props.grn.id}/pdf/`, `${props.grn.grn_number}.pdf`)
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

function handleExportLotsCsv() {
  if (!props.grn || !props.grn.lots) return
  const headers = [
    t('inventory.lotNo'),
    t('grn.commodityProduct'),
    t('inventory.location'),
    t('common.quantity'),
    t('inventory.remainingQty'),
    t('common.unit'),
    t('common.weight'),
    t('common.rate')
  ]
  const rows = props.grn.lots.map((lot) => [
    lot.lot_number,
    lot.commodity_name || '-',
    lot.location_display || '-',
    lot.initial_qty,
    lot.remaining_qty,
    lot.commodity_unit || 'Bags',
    lot.unit_weight || '-',
    lot.rent_rate_per_unit || '-'
  ])
  exportToCsv(`${props.grn.grn_number}_lots.csv`, headers, rows)
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="(val) => emit('update:visible', val)"
    modal
    :header="grn ? t('grn.detailsHeader', { number: grn.grn_number }) : t('grn.details')"
    :style="{ width: '800px', maxWidth: '95vw' }"
  >
    <div v-if="grn" class="grn-detail-content">
      <!-- Status Tag -->
      <div class="detail-header-status">
        <Tag
          :value="t(`status.${(grn.status || 'DRAFT').toLowerCase()}`)"
          :severity="grn.status === 'POSTED' ? 'success' : grn.status === 'CANCELLED' ? 'danger' : 'warn'"
        />
        <button
          class="btn-outlined btn-sm"
          type="button"
          :disabled="downloadingPdf"
          @click="handleDownloadPdf"
        >
          <Printer :size="15" />
          <span>PDF</span>
        </button>
      </div>

      <!-- Main Info Meta Grid -->
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">{{ t('grn.grnNumber') }}</span>
          <strong class="meta-value">{{ grn.grn_number }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('common.date') }}</span>
          <span class="meta-value">{{ grn.receipt_date }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('grn.party') }}</span>
          <strong class="meta-value">{{ grn.party_name }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('grn.vehicle') }}</span>
          <span class="meta-value">{{ grn.vehicle_number || '-' }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('grn.driverName') }}</span>
          <span class="meta-value">{{ grn.driver_name || '-' }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('grn.loadingUnloadingCharge') }}</span>
          <span class="meta-value">
            {{ grn.loading_charge ? formatCurrency(Number(grn.loading_charge)) : '-' }}
          </span>
        </div>
      </div>

      <div v-if="grn.remarks" class="remarks-box">
        <strong>{{ t('common.remarks') }}:</strong> {{ grn.remarks }}
      </div>

      <!-- Inward Lots Table -->
      <div class="lots-section">
        <div class="lots-header">
          <h4 class="section-title">
            {{ t('grn.inwardLots', { count: grn.lots ? grn.lots.length : 0 }) }}
          </h4>
          <button
            v-if="grn.lots && grn.lots.length > 0"
            class="btn-outlined btn-sm"
            type="button"
            @click="handleExportLotsCsv"
          >
            {{ t('grn.exportLotsCsv') }}
          </button>
        </div>

        <DataTable
          :value="grn.lots || []"
          size="small"
          stripedRows
          responsiveLayout="scroll"
          class="custom-datatable"
        >
          <Column field="lot_number" :header="t('inventory.lotNo')">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number }}</span>
            </template>
          </Column>

          <Column field="commodity_name" :header="t('grn.commodityProduct')" />

          <Column :header="t('inventory.location')">
            <template #body="{ data }">
              <span>{{ data.location_display || [data.chamber_name, data.floor_name, data.block_name].filter(Boolean).join(' / ') || '-' }}</span>
            </template>
          </Column>

          <Column field="initial_qty" :header="t('inventory.inQty')">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.initial_qty, 0) }}</span>
            </template>
          </Column>

          <Column field="remaining_qty" :header="t('inventory.remainingQty')">
            <template #body="{ data }">
              <strong class="num-val">{{ formatQty(data.remaining_qty, 0) }}</strong>
            </template>
          </Column>

          <Column field="commodity_unit" :header="t('common.unit')" />

          <Column field="unit_weight" :header="t('common.weight') + ' (MT)'">
            <template #body="{ data }">
              <span class="num-val">{{ data.unit_weight || '-' }}</span>
            </template>
          </Column>

          <Column field="rent_rate_per_unit" :header="t('common.rate')">
            <template #body="{ data }">
              <span class="num-val">{{ data.rent_rate_per_unit ? formatCurrency(Number(data.rent_rate_per_unit)) : '-' }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.grn-detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 8px;
}

.detail-header-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.meta-value {
  font-size: 13.5px;
  color: var(--text-primary);
}

.remarks-box {
  background: var(--accent-primary-light);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-primary);
}

.lots-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lots-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-sm {
  padding: 5px 10px;
  font-size: 12px;
}

@media (max-width: 640px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>

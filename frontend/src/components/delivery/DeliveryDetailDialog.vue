<script setup lang="ts">
import { ref, computed, toRef } from 'vue'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { Download, Printer, Mail } from 'lucide-vue-next'
import { formatQty, formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { downloadPdf } from '../../utils/downloadPdf'
import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
import { emailDeliveryNote } from '../../api/delivery'
import { EMAIL_TO_CLIENT_ENABLED } from '../../config/features'
import type { DeliveryNoteOutput, DeliveryLineOutput } from '../../api/delivery'

interface Props {
  visible: boolean
  deliveryNote: DeliveryNoteOutput | null
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

const handleClose = () => {
  emit('update:visible', false)
}

const { t } = useI18n()
const toast = useToast()
const downloadingId = ref<number | null>(null)
const emailing = ref(false)

function formatDateTime(d?: string | null): string {
  if (!d) return t('common.never')
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d || ''
  }
}

async function handleEmailToClient() {
  if (!props.deliveryNote) return
  emailing.value = true
  try {
    await emailDeliveryNote(props.deliveryNote.id)
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


async function handleDownloadPdf(id: number, docNumber: string) {
  downloadingId.value = id
  try {
    await downloadPdf(`/api/delivery-notes/${id}/pdf/`, `${docNumber}.pdf`)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.pdfFailed'),
      detail: err instanceof Error ? err.message : t('delivery.couldNotGeneratePdf'),
      life: 5000
    })
  } finally {
    downloadingId.value = null
  }
}

const totalQty = computed(() => {
  if (!props.deliveryNote?.lines) return 0
  return props.deliveryNote.lines.reduce((sum, line) => sum + (line.qty || 0), 0)
})

function getBalanceBefore(line: DeliveryLineOutput): number | null {
  if (line.balance_after === null || line.balance_after === undefined) return null
  if (line.qty === null || line.qty === undefined) return null
  return Number(line.balance_after) + Number(line.qty)
}

const handleExportLines = () => {
  if (!props.deliveryNote || !props.deliveryNote.lines) return
  const headers = [t('inventory.lotNo'), t('common.commodity'), t('delivery.balanceBefore'), t('common.quantity'), t('delivery.balanceAfter')]
  const rows = props.deliveryNote.lines.map((line) => {
    const balBefore = getBalanceBefore(line)
    return [
      line.lot_number || '—',
      line.commodity_name || '—',
      balBefore !== null ? balBefore : '—',
      line.qty,
      line.balance_after !== null && line.balance_after !== undefined ? line.balance_after : '—'
    ]
  })
  exportToCsv(`delivery_${props.deliveryNote.dn_number}_lines.csv`, headers, rows)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="props.deliveryNote ? t('delivery.detailsHeader', { number: props.deliveryNote.dn_number }) : t('delivery.details')"
    :style="{ width: '820px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div v-if="props.deliveryNote" class="detail-dialog-body">
      <!-- Summary / Header Grid -->
      <div class="info-card">
        <div class="info-item">
          <span class="info-label">{{ t('delivery.dnNumber') }}</span>
          <span class="info-val code-link">{{ props.deliveryNote.dn_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('delivery.dispatchDate') }}</span>
          <span class="info-val">{{ props.deliveryNote.dispatch_date || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('common.status') }}</span>
          <div>
            <span
              class="status-pill"
              :class="{
                success: props.deliveryNote.status === 'POSTED',
                warning: props.deliveryNote.status === 'DRAFT',
                danger: props.deliveryNote.status === 'CANCELLED'
              }"
            >
              {{ props.deliveryNote.status ? t(`status.${props.deliveryNote.status}`) : '—' }}
            </span>
          </div>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('grn.party') }}</span>
          <span class="info-val party-name">
            {{ props.deliveryNote.party_name ? `${props.deliveryNote.party_name}${props.deliveryNote.party_code ? ` (${props.deliveryNote.party_code})` : ''}` : '—' }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('delivery.vehicleNo') }}</span>
          <span class="info-val">{{ props.deliveryNote.vehicle_number || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('delivery.driverName') }}</span>
          <span class="info-val">{{ props.deliveryNote.driver_name || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('delivery.transporter') }}</span>
          <span class="info-val">{{ props.deliveryNote.transporter || '—' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('common.lastEmailed') }}</span>
          <span class="info-val">{{ formatDateTime(props.deliveryNote.last_emailed_at) }}</span>
        </div>
        <div class="info-item highlight-summary">
          <span class="info-label">{{ t('delivery.totalQty') }}</span>
          <span class="info-val total-val num-val">{{ formatQty(totalQty, 0) }}</span>
        </div>
      </div>

      <!-- Charges Block -->
      <div class="charges-card">
        <h4 class="section-subtitle">{{ t('delivery.loadingUnloadingCharge') }}</h4>
        <div class="charges-grid">
          <div class="info-item">
            <span class="info-label">{{ t('delivery.chargeMode') }}</span>
            <span class="info-val">
              {{ props.deliveryNote.loading_charge_mode === 'PER_UNIT' ? t('chargeMode.perUnit') : t('chargeMode.flat') }}
            </span>
          </div>
          <div v-if="props.deliveryNote.loading_charge_mode === 'PER_UNIT'" class="info-item">
            <span class="info-label">{{ t('delivery.loadingUnloadingRatePerUnit') }}</span>
            <span class="info-val num-val">
              {{ props.deliveryNote.loading_unloading_rate_per_unit ? `${formatCurrency(Number(props.deliveryNote.loading_unloading_rate_per_unit))} / ${t('common.unit').toLowerCase()}` : '—' }}
            </span>
          </div>
          <div v-else class="info-item">
            <span class="info-label">{{ t('delivery.flatLoadingUnloadingCharge') }}</span>
            <span class="info-val num-val">
              {{ props.deliveryNote.loading_charge ? formatCurrency(Number(props.deliveryNote.loading_charge)) : '—' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('delivery.computedLoadingUnloadingCharge') }}</span>
            <span class="info-val num-val highlight-val">
              {{ props.deliveryNote.computed_loading_charge ? formatCurrency(Number(props.deliveryNote.computed_loading_charge)) : '—' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Remarks if present -->
      <div v-if="props.deliveryNote.remarks" class="remarks-box">
        <span class="info-label">{{ t('delivery.remarks') }}:</span>
        <span class="remarks-text">{{ props.deliveryNote.remarks }}</span>
      </div>

      <!-- Line Items Section -->
      <div class="lines-header">
        <h4 class="lines-title">{{ t('delivery.dispatchedItems', { count: props.deliveryNote.lines ? props.deliveryNote.lines.length : 0 }) }}</h4>
        <button class="btn-outlined btn-sm" type="button" @click="handleExportLines">
          <Download :size="14" />
          <span>{{ t('delivery.exportLinesCsv') }}</span>
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
          <Column field="lot_number" :header="t('inventory.lotNo')">
            <template #body="{ data }">
              <span class="code-link">{{ data.lot_number || '—' }}</span>
            </template>
          </Column>

          <Column field="commodity_name" :header="t('common.commodity')">
            <template #body="{ data }">
              <span>{{ data.commodity_name || '—' }}</span>
            </template>
          </Column>

          <Column :header="t('delivery.balanceBefore')">
            <template #body="{ data }">
              <span class="num-val">
                {{ getBalanceBefore(data) !== null ? formatQty(getBalanceBefore(data)!, 0) : '—' }}
              </span>
            </template>
          </Column>

          <Column field="qty" :header="t('common.quantity')">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.qty, 0) }}</span>
            </template>
          </Column>

          <Column :header="t('delivery.balanceAfter')">
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
          <button
            v-if="props.deliveryNote"
            class="btn-primary"
            type="button"
            title="PDF"
            aria-label="PDF"
            :disabled="downloadingId === props.deliveryNote.id"
            @click="handleDownloadPdf(props.deliveryNote.id, props.deliveryNote.dn_number)"
          >
            <Printer :size="15" />
            <span>PDF</span>
          </button>
          <button
            v-if="EMAIL_TO_CLIENT_ENABLED && props.deliveryNote"
            class="btn-outlined"
            type="button"
            :disabled="!props.deliveryNote.party_email || emailing"
            :title="!props.deliveryNote.party_email ? t('common.noClientEmailTooltip') : t('common.emailToClient')"
            @click="handleEmailToClient"
          >
            <Mail :size="15" />
            <span>{{ emailing ? t('common.loading') : t('common.emailToClient') }}</span>
          </button>
        </div>
        <button class="btn-outlined" type="button" @click="handleClose">{{ t('common.close') }}</button>
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

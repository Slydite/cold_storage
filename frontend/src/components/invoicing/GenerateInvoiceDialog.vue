<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { AlertCircle, FileSpreadsheet, FileCheck } from 'lucide-vue-next'
import { fetchRentRuns, fetchRentRun, type RentRunOutput } from '../../api/billing'
import { useGenerateInvoices } from '../../composables/useInvoices'
import { formatCurrency } from '../../utils/format'
import type { InvoiceOutput } from '../../api/invoicing'

interface Props {
  visible: boolean
  facilityId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: [createdInvoices: InvoiceOutput[]]
  error: [message: string]
}>()

const selectedRentRunId = ref<number | null>(null)
const rentRuns = ref<RentRunOutput[]>([])
const selectedRunDetail = ref<RentRunOutput | null>(null)
const loadingRentRuns = ref(false)
const loadingRunDetail = ref(false)
const fetchError = ref<string | null>(null)

const generateMutation = useGenerateInvoices()

const postedRentRunsOptions = computed(() => {
  return rentRuns.value
    .filter((rr) => rr.status === 'POSTED')
    .map((rr) => ({
      label: `Rent Run #${rr.id}: ${rr.period_start} to ${rr.period_end} (${formatCurrency(Number(rr.total_amount || 0))})`,
      value: rr.id
    }))
})

const partySummaries = computed(() => {
  if (!selectedRunDetail.value || !selectedRunDetail.value.lines) return []
  const map = new Map<number, { party_id: number; party_name: string; lot_count: number; total_rent: number }>()

  for (const line of selectedRunDetail.value.lines) {
    const pId = line.party_id
    const existing = map.get(pId)
    const amt = Number(line.amount || 0)
    if (existing) {
      existing.lot_count += 1
      existing.total_rent += amt
    } else {
      map.set(pId, {
        party_id: pId,
        party_name: line.party_name || `Party #${pId}`,
        lot_count: 1,
        total_rent: amt
      })
    }
  }
  return Array.from(map.values())
})

async function loadRentRuns() {
  if (!props.facilityId) return
  loadingRentRuns.value = true
  fetchError.value = null
  selectedRunDetail.value = null
  try {
    const list = await fetchRentRuns({ facilityId: props.facilityId })
    rentRuns.value = list
    if (postedRentRunsOptions.value.length > 0 && postedRentRunsOptions.value[0]) {
      selectedRentRunId.value = postedRentRunsOptions.value[0].value
    } else {
      selectedRentRunId.value = null
    }
  } catch (err) {
    fetchError.value = err instanceof Error ? err.message : 'Failed to fetch rent runs'
  } finally {
    loadingRentRuns.value = false
  }
}

async function loadRunDetail(id: number | null) {
  if (!id) {
    selectedRunDetail.value = null
    return
  }
  loadingRunDetail.value = true
  try {
    const detail = await fetchRentRun(id)
    selectedRunDetail.value = detail
  } catch (err) {
    fetchError.value = err instanceof Error ? err.message : 'Failed to load rent run detail'
  } finally {
    loadingRunDetail.value = false
  }
}

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      loadRentRuns()
    }
  }
)

watch(selectedRentRunId, (newId) => {
  if (newId) {
    loadRunDetail(newId)
  } else {
    selectedRunDetail.value = null
  }
})

async function handleSubmit() {
  if (!props.facilityId || !selectedRentRunId.value) return
  if (partySummaries.value.length === 0) return

  try {
    const createdInvoices = await generateMutation.mutateAsync({
      facility_id: props.facilityId,
      rent_run_id: selectedRentRunId.value
    })
    emit('success', createdInvoices)
    emit('update:visible', false)
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to generate invoices'
    emit('error', message)
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    header="Generate Invoices from Rent Run"
    :style="{ width: '560px', maxWidth: '95vw' }"
  >
    <div class="generate-dialog-body">
      <p class="dialog-desc">
        Select a posted rent run to preview and generate official GST tax invoices. One invoice will be created for each party included in the run.
      </p>

      <div v-if="loadingRentRuns" class="loading-box">
        <Skeleton height="40px" />
      </div>

      <div v-else-if="fetchError" class="error-box">
        <AlertCircle :size="18" class="error-icon" />
        <span>{{ fetchError }}</span>
      </div>

      <div v-else-if="postedRentRunsOptions.length === 0" class="empty-box">
        <FileSpreadsheet :size="32" class="empty-icon" />
        <p class="empty-title">No Posted Rent Runs Available</p>
        <p class="empty-sub">
          Invoices can only be generated from rent runs that are already in <strong>POSTED</strong> status. Please complete and post a rent run first.
        </p>
      </div>

      <form v-else @submit.prevent="handleSubmit" class="generate-form">
        <div class="form-field">
          <label for="rent-run-select">Posted Rent Run <span class="required">*</span></label>
          <Select
            id="rent-run-select"
            v-model="selectedRentRunId"
            :options="postedRentRunsOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Select a posted rent run"
            class="w-full"
          />
        </div>

        <!-- Run Summary & Per-Party Invoices Preview -->
        <div v-if="loadingRunDetail" class="loading-box">
          <Skeleton height="120px" />
        </div>

        <div v-else-if="selectedRunDetail" class="invoice-summary-box">
          <div class="summary-meta-header">
            <div>
              <span class="meta-label">Run Period:</span>
              <span class="meta-val">{{ selectedRunDetail.period_start }} &rarr; {{ selectedRunDetail.period_end }}</span>
            </div>
            <div>
              <span class="meta-label">Total Rent:</span>
              <span class="meta-val highlight-val">{{ formatCurrency(Number(selectedRunDetail.total_amount || 0)) }}</span>
            </div>
          </div>

          <div v-if="partySummaries.length > 0" class="party-breakdown-container">
            <h5 class="breakdown-title">
              Invoices to be Generated ({{ partySummaries.length }} Party/Parties)
            </h5>

            <DataTable :value="partySummaries" size="small" stripedRows responsiveLayout="scroll">
              <Column field="party_name" header="Party / Customer">
                <template #body="{ data }">
                  <span class="party-name">{{ data.party_name }}</span>
                </template>
              </Column>
              <Column field="lot_count" header="Lots Billed">
                <template #body="{ data }">
                  <span class="num-val">{{ data.lot_count }}</span>
                </template>
              </Column>
              <Column field="total_rent" header="Rent Subtotal (₹)">
                <template #body="{ data }">
                  <span class="num-val font-bold">{{ formatCurrency(data.total_rent) }}</span>
                </template>
              </Column>
            </DataTable>

            <p class="summary-note">
              <FileCheck :size="14" class="note-icon" />
              <span>One official GST invoice will be issued for each party listed above.</span>
            </p>
          </div>

          <div v-else class="empty-lines-warning">
            <AlertCircle :size="18" class="warning-icon" />
            <span>This rent run has no billed line items. Invoices cannot be generated.</span>
          </div>
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="emit('update:visible', false)"
            :disabled="generateMutation.isPending.value"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="!selectedRentRunId || loadingRunDetail || partySummaries.length === 0 || generateMutation.isPending.value"
          >
            {{ generateMutation.isPending.value ? 'Generating...' : `Generate ${partySummaries.length} Invoice(s)` }}
          </button>
        </div>
      </form>
    </div>
  </Dialog>
</template>

<style scoped>
.generate-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.dialog-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.loading-box {
  padding: 8px 0;
}

.error-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--status-danger-bg);
  color: var(--status-danger-color);
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.error-icon {
  flex-shrink: 0;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 24px 16px;
  background: var(--bg-page);
  border: 1px dashed var(--border-subtle);
  border-radius: 12px;
  gap: 8px;
}

.empty-icon {
  color: var(--text-secondary);
}

.empty-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.empty-sub {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.generate-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.invoice-summary-box {
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-meta-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
  font-size: 12.5px;
}

.meta-label {
  color: var(--text-secondary);
  margin-right: 6px;
}

.meta-val {
  font-weight: 600;
  color: var(--text-primary);
}

.highlight-val {
  color: var(--accent-primary);
  font-weight: 700;
}

.party-breakdown-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.breakdown-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.note-icon {
  color: var(--status-success-color);
}

.empty-lines-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--status-warning-bg);
  color: var(--status-warning-color);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12.5px;
}

.font-bold {
  font-weight: 700;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

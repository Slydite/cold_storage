<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { AlertCircle, FileSpreadsheet } from 'lucide-vue-next'
import { fetchRentRuns, type RentRunOutput } from '../../api/billing'
import { useGenerateInvoices } from '../../composables/useInvoices'
import { formatCurrency } from '../../utils/format'

interface Props {
  visible: boolean
  facilityId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  success: [createdCount: number, partyNames: string[]]
  error: [message: string]
}>()

const selectedRentRunId = ref<number | null>(null)
const rentRuns = ref<RentRunOutput[]>([])
const loadingRentRuns = ref(false)
const fetchError = ref<string | null>(null)

const generateMutation = useGenerateInvoices()

const postedRentRunsOptions = computed(() => {
  return rentRuns.value
    .filter((rr) => rr.status === 'POSTED')
    .map((rr) => ({
      label: `Run #${rr.id}: ${rr.period_start} to ${rr.period_end} (${formatCurrency(Number(rr.total_amount || 0))})`,
      value: rr.id
    }))
})

async function loadRentRuns() {
  if (!props.facilityId) return
  loadingRentRuns.value = true
  fetchError.value = null
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

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      loadRentRuns()
    }
  }
)

async function handleSubmit() {
  if (!props.facilityId || !selectedRentRunId.value) return

  try {
    const createdInvoices = await generateMutation.mutateAsync({
      facility_id: props.facilityId,
      rent_run_id: selectedRentRunId.value
    })
    const partyNames = Array.from(new Set(createdInvoices.map((inv) => inv.party_name).filter(Boolean)))
    emit('success', createdInvoices.length, partyNames)
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
    :style="{ width: '480px' }"
  >
    <div class="generate-dialog-body">
      <p class="dialog-desc">
        Select a posted rent run to generate official GST invoices. One invoice will be created for each party included in the run.
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
            :disabled="!selectedRentRunId || generateMutation.isPending.value"
          >
            {{ generateMutation.isPending.value ? 'Generating...' : 'Generate Invoices' }}
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

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

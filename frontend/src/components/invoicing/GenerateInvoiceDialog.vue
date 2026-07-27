<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { useI18n } from 'vue-i18n'
import { FileCheck, AlertCircle, RefreshCw, Inbox, Loader2 } from 'lucide-vue-next'
import { useQuery } from '@tanstack/vue-query'
import { fetchParties } from '../../api/party'
import { useGenerateInvoices, useInvoicePreview } from '../../composables/useInvoices'
import PartyPreviewSection from './PartyPreviewSection.vue'
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

const { t } = useI18n()
const selectedPartyId = ref<number | null>(null)

const facilityIdRef = computed(() => props.facilityId)
const partyIdRef = computed(() => selectedPartyId.value)

const generateMutation = useGenerateInvoices()

const partiesQuery = useQuery({
  queryKey: computed(() => ['parties', props.facilityId]),
  queryFn: () => fetchParties({ facilityId: props.facilityId! }),
  enabled: computed(() => props.facilityId !== undefined)
})

const partyOptions = computed(() => {
  const options: Array<{ label: string; value: number | null }> = [
    { label: t('invoicing.allPartiesUninvoiced'), value: null }
  ]
  if (partiesQuery.data.value) {
    options.push(
      ...partiesQuery.data.value.map((p) => ({
        label: `${p.name} (${p.code})`,
        value: p.id
      }))
    )
  }
  return options
})

const previewQuery = useInvoicePreview(facilityIdRef, partyIdRef)

const previewData = computed(() => previewQuery.data.value ?? [])
const isLoadingPreview = computed(() => previewQuery.isLoading.value)
const isErrorPreview = computed(() => previewQuery.isError.value)
const errorMessage = computed(() => {
  if (previewQuery.error.value instanceof Error) {
    return previewQuery.error.value.message
  }
  return t('invoicing.failedToLoadPreview')
})
const isEmptyPreview = computed(
  () => !isLoadingPreview.value && !isErrorPreview.value && previewData.value.length === 0
)

const partyCount = computed(() => previewData.value.length)

const isGenerateDisabled = computed(() => {
  return (
    generateMutation.isPending.value ||
    isLoadingPreview.value ||
    isErrorPreview.value ||
    isEmptyPreview.value
  )
})

const generateButtonLabel = computed(() => {
  if (generateMutation.isPending.value) {
    return t('invoicing.generating')
  }
  if (partyCount.value > 0) {
    return t('invoicing.generateCountInvoices', { count: partyCount.value })
  }
  return t('invoicing.generateInvoices')
})

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      selectedPartyId.value = null
    }
  }
)

async function handleSubmit() {
  if (!props.facilityId || isGenerateDisabled.value) return

  try {
    const createdInvoices = await generateMutation.mutateAsync({
      facility_id: props.facilityId,
      party_id: selectedPartyId.value || undefined
    })
    emit('success', createdInvoices)
    emit('update:visible', false)
  } catch (err) {
    const message = err instanceof Error ? err.message : t('invoicing.generationError')
    emit('error', message)
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="t('invoicing.generateDialogHeader')"
    :style="{ width: '850px', maxWidth: '95vw' }"
  >
    <div class="generate-dialog-body">
      <p class="dialog-desc">
        {{ t('invoicing.generateDialogDesc') }}
      </p>

      <form @submit.prevent="handleSubmit" class="generate-form">
        <div class="form-field">
          <label for="party-select">{{ t('invoicing.selectClientParty') }}</label>
          <Select
            id="party-select"
            v-model="selectedPartyId"
            :options="partyOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('invoicing.selectPartyOrAll')"
            :loading="partiesQuery.isLoading.value"
            class="w-full"
          />
        </div>

        <div class="info-callout">
          <FileCheck :size="16" class="callout-icon" />
          <span>{{ t('invoicing.uninvoicedNotice') }}</span>
        </div>

        <!-- Preview Section with Explicit States -->
        <div class="preview-container">
          <h4 class="preview-heading">{{ t('invoicing.invoiceChargesPreview') }}</h4>

          <!-- State 1: Loading State -->
          <div v-if="isLoadingPreview" class="preview-state loading-state">
            <Loader2 :size="24" class="spin-icon text-accent" />
            <span>{{ t('invoicing.calculatingPreview') }}</span>
            <div class="skeleton-box">
              <Skeleton height="32px" class="mb-2" />
              <Skeleton height="80px" />
            </div>
          </div>

          <!-- State 2: Error State -->
          <div v-else-if="isErrorPreview" class="preview-state error-state">
            <AlertCircle :size="32" class="text-danger" />
            <div class="error-content">
              <h5 class="error-title">{{ t('invoicing.failedToLoadPreview') }}</h5>
              <p class="error-message">{{ errorMessage }}</p>
            </div>
            <button type="button" class="btn-outlined btn-sm" @click="previewQuery.refetch()">
              <RefreshCw :size="14" />
              <span>{{ t('common.retry') }}</span>
            </button>
          </div>

          <!-- State 3: Empty State -->
          <div v-else-if="isEmptyPreview" class="preview-state empty-state">
            <Inbox :size="36" class="text-muted" />
            <h5 class="empty-title">{{ t('invoicing.nothingToInvoice') }}</h5>
            <p class="empty-desc">{{ t('invoicing.nothingToInvoiceDesc') }}</p>
          </div>

          <!-- State 4: Loaded State -->
          <div v-else class="preview-list">
            <PartyPreviewSection
              v-for="party in previewData"
              :key="party.party_id"
              :party="party"
            />
          </div>
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="emit('update:visible', false)"
            :disabled="generateMutation.isPending.value"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="isGenerateDisabled"
          >
            {{ generateButtonLabel }}
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

.info-callout {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-subtle);
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.callout-icon {
  color: var(--accent-primary);
  flex-shrink: 0;
}

.w-full {
  width: 100%;
}

.preview-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 14px;
}

.preview-heading {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.preview-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px 16px;
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-page);
  text-align: center;
}

.loading-state {
  color: var(--text-secondary);
  font-size: 13px;
}

.skeleton-box {
  width: 100%;
  max-width: 400px;
  margin-top: 8px;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

.text-accent {
  color: var(--accent-primary);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.error-state {
  border-color: var(--border-danger, #fca5a5);
  background: var(--bg-surface);
}

.text-danger {
  color: var(--status-danger-color);
}

.error-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.error-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.error-message {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin: 0;
}

.btn-sm {
  font-size: 12px;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.empty-state {
  color: var(--text-secondary);
}

.text-muted {
  color: var(--text-secondary);
  opacity: 0.7;
}

.empty-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin: 0;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useFacility } from '../composables/useFacility'
import { useRateCardList } from '../composables/useRateCards'
import { useRentRunList, usePostRentRun, useCancelRentRun } from '../composables/useRentRuns'
import RateCardTable from '../components/billing/RateCardTable.vue'
import RateCardCreateDialog from '../components/billing/RateCardCreateDialog.vue'
import RentRunTable from '../components/billing/RentRunTable.vue'
import RentRunCreateDialog from '../components/billing/RentRunCreateDialog.vue'
import RentRunDetailDialog from '../components/billing/RentRunDetailDialog.vue'
import type { RentRunOutput } from '../api/billing'

const toast = useToast()

const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const rateCardsQuery = useRateCardList(facilityId)
const rentRunsQuery = useRentRunList(facilityId)

const postRentRunMutation = usePostRentRun()
const cancelRentRunMutation = useCancelRentRun()

const isCreateRateCardOpen = ref(false)
const isCreateRentRunOpen = ref(false)
const isRentRunDetailOpen = ref(false)
const selectedRentRun = ref<RentRunOutput | null>(null)

const rateCards = computed(() => rateCardsQuery.data.value || [])
const rentRuns = computed(() => rentRunsQuery.data.value || [])

const isRateCardsLoading = computed(() => loadingFacility.value || rateCardsQuery.isLoading.value)
const isRateCardsError = computed(() => facilityError.value || rateCardsQuery.isError.value)
const rateCardsErrorMsg = computed(() =>
  rateCardsQuery.error.value instanceof Error ? rateCardsQuery.error.value.message : undefined
)

const isRentRunsLoading = computed(() => loadingFacility.value || rentRunsQuery.isLoading.value)
const isRentRunsError = computed(() => facilityError.value || rentRunsQuery.isError.value)
const rentRunsErrorMsg = computed(() =>
  rentRunsQuery.error.value instanceof Error ? rentRunsQuery.error.value.message : undefined
)

const handlePostRentRun = async (id: number) => {
  try {
    const updated = await postRentRunMutation.mutateAsync(id)
    toast.add({
      severity: 'success',
      summary: 'Rent Run Posted',
      detail: `Rent Run #${updated.id} has been posted and finalized.`,
      life: 4000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Post Failed',
      detail: err instanceof Error ? err.message : 'Failed to post rent run',
      life: 5000
    })
  }
}

const handleCancelRentRun = async (id: number) => {
  try {
    const updated = await cancelRentRunMutation.mutateAsync(id)
    toast.add({
      severity: 'info',
      summary: 'Rent Run Cancelled',
      detail: `Rent Run #${updated.id} has been cancelled.`,
      life: 4000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Cancel Failed',
      detail: err instanceof Error ? err.message : 'Failed to cancel rent run',
      life: 5000
    })
  }
}

const handleViewRentRun = (run: RentRunOutput) => {
  selectedRentRun.value = run
  isRentRunDetailOpen.value = true
}

const handleRentRunCreated = (createdRun: RentRunOutput) => {
  selectedRentRun.value = createdRun
  isRentRunDetailOpen.value = true
}

const handleRetryRateCards = () => {
  refetchFacility()
  rateCardsQuery.refetch()
}

const handleRetryRentRuns = () => {
  refetchFacility()
  rentRunsQuery.refetch()
}
</script>

<template>
  <div class="billing-page page-container">
    <ConfirmDialog />

    <!-- Rate Cards Section -->
    <div class="billing-section">
      <div class="section-header">
        <h3 class="section-title">Storage Rate Cards</h3>
        <p class="section-desc">Active rate cards per commodity & weight category used for automated rent calculation.</p>
      </div>

      <RateCardTable
        :rateCards="rateCards"
        :loading="isRateCardsLoading"
        :error="isRateCardsError"
        :errorDetail="rateCardsErrorMsg"
        @openCreate="isCreateRateCardOpen = true"
        @retry="handleRetryRateCards"
      />
    </div>

    <!-- Rent Runs Section -->
    <div class="billing-section">
      <div class="section-header">
        <h3 class="section-title">Rent Calculation & Billing Runs</h3>
        <p class="section-desc">Calculate automated storage charges based on occupied space, bag weight, & duration.</p>
      </div>

      <RentRunTable
        :rentRuns="rentRuns"
        :loading="isRentRunsLoading"
        :error="isRentRunsError"
        :errorDetail="rentRunsErrorMsg"
        @openCreate="isCreateRentRunOpen = true"
        @retry="handleRetryRentRuns"
        @view="handleViewRentRun"
        @post="handlePostRentRun"
        @cancel="handleCancelRentRun"
      />
    </div>

    <!-- Dialogs -->
    <RateCardCreateDialog
      v-model:visible="isCreateRateCardOpen"
      :facilityId="facilityId"
      @created="rateCardsQuery.refetch()"
    />

    <RentRunCreateDialog
      v-model:visible="isCreateRentRunOpen"
      :facilityId="facilityId"
      @created="handleRentRunCreated"
    />

    <RentRunDetailDialog
      v-model:visible="isRentRunDetailOpen"
      :rentRun="selectedRentRun"
    />
  </div>
</template>

<style scoped>
.billing-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.billing-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
}
</style>

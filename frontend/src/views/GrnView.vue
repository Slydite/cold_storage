<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { useToast } from 'primevue/usetoast'
import { useFacility } from '../composables/useFacility'
import { useGrnList, usePostGrn, useCancelGrn } from '../composables/useGrns'
import { useSearchFilter } from '../composables/useSearchFilter'
import { fetchParties } from '../api/party'
import { fetchCommodities } from '../api/commodity'
import GrnListTable from '../components/grn/GrnListTable.vue'
import GrnCreatePanel from '../components/grn/GrnCreatePanel.vue'
import GrnDetailDialog from '../components/grn/GrnDetailDialog.vue'
import type { GrnOutput } from '../api/grn'

const route = useRoute()
const toast = useToast()

const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedChamber = ref('all')
const selectedPeriod = ref('this_month')
const isPanelOpen = ref(false)
const selectedGrn = ref<GrnOutput | null>(null)
const isDetailOpen = ref(false)

const grnsQuery = useGrnList(facilityId)
const postMutation = usePostGrn()
const cancelMutation = useCancelGrn()

const partiesQuery = useQuery({
  queryKey: computed(() => ['parties', facilityId.value]),
  queryFn: () => fetchParties({ facilityId: facilityId.value! }),
  enabled: computed(() => !!facilityId.value)
})

const commoditiesQuery = useQuery({
  queryKey: computed(() => ['commodities', facilityId.value]),
  queryFn: () => fetchCommodities({ facilityId: facilityId.value! }),
  enabled: computed(() => !!facilityId.value)
})

const grnList = computed<GrnOutput[]>(() => grnsQuery.data.value || [])

const { searchQuery, filtered: searchedGrns } = useSearchFilter(grnList, (item, query) =>
  item.grn_number.toLowerCase().includes(query) ||
  (item.party_name ? item.party_name.toLowerCase().includes(query) : false) ||
  (item.vehicle_number ? item.vehicle_number.toLowerCase().includes(query) : false)
)

const filteredGrns = computed(() =>
  searchedGrns.value.filter((item) => selectedChamber.value === 'all' || item.lots?.some((l) => l.chamber === selectedChamber.value))
)

const isListLoading = computed(() => loadingFacility.value || grnsQuery.isLoading.value)
const isListError = computed(() => facilityError.value || grnsQuery.isError.value)
const errorMessage = computed(() => (grnsQuery.error.value instanceof Error ? grnsQuery.error.value.message : undefined))

const handlePost = async (id: number) => {
  try {
    const updated = await postMutation.mutateAsync(id)
    toast.add({ severity: 'success', summary: 'GRN Posted', detail: `GRN ${updated.grn_number} posted successfully.`, life: 3000 })
  } catch (err: unknown) {
    toast.add({ severity: 'error', summary: 'Action Failed', detail: err instanceof Error ? err.message : 'Failed to post GRN', life: 5000 })
  }
}

const handleCancel = async (id: number) => {
  try {
    const updated = await cancelMutation.mutateAsync(id)
    toast.add({ severity: 'warn', summary: 'GRN Cancelled', detail: `GRN ${updated.grn_number} was cancelled.`, life: 3000 })
  } catch (err: unknown) {
    toast.add({ severity: 'error', summary: 'Action Failed', detail: err instanceof Error ? err.message : 'Failed to cancel GRN', life: 5000 })
  }
}

const handleView = (grn: GrnOutput) => {
  selectedGrn.value = grn
  isDetailOpen.value = true
}

const handleRetry = () => {
  refetchFacility()
  grnsQuery.refetch()
}

onMounted(() => {
  if (route.query.action === 'create') isPanelOpen.value = true
})
</script>

<template>
  <div class="grn-page" :class="{ 'panel-active': isPanelOpen }">
    <GrnListTable
      :grns="filteredGrns"
      :loading="isListLoading"
      :error="isListError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      v-model:selectedChamber="selectedChamber"
      v-model:selectedPeriod="selectedPeriod"
      @openCreate="isPanelOpen = true"
      @retry="handleRetry"
      @view="handleView"
      @post="handlePost"
      @cancel="handleCancel"
      :class="{ 'shrink-list': isPanelOpen }"
    />

    <GrnDetailDialog v-model:visible="isDetailOpen" :grn="selectedGrn" />

    <transition name="panel-slide">
      <GrnCreatePanel
        v-if="isPanelOpen"
        :facilityId="facilityId"
        :parties="partiesQuery.data.value || []"
        :commodities="commoditiesQuery.data.value || []"
        :loadingParties="partiesQuery.isLoading.value"
        :loadingCommodities="commoditiesQuery.isLoading.value"
        @close="isPanelOpen = false"
        @created="isPanelOpen = false"
      />
    </transition>
  </div>
</template>

<style scoped>
.grn-page {
  display: flex;
  gap: 20px;
  width: 100%;
  position: relative;
}
.shrink-list {
  max-width: 40%;
}

@media (max-width: 900px) {
  .grn-page {
    flex-direction: column;
  }
  .shrink-list {
    max-width: 100%;
  }
}
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>

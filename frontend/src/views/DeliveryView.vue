<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useFacility } from '../composables/useFacility'
import {
  useDeliveryNoteList,
  usePostDeliveryNote,
  useCancelDeliveryNote
} from '../composables/useDeliveryNotes'
import { useSearchFilter } from '../composables/useSearchFilter'
import DeliveryListTable from '../components/delivery/DeliveryListTable.vue'
import type { DeliveryNoteOutput } from '../api/delivery'

const toast = useToast()
const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedStatus = ref('all')

const deliveryFilters = computed(() => ({
  status: selectedStatus.value
}))

const deliveriesQuery = useDeliveryNoteList(facilityId, deliveryFilters)
const postMutation = usePostDeliveryNote()
const cancelMutation = useCancelDeliveryNote()

const deliveryList = computed<DeliveryNoteOutput[]>(() => deliveriesQuery.data.value || [])

const { searchQuery, filtered: searchedDeliveries } = useSearchFilter(deliveryList, (item, query) =>
  item.dn_number.toLowerCase().includes(query) ||
  item.party_name.toLowerCase().includes(query) ||
  (item.vehicle_number ? item.vehicle_number.toLowerCase().includes(query) : false) ||
  (item.driver_name ? item.driver_name.toLowerCase().includes(query) : false)
)

const isLoading = computed(() => loadingFacility.value || deliveriesQuery.isLoading.value)
const isError = computed(() => facilityError.value || deliveriesQuery.isError.value)
const errorMessage = computed(() => (deliveriesQuery.error.value instanceof Error ? deliveriesQuery.error.value.message : undefined))

const handlePost = async (id: number) => {
  try {
    const updated = await postMutation.mutateAsync(id)
    toast.add({
      severity: 'success',
      summary: 'Delivery Note Posted',
      detail: `DN ${updated.dn_number} posted successfully and stock updated.`,
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Action Failed',
      detail: err instanceof Error ? err.message : 'Failed to post Delivery Note',
      life: 5000
    })
  }
}

const handleCancel = async (id: number) => {
  try {
    const updated = await cancelMutation.mutateAsync(id)
    toast.add({
      severity: 'warn',
      summary: 'Delivery Note Cancelled',
      detail: `DN ${updated.dn_number} was cancelled.`,
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Action Failed',
      detail: err instanceof Error ? err.message : 'Failed to cancel Delivery Note',
      life: 5000
    })
  }
}

const handleNewDelivery = () => {
  toast.add({
    severity: 'info',
    summary: 'New Delivery (DN)',
    detail: 'Delivery Note creation form will be enabled in the next release.',
    life: 4000
  })
}

const handleRetry = () => {
  refetchFacility()
  deliveriesQuery.refetch()
}
</script>

<template>
  <div class="page-container">
    <DeliveryListTable
      :deliveries="searchedDeliveries"
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      v-model:selectedStatus="selectedStatus"
      @newDelivery="handleNewDelivery"
      @retry="handleRetry"
      @post="handlePost"
      @cancel="handleCancel"
    />
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
}
</style>

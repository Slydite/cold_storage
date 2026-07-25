<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useFacility } from '../composables/useFacility'
import {
  useDeliveryNoteList,
  usePostDeliveryNote,
  useCancelDeliveryNote,
  useGenerateDeliveryNotePdf
} from '../composables/useDeliveryNotes'
import { usePartyList } from '../composables/useParties'
import { useSearchFilter } from '../composables/useSearchFilter'
import DeliveryListTable from '../components/delivery/DeliveryListTable.vue'
import DeliveryCreatePanel from '../components/delivery/DeliveryCreatePanel.vue'
import DeliveryDetailDialog from '../components/delivery/DeliveryDetailDialog.vue'
import type { DeliveryNoteOutput } from '../api/delivery'

const route = useRoute()
const toast = useToast()
const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedStatus = ref('all')
const isPanelOpen = ref(false)
const selectedDelivery = ref<DeliveryNoteOutput | null>(null)
const isDetailOpen = ref(false)
const generatingPdfId = ref<number | null>(null)

const deliveryFilters = computed(() => ({
  status: selectedStatus.value
}))

const deliveriesQuery = useDeliveryNoteList(facilityId, deliveryFilters)
const partiesQuery = usePartyList(facilityId)
const postMutation = usePostDeliveryNote()
const cancelMutation = useCancelDeliveryNote()
const generatePdfMutation = useGenerateDeliveryNotePdf()

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

const handleView = (dn: DeliveryNoteOutput) => {
  selectedDelivery.value = dn
  isDetailOpen.value = true
}

const handleGeneratePdf = async (id: number) => {
  generatingPdfId.value = id
  try {
    const updated = await generatePdfMutation.mutateAsync(id)
    toast.add({
      severity: 'success',
      summary: 'PDF Generated',
      detail: `PDF generated for Delivery Note ${updated.dn_number}.`,
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Action Failed',
      detail: err instanceof Error ? err.message : 'Failed to generate PDF',
      life: 5000
    })
  } finally {
    generatingPdfId.value = null
  }
}

const handleCreated = (dnNumber: string, status: string) => {
  isPanelOpen.value = false
  const isDraft = status === 'DRAFT'
  toast.add({
    severity: isDraft ? 'info' : 'success',
    summary: isDraft ? 'Draft Saved' : 'Delivery Note Created',
    detail: `Delivery Note ${dnNumber} was successfully ${isDraft ? 'saved as draft' : 'posted'}.`,
    life: 4000
  })
}

const handleRetry = () => {
  refetchFacility()
  deliveriesQuery.refetch()
}

onMounted(() => {
  if (route.query.action === 'create') {
    isPanelOpen.value = true
  }
})
</script>

<template>
  <div class="delivery-page" :class="{ 'panel-active': isPanelOpen }">
    <DeliveryListTable
      :deliveries="searchedDeliveries"
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      :generatingPdfId="generatingPdfId"
      v-model:searchQuery="searchQuery"
      v-model:selectedStatus="selectedStatus"
      @newDelivery="isPanelOpen = true"
      @retry="handleRetry"
      @view="handleView"
      @post="handlePost"
      @cancel="handleCancel"
      @generatePdf="handleGeneratePdf"
      :class="{ 'shrink-list': isPanelOpen }"
    />

    <DeliveryDetailDialog v-model:visible="isDetailOpen" :deliveryNote="selectedDelivery" />

    <transition name="panel-slide">
      <DeliveryCreatePanel
        v-if="isPanelOpen"
        :facilityId="facilityId"
        :parties="partiesQuery.data.value || []"
        :loadingParties="partiesQuery.isLoading.value"
        @close="isPanelOpen = false"
        @created="handleCreated"
      />
    </transition>
  </div>
</template>

<style scoped>
.delivery-page {
  display: flex;
  gap: 20px;
  width: 100%;
  position: relative;
}
.shrink-list {
  max-width: 40%;
}

@media (max-width: 900px) {
  .delivery-page {
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useFacility } from '../composables/useFacility'
import {
  useDeliveryNoteList,
  usePostDeliveryNote,
  useCancelDeliveryNote
} from '../composables/useDeliveryNotes'
import { usePartyList } from '../composables/useParties'
import { useSearchFilter } from '../composables/useSearchFilter'
import { useHistoryDismiss } from '../composables/useHistoryDismiss'
import DeliveryListTable from '../components/delivery/DeliveryListTable.vue'
import DeliveryCreatePanel from '../components/delivery/DeliveryCreatePanel.vue'
import DeliveryDetailDialog from '../components/delivery/DeliveryDetailDialog.vue'
import type { DeliveryNoteOutput } from '../api/delivery'

const route = useRoute()
const toast = useToast()
const { t } = useI18n()
const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedStatus = ref('all')
const isPanelOpen = ref(false)
const selectedDelivery = ref<DeliveryNoteOutput | null>(null)
const isDetailOpen = ref(false)

// Hardware/browser Back closes an open panel or dialog instead of leaving the page.
useHistoryDismiss(isPanelOpen, () => { isPanelOpen.value = false })
useHistoryDismiss(isDetailOpen, () => { isDetailOpen.value = false })

const deliveryFilters = computed(() => ({
  status: selectedStatus.value
}))

const deliveriesQuery = useDeliveryNoteList(facilityId, deliveryFilters)
const partiesQuery = usePartyList(facilityId)
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
      summary: t('delivery.postedToastSummary'),
      detail: t('delivery.postedToastDetail', { number: updated.dn_number }),
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('common.actionFailed'),
      detail: err instanceof Error ? err.message : t('delivery.postFailed'),
      life: 5000
    })
  }
}

const handleCancel = async (id: number) => {
  try {
    const updated = await cancelMutation.mutateAsync(id)
    toast.add({
      severity: 'warn',
      summary: t('delivery.cancelledToastSummary'),
      detail: t('delivery.cancelledToastDetail', { number: updated.dn_number }),
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('common.actionFailed'),
      detail: err instanceof Error ? err.message : t('delivery.cancelFailed'),
      life: 5000
    })
  }
}

const editingDelivery = ref<DeliveryNoteOutput | undefined>(undefined)

const handleNewDelivery = () => {
  editingDelivery.value = undefined
  isPanelOpen.value = true
}

const handleClosePanel = () => {
  isPanelOpen.value = false
  editingDelivery.value = undefined
}

const handleEdit = (dn: DeliveryNoteOutput) => {
  editingDelivery.value = dn
  isPanelOpen.value = true
}

const handleEditFromDialog = (dn: DeliveryNoteOutput) => {
  isDetailOpen.value = false
  handleEdit(dn)
}

const handleView = (dn: DeliveryNoteOutput) => {
  selectedDelivery.value = dn
  isDetailOpen.value = true
}

const handleRefresh = async () => {
  await deliveriesQuery.refetch()
  if (selectedDelivery.value) {
    const updated = deliveryList.value.find(item => item.id === selectedDelivery.value?.id)
    if (updated) {
      selectedDelivery.value = updated
    }
  }
}

const handleCreated = () => {
  isPanelOpen.value = false
  editingDelivery.value = undefined
}

const handleRetry = () => {
  refetchFacility()
  deliveriesQuery.refetch()
}

onMounted(() => {
  if (route.query.action === 'create') {
    handleNewDelivery()
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
      v-model:searchQuery="searchQuery"
      v-model:selectedStatus="selectedStatus"
      @newDelivery="handleNewDelivery"
      @retry="handleRetry"
      @view="handleView"
      @edit="handleEdit"
      @post="handlePost"
      @cancel="handleCancel"
      :class="{ 'shrink-list': isPanelOpen }"
    />

    <DeliveryDetailDialog v-model:visible="isDetailOpen" :deliveryNote="selectedDelivery" @refresh="handleRefresh" @edit="handleEditFromDialog" />

    <transition name="panel-slide">
      <DeliveryCreatePanel
        v-if="isPanelOpen"
        :facilityId="facilityId"
        :parties="partiesQuery.data.value || []"
        :loadingParties="partiesQuery.isLoading.value"
        :deliveryNote="editingDelivery"
        @close="handleClosePanel"
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

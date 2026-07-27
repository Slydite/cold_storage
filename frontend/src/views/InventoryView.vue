<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useFacility } from '../composables/useFacility'
import { useLotList } from '../composables/useLots'
import { useChamberList, useFloorList, useBlockList } from '../composables/useLocations'
import { useSearchFilter } from '../composables/useSearchFilter'
import { fetchParties } from '../api/party'
import InventoryListTable from '../components/inventory/InventoryListTable.vue'
import type { LotOutput } from '../api/lot'

const { facilities, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedFacilityId = ref<number | undefined>(undefined)
const selectedChamberId = ref<number | undefined>(undefined)
const selectedFloorId = ref<number | undefined>(undefined)
const selectedBlockId = ref<number | undefined>(undefined)
const selectedPartyId = ref<number | undefined>(undefined)
const selectedStatus = ref('active')

const handleFacilityChange = (id: number | undefined) => {
  selectedFacilityId.value = id
  selectedChamberId.value = undefined
  selectedFloorId.value = undefined
  selectedBlockId.value = undefined
  selectedPartyId.value = undefined
}

const handleChamberChange = (id: number | undefined) => {
  selectedChamberId.value = id
  selectedFloorId.value = undefined
  selectedBlockId.value = undefined
}

const handleFloorChange = (id: number | undefined) => {
  selectedFloorId.value = id
  selectedBlockId.value = undefined
}

const chambersQuery = useChamberList({ facilityId: selectedFacilityId })
const floorsQuery = useFloorList({ facilityId: selectedFacilityId, chamberId: selectedChamberId })
const blocksQuery = useBlockList({ facilityId: selectedFacilityId, chamberId: selectedChamberId, floorId: selectedFloorId })

const lotFilters = computed(() => ({
  chamberId: selectedChamberId.value,
  floorId: selectedFloorId.value,
  blockId: selectedBlockId.value,
  partyId: selectedPartyId.value,
  inStockOnly: selectedStatus.value === 'active'
}))

const lotsQuery = useLotList(selectedFacilityId, lotFilters)

const partiesQuery = useQuery({
  queryKey: computed(() => ['parties', selectedFacilityId.value]),
  queryFn: () => fetchParties({ facilityId: selectedFacilityId.value! }),
  enabled: computed(() => selectedFacilityId.value !== undefined)
})

const rawLots = computed<LotOutput[]>(() => lotsQuery.data.value || [])

const { searchQuery, filtered: searchedLots } = useSearchFilter(rawLots, (item, query) =>
  item.lot_number.toLowerCase().includes(query) ||
  item.commodity_name.toLowerCase().includes(query) ||
  (item.location_display ? item.location_display.toLowerCase().includes(query) : false) ||
  (item.party_name ? item.party_name.toLowerCase().includes(query) : false) ||
  (item.facility_name ? item.facility_name.toLowerCase().includes(query) : false)
)

const filteredLots = computed(() => {
  return searchedLots.value.filter((lot) => {
    if (selectedStatus.value === 'depleted') {
      return lot.remaining_qty === 0
    }
    return true
  })
})

const isLoading = computed(() => loadingFacility.value || lotsQuery.isLoading.value)
const isError = computed(() => facilityError.value || lotsQuery.isError.value)
const errorMessage = computed(() => (lotsQuery.error.value instanceof Error ? lotsQuery.error.value.message : undefined))

const handleRetry = () => {
  refetchFacility()
  lotsQuery.refetch()
}
</script>

<template>
  <div class="page-container">
    <InventoryListTable
      :lots="filteredLots"
      :facilities="facilities"
      :chambers="chambersQuery.data.value || []"
      :floors="floorsQuery.data.value || []"
      :blocks="blocksQuery.data.value || []"
      :parties="partiesQuery.data.value || []"
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      :selectedFacilityId="selectedFacilityId"
      @update:selectedFacilityId="handleFacilityChange"
      :selectedChamberId="selectedChamberId"
      @update:selectedChamberId="handleChamberChange"
      :selectedFloorId="selectedFloorId"
      @update:selectedFloorId="handleFloorChange"
      v-model:selectedBlockId="selectedBlockId"
      v-model:selectedPartyId="selectedPartyId"
      v-model:selectedStatus="selectedStatus"
      @retry="handleRetry"
    />
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
}
</style>


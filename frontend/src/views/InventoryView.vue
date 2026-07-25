<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useFacility } from '../composables/useFacility'
import { useLotList } from '../composables/useLots'
import { useSearchFilter } from '../composables/useSearchFilter'
import { fetchParties } from '../api/party'
import InventoryListTable from '../components/inventory/InventoryListTable.vue'
import type { LotOutput } from '../api/lot'

const { facilities, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedFacilityId = ref<number | undefined>(undefined)
const selectedFloor = ref('all')
const selectedChamber = ref('all')
const selectedPartyId = ref<number | undefined>(undefined)
const selectedStatus = ref('active')

const lotFilters = computed(() => ({
  floor: selectedFloor.value,
  chamber: selectedChamber.value,
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
  (item.chamber ? item.chamber.toLowerCase().includes(query) : false) ||
  (item.floor ? item.floor.toLowerCase().includes(query) : false) ||
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
      :parties="partiesQuery.data.value || []"
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      v-model:selectedFacilityId="selectedFacilityId"
      v-model:selectedFloor="selectedFloor"
      v-model:selectedChamber="selectedChamber"
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


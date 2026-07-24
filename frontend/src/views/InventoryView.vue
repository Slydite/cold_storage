<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFacility } from '../composables/useFacility'
import { useLotList } from '../composables/useLots'
import { useSearchFilter } from '../composables/useSearchFilter'
import InventoryListTable from '../components/inventory/InventoryListTable.vue'
import type { LotOutput } from '../api/lot'

const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedChamber = ref('all')
const selectedStatus = ref('active')

const lotFilters = computed(() => ({
  chamber: selectedChamber.value,
  inStockOnly: selectedStatus.value === 'active'
}))

const lotsQuery = useLotList(facilityId, lotFilters)

const rawLots = computed<LotOutput[]>(() => lotsQuery.data.value || [])

const { searchQuery, filtered: searchedLots } = useSearchFilter(rawLots, (item, query) =>
  item.lot_number.toLowerCase().includes(query) ||
  item.commodity_name.toLowerCase().includes(query) ||
  (item.chamber ? item.chamber.toLowerCase().includes(query) : false)
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
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      v-model:selectedChamber="selectedChamber"
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

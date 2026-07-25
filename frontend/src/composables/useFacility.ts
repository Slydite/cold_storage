import { computed, watchEffect } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { fetchFacilities } from '../api/facility'
import { useFacilityStore } from '../stores/facility'

export function useFacility() {
  const facilityStore = useFacilityStore()

  const query = useQuery({
    queryKey: ['facilities'],
    queryFn: () => fetchFacilities(),
    staleTime: Infinity
  })

  watchEffect(() => {
    const list = query.data.value
    if (list && list.length > 0) {
      const exists = list.some((f) => f.id === facilityStore.selectedFacilityId)
      if (!exists && list[0]) {
        facilityStore.setSelectedFacilityId(list[0].id)
      }
    }
  })

  const facilityId = computed(() => facilityStore.selectedFacilityId ?? query.data.value?.[0]?.id)
  const facilities = computed(() => query.data.value ?? [])

  return {
    facilityId,
    selectedFacilityId: computed(() => facilityStore.selectedFacilityId),
    setSelectedFacilityId: facilityStore.setSelectedFacilityId,
    facilities,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch
  }
}


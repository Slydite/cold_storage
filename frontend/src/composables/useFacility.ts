import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { fetchFacilities } from '../api/facility'

export function useFacility() {
  const query = useQuery({
    queryKey: ['facilities'],
    queryFn: () => fetchFacilities(),
    staleTime: Infinity
  })

  const facilityId = computed(() => query.data.value?.[0]?.id)

  return {
    facilityId,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch
  }
}

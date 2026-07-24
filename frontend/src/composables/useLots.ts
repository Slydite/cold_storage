import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { fetchLots } from '../api/lot'

export function useLotList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?:
    | Ref<{
        partyId?: number
        commodityId?: number
        chamber?: string
        inStockOnly?: boolean
      }>
    | ComputedRef<{
        partyId?: number
        commodityId?: number
        chamber?: string
        inStockOnly?: boolean
      }>
) {
  return useQuery({
    queryKey: computed(() => [
      'lots',
      facilityId.value,
      filters?.value?.partyId,
      filters?.value?.commodityId,
      filters?.value?.chamber,
      filters?.value?.inStockOnly
    ]),
    queryFn: () =>
      fetchLots({
        facilityId: facilityId.value!,
        partyId: filters?.value?.partyId,
        commodityId: filters?.value?.commodityId,
        chamber: filters?.value?.chamber === 'all' ? undefined : filters?.value?.chamber,
        inStockOnly: filters?.value?.inStockOnly
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

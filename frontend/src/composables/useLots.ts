import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { fetchLots } from '../api/lot'

export function useLotList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?:
    | Ref<{
        chamberId?: number
        floorId?: number
        blockId?: number
        partyId?: number
        commodityId?: number
        inStockOnly?: boolean
      }>
    | ComputedRef<{
        chamberId?: number
        floorId?: number
        blockId?: number
        partyId?: number
        commodityId?: number
        inStockOnly?: boolean
      }>
) {
  return useQuery({
    queryKey: computed(() => [
      'lots',
      facilityId.value,
      filters?.value?.chamberId,
      filters?.value?.floorId,
      filters?.value?.blockId,
      filters?.value?.partyId,
      filters?.value?.commodityId,
      filters?.value?.inStockOnly
    ]),
    queryFn: () =>
      fetchLots({
        facilityId: facilityId.value,
        chamberId: filters?.value?.chamberId,
        floorId: filters?.value?.floorId,
        blockId: filters?.value?.blockId,
        partyId: filters?.value?.partyId,
        commodityId: filters?.value?.commodityId,
        inStockOnly: filters?.value?.inStockOnly
      })
  })
}


import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { fetchCommodities, createCommodity, updateCommodity } from '../api/commodity'
import type { CommodityInput } from '../api/commodity'

export function useCommodityList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>
) {
  return useQuery({
    queryKey: computed(() => ['commodities', facilityId.value]),
    queryFn: () => fetchCommodities({ facilityId: facilityId.value! }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateCommodity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CommodityInput) => createCommodity(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commodities'] })
    }
  })
}

export function useUpdateCommodity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CommodityInput }) => updateCommodity(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commodities'] })
    }
  })
}

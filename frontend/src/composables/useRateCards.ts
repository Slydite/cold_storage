import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { fetchRateCards, createRateCard } from '../api/billing'
import type { RateCardInput } from '../api/billing'

export function useRateCardList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?: Ref<{ commodityId?: number; isActive?: boolean }> | ComputedRef<{ commodityId?: number; isActive?: boolean }>
) {
  return useQuery({
    queryKey: computed(() => [
      'rate-cards',
      facilityId.value,
      filters?.value?.commodityId,
      filters?.value?.isActive
    ]),
    queryFn: () =>
      fetchRateCards({
        facilityId: facilityId.value!,
        commodityId: filters?.value?.commodityId,
        isActive: filters?.value?.isActive
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateRateCard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: RateCardInput) => createRateCard(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rate-cards'] })
    }
  })
}

import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { fetchGrns, createGrn, postGrn, cancelGrn } from '../api/grn'
import type { GrnCreateInput } from '../api/grn'

export function useGrnList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?: Ref<{ partyId?: number; status?: string }> | ComputedRef<{ partyId?: number; status?: string }>
) {
  return useQuery({
    queryKey: computed(() => [
      'grns',
      facilityId.value,
      filters?.value?.partyId,
      filters?.value?.status
    ]),
    queryFn: () =>
      fetchGrns({
        facilityId: facilityId.value!,
        partyId: filters?.value?.partyId,
        status: filters?.value?.status
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateGrn() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: GrnCreateInput) => createGrn(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grns'] })
    }
  })
}

export function usePostGrn() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => postGrn(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grns'] })
      queryClient.invalidateQueries({ queryKey: ['lots'] })
    }
  })
}

export function useCancelGrn() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelGrn(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grns'] })
    }
  })
}

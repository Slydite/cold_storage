import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchRentRuns,
  fetchRentRun,
  previewRentRun,
  createRentRun,
  postRentRun,
  cancelRentRun
} from '../api/billing'
import type { RentRunCreateInput, RentRunPreviewInput } from '../api/billing'

export function useRentRunList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?: Ref<{ status?: string }> | ComputedRef<{ status?: string }>
) {
  return useQuery({
    queryKey: computed(() => [
      'rent-runs',
      facilityId.value,
      filters?.value?.status
    ]),
    queryFn: () =>
      fetchRentRuns({
        facilityId: facilityId.value!,
        status: filters?.value?.status
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useRentRunDetail(id: Ref<number | null> | ComputedRef<number | null>) {
  return useQuery({
    queryKey: computed(() => ['rent-runs', id.value]),
    queryFn: () => fetchRentRun(id.value!),
    enabled: computed(() => id.value !== null && id.value > 0)
  })
}

export function usePreviewRentRun() {
  return useMutation({
    mutationFn: (body: RentRunPreviewInput) => previewRentRun(body)
  })
}

export function useCreateRentRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: RentRunCreateInput) => createRentRun(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rent-runs'] })
    }
  })
}

export function usePostRentRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => postRentRun(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rent-runs'] })
    }
  })
}

export function useCancelRentRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelRentRun(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rent-runs'] })
    }
  })
}

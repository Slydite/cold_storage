import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { createFacility, updateFacility } from '../api/facility'
import type { FacilityInput } from '../api/facility'

export function useCreateFacility() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: FacilityInput) => createFacility(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['facilities'] })
    }
  })
}

export function useUpdateFacility() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: FacilityInput }) => updateFacility(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['facilities'] })
    }
  })
}

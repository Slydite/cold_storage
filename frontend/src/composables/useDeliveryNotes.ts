import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchDeliveryNotes,
  createDeliveryNote,
  postDeliveryNote,
  cancelDeliveryNote,
  updateDeliveryNote,
  updateAndPostDeliveryNote
} from '../api/delivery'
import type { DeliveryNoteCreateInput, DeliveryNoteUpdateInput } from '../api/delivery'

export function useDeliveryNoteList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?: Ref<{ partyId?: number; status?: string }> | ComputedRef<{ partyId?: number; status?: string }>
) {
  return useQuery({
    queryKey: computed(() => [
      'delivery-notes',
      facilityId.value,
      filters?.value?.partyId,
      filters?.value?.status
    ]),
    queryFn: () =>
      fetchDeliveryNotes({
        facilityId: facilityId.value!,
        partyId: filters?.value?.partyId,
        status: filters?.value?.status === 'all' ? undefined : filters?.value?.status
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useCreateDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: DeliveryNoteCreateInput) => createDeliveryNote(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-notes'] })
    }
  })
}

export function useUpdateDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: DeliveryNoteUpdateInput }) => updateDeliveryNote(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-notes'] })
    }
  })
}

export function useUpdateAndPostDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: DeliveryNoteUpdateInput }) => updateAndPostDeliveryNote(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-notes'] })
      queryClient.invalidateQueries({ queryKey: ['lots'] })
    }
  })
}

export function usePostDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => postDeliveryNote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-notes'] })
      queryClient.invalidateQueries({ queryKey: ['lots'] })
    }
  })
}

export function useCancelDeliveryNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelDeliveryNote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-notes'] })
    }
  })
}

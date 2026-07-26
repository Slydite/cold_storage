import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchInvoices,
  generateInvoices,
  postInvoice,
  cancelInvoice
} from '../api/invoicing'

export function useInvoiceList(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  filters?: Ref<{ partyId?: number; status?: string }> | ComputedRef<{ partyId?: number; status?: string }>
) {
  return useQuery({
    queryKey: computed(() => [
      'invoices',
      facilityId.value,
      filters?.value?.partyId,
      filters?.value?.status
    ]),
    queryFn: () =>
      fetchInvoices({
        facilityId: facilityId.value!,
        partyId: filters?.value?.partyId,
        status: filters?.value?.status
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useGenerateInvoices() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { facility_id: number; rent_run_id: number }) => generateInvoices(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    }
  })
}

export function usePostInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => postInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    }
  })
}

export function useCancelInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    }
  })
}

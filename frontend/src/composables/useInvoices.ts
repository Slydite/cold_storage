import { computed, type Ref, type ComputedRef } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  fetchInvoices,
  fetchInvoicePreview,
  generateInvoices,
  postInvoice,
  cancelInvoice,
  createInvoicePayment,
  deleteInvoicePayment
} from '../api/invoicing'
import type { GenerateInvoicesInput, PaymentInput } from '../api/invoicing'

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

export function useInvoicePreview(
  facilityId: Ref<number | undefined> | ComputedRef<number | undefined>,
  partyId?: Ref<number | undefined | null> | ComputedRef<number | undefined | null>
) {
  return useQuery({
    queryKey: computed(() => [
      'invoice-preview',
      facilityId.value,
      partyId?.value ?? undefined
    ]),
    queryFn: () =>
      fetchInvoicePreview({
        facilityId: facilityId.value!,
        partyId: partyId?.value ?? undefined
      }),
    enabled: computed(() => !!facilityId.value)
  })
}

export function useGenerateInvoices() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: GenerateInvoicesInput) => generateInvoices(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['invoice-preview'] })
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

export function useCreateInvoicePayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ invoiceId, body }: { invoiceId: number; body: PaymentInput }) =>
      createInvoicePayment(invoiceId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    }
  })
}

export function useDeleteInvoicePayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ invoiceId, paymentId }: { invoiceId: number; paymentId: number }) =>
      deleteInvoicePayment(invoiceId, paymentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    }
  })
}


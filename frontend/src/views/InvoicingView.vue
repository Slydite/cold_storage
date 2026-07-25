<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useFacility } from '../composables/useFacility'
import {
  useInvoiceList,
  usePostInvoice,
  useCancelInvoice,
  useGenerateInvoicePdf
} from '../composables/useInvoices'
import InvoiceTable from '../components/invoicing/InvoiceTable.vue'
import GenerateInvoiceDialog from '../components/invoicing/GenerateInvoiceDialog.vue'

import type { InvoiceOutput } from '../api/invoicing'

const toast = useToast()
const { facilityId } = useFacility()

const searchQuery = ref('')
const selectedStatus = ref('')
const showGenerateDialog = ref(false)
const generatingPdfId = ref<number | null>(null)

const filters = computed(() => ({
  status: selectedStatus.value || undefined
}))

const {
  data: rawInvoices,
  isLoading,
  isError,
  error,
  refetch
} = useInvoiceList(facilityId, filters)

const postMutation = usePostInvoice()
const cancelMutation = useCancelInvoice()
const generatePdfMutation = useGenerateInvoicePdf()

const filteredInvoices = computed(() => {
  const list = rawInvoices.value ?? []
  if (!searchQuery.value.trim()) return list
  const q = searchQuery.value.toLowerCase().trim()
  return list.filter(
    (inv) =>
      inv.invoice_number.toLowerCase().includes(q) ||
      inv.party_name.toLowerCase().includes(q)
  )
})

async function handlePost(id: number) {
  try {
    const updated = await postMutation.mutateAsync(id)
    toast.add({
      severity: 'success',
      summary: 'Invoice Posted',
      detail: `Invoice ${updated.invoice_number} is now POSTED.`,
      life: 4000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Failed to Post',
      detail: err instanceof Error ? err.message : 'Could not post invoice',
      life: 5000
    })
  }
}

async function handleCancel(id: number) {
  try {
    const updated = await cancelMutation.mutateAsync(id)
    toast.add({
      severity: 'info',
      summary: 'Invoice Cancelled',
      detail: `Invoice ${updated.invoice_number} was cancelled.`,
      life: 4000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Failed to Cancel',
      detail: err instanceof Error ? err.message : 'Could not cancel invoice',
      life: 5000
    })
  }
}

async function handleGeneratePdf(id: number) {
  generatingPdfId.value = id
  try {
    const updated = await generatePdfMutation.mutateAsync(id)
    toast.add({
      severity: 'success',
      summary: 'PDF Generated',
      detail: `PDF ready for ${updated.invoice_number}`,
      life: 4000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'PDF Error',
      detail: err instanceof Error ? err.message : 'Failed to generate PDF',
      life: 5000
    })
  } finally {
    generatingPdfId.value = null
  }
}

function handleGenerateSuccess(createdInvoices: InvoiceOutput[]) {
  const count = createdInvoices.length
  const numbers = createdInvoices.map((inv) => inv.invoice_number).join(', ')
  const partyNames = Array.from(new Set(createdInvoices.map((inv) => inv.party_name).filter(Boolean))).join(', ')
  toast.add({
    severity: 'success',
    summary: 'Invoices Generated',
    detail: `Created ${count} invoice(s) [${numbers}] for ${partyNames}.`,
    life: 6000
  })
}

function handleGenerateError(message: string) {
  toast.add({
    severity: 'error',
    summary: 'Generation Error',
    detail: message,
    life: 6000
  })
}
</script>

<template>
  <div class="page-container">
    <InvoiceTable
      :invoices="filteredInvoices"
      :loading="isLoading"
      :error="isError"
      :errorDetail="error ? (error as Error).message : undefined"
      v-model:searchQuery="searchQuery"
      v-model:selectedStatus="selectedStatus"
      :generatingPdfId="generatingPdfId"
      @openGenerate="showGenerateDialog = true"
      @retry="refetch"
      @post="handlePost"
      @cancel="handleCancel"
      @generatePdf="handleGeneratePdf"
    />

    <GenerateInvoiceDialog
      v-model:visible="showGenerateDialog"
      :facilityId="facilityId"
      @success="handleGenerateSuccess"
      @error="handleGenerateError"
    />
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>

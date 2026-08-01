<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useFacility } from '../composables/useFacility'
import {
  useInvoiceList,
  usePostInvoice,
  useCancelInvoice
} from '../composables/useInvoices'
import InvoiceTable from '../components/invoicing/InvoiceTable.vue'
import GenerateInvoiceDialog from '../components/invoicing/GenerateInvoiceDialog.vue'
import type { InvoiceOutput } from '../api/invoicing'

const toast = useToast()
const { t } = useI18n()
const { facilityId } = useFacility()

const searchQuery = ref('')
const selectedStatus = ref('')
const selectedFinancialYear = ref('')
const showGenerateDialog = ref(false)

const filters = computed(() => ({
  status: selectedStatus.value || undefined,
  financialYear: selectedFinancialYear.value || undefined
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
      summary: t('invoicing.invoicePostedSummary'),
      detail: t('invoicing.invoicePostedDetail', { number: updated.invoice_number }),
      life: 4000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('invoicing.postFailed'),
      detail: err instanceof Error ? err.message : t('invoicing.postFailed'),
      life: 5000
    })
  }
}

async function handleCancel(id: number) {
  try {
    const updated = await cancelMutation.mutateAsync(id)
    toast.add({
      severity: 'info',
      summary: t('invoicing.invoiceCancelledSummary'),
      detail: t('invoicing.invoiceCancelledDetail', { number: updated.invoice_number }),
      life: 4000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('invoicing.cancelFailed'),
      detail: err instanceof Error ? err.message : t('invoicing.cancelFailed'),
      life: 5000
    })
  }
}

function handleGenerateSuccess(createdInvoices: InvoiceOutput[]) {
  const count = createdInvoices.length
  const numbers = createdInvoices.map((inv) => inv.invoice_number).join(', ')
  const partyNames = Array.from(new Set(createdInvoices.map((inv) => inv.party_name).filter(Boolean))).join(', ')
  toast.add({
    severity: 'success',
    summary: t('invoicing.invoicesGeneratedSummary'),
    detail: t('invoicing.invoicesGeneratedDetail', { count, numbers, partyNames }),
    life: 6000
  })
}

function handleGenerateError(message: string) {
  toast.add({
    severity: 'error',
    summary: t('invoicing.generationError'),
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
      v-model:selectedFinancialYear="selectedFinancialYear"
      @openGenerate="showGenerateDialog = true"
      @retry="refetch"
      @post="handlePost"
      @cancel="handleCancel"
      @refresh="refetch"
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

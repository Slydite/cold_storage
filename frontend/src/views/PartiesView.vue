<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useFacility } from '../composables/useFacility'
import { usePartyList, useCreateParty } from '../composables/useParties'
import { useSearchFilter } from '../composables/useSearchFilter'
import PartyListTable from '../components/party/PartyListTable.vue'
import PartyCreateDialog from '../components/party/PartyCreateDialog.vue'
import type { PartyOutput, TypeEnum } from '../api/party'

const toast = useToast()
const { facilityId, isLoading: loadingFacility, isError: facilityError, refetch: refetchFacility } = useFacility()

const selectedType = ref('all')
const isDialogOpen = ref(false)

const partiesQuery = usePartyList(facilityId)
const createMutation = useCreateParty()

const partyList = computed<PartyOutput[]>(() => partiesQuery.data.value || [])

const { searchQuery, filtered: searchedParties } = useSearchFilter(partyList, (item, query) =>
  item.name.toLowerCase().includes(query) ||
  item.code.toLowerCase().includes(query) ||
  (item.phone ? item.phone.toLowerCase().includes(query) : false) ||
  (item.email ? item.email.toLowerCase().includes(query) : false)
)

const filteredParties = computed(() =>
  searchedParties.value.filter(
    (party) => selectedType.value === 'all' || party.type === selectedType.value
  )
)

const isLoading = computed(() => loadingFacility.value || partiesQuery.isLoading.value)
const isError = computed(() => facilityError.value || partiesQuery.isError.value)
const errorMessage = computed(() => (partiesQuery.error.value instanceof Error ? partiesQuery.error.value.message : undefined))

const handleRetry = () => {
  refetchFacility()
  partiesQuery.refetch()
}

const handleCreateParty = async (values: {
  name: string
  code: string
  type: TypeEnum
  phone?: string
  email?: string
  address?: string
  gstin?: string
}) => {
  if (!facilityId.value) return
  try {
    const created = await createMutation.mutateAsync({
      facility_id: facilityId.value,
      ...values
    })
    toast.add({
      severity: 'success',
      summary: 'Party Created',
      detail: `Party "${created.name}" (${created.code}) created successfully.`,
      life: 3000
    })
    isDialogOpen.value = false
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Action Failed',
      detail: err instanceof Error ? err.message : 'Failed to create party',
      life: 5000
    })
  }
}
</script>

<template>
  <div class="page-container">
    <PartyListTable
      :parties="filteredParties"
      :loading="isLoading"
      :error="isError"
      :errorDetail="errorMessage"
      v-model:searchQuery="searchQuery"
      v-model:selectedType="selectedType"
      @openCreate="isDialogOpen = true"
      @retry="handleRetry"
    />

    <PartyCreateDialog
      v-model:visible="isDialogOpen"
      :loading="createMutation.isPending.value"
      @submit="handleCreateParty"
    />
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
}
</style>

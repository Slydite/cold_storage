<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import { useConfirm } from 'primevue/useconfirm'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Filter,
  FilterX,
  Download,
  Plus,
  Eye,
  AlertCircle,
  RefreshCw,
  Truck,
  FileCheck,
  XCircle,
  Printer
} from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import type { DeliveryNoteOutput } from '../../api/delivery'

interface Props {
  deliveries: DeliveryNoteOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedStatus: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedStatus': [status: string]
  newDelivery: []
  retry: []
  view: [delivery: DeliveryNoteOutput]
  post: [id: number]
  cancel: [id: number]
}>()

const confirm = useConfirm()

const statusOptions = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Posted', value: 'POSTED' },
  { label: 'Cancelled', value: 'CANCELLED' }
]

const statusFilterOptions = [
  { label: 'DRAFT', value: 'DRAFT' },
  { label: 'POSTED', value: 'POSTED' },
  { label: 'CANCELLED', value: 'CANCELLED' }
]

function buildDefaultFilters() {
  return {
    dn_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    dispatch_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    vehicle_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (props.searchQuery && props.searchQuery.trim() !== '') count++
  if (props.selectedStatus && props.selectedStatus !== 'all') count++
  return count
})

const {
  filters,
  showFilterRow,
  activeFilterCount,
  hasActiveFilters,
  clearFilters,
  toggleFilterRow
} = useTableFilters(buildDefaultFilters, extraActiveCount)

function handleClearAll() {
  clearFilters()
  emit('update:searchQuery', '')
  emit('update:selectedStatus', 'all')
}

function computeTotalQty(dn: DeliveryNoteOutput): number {
  if (!dn.lines || dn.lines.length === 0) return 0
  return dn.lines.reduce((sum, line) => sum + (line.qty || 0), 0)
}

const handleExport = () => {
  const headers = ['DN No.', 'Dispatch Date', 'Party', 'Vehicle No.', 'Total Qty', 'Status']
  const rows = props.deliveries.map((dn) => [
    dn.dn_number,
    dn.dispatch_date,
    dn.party_name,
    dn.vehicle_number || '-',
    formatQty(computeTotalQty(dn)),
    dn.status || '-'
  ])
  exportToCsv('deliveries.csv', headers, rows)
}

const confirmPost = (dn: DeliveryNoteOutput) => {
  confirm.require({
    message: `Are you sure you want to post Delivery Note ${dn.dn_number}? This will withdraw stock from inventory and cannot be directly undone.`,
    header: 'Confirm Stock Withdrawal',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Post Delivery Note',
      severity: 'success'
    },
    accept: () => {
      emit('post', dn.id)
    }
  })
}

const confirmCancel = (dn: DeliveryNoteOutput) => {
  confirm.require({
    message: `Are you sure you want to cancel draft Delivery Note ${dn.dn_number}?`,
    header: 'Cancel Delivery Note',
    icon: 'pi pi-exclamation-circle',
    rejectProps: {
      label: 'Back',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Cancel DN',
      severity: 'danger'
    },
    accept: () => {
      emit('cancel', dn.id)
    }
  })
}
</script>

<template>
  <div class="master-list-container">
    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            :value="searchQuery"
            @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
            type="text"
            placeholder="Search DN no., party, vehicle..."
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedStatus"
          @update:modelValue="emit('update:selectedStatus', $event)"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
        />
      </div>

      <div class="toolbar-actions">
        <button
          class="btn-outlined"
          :class="{ active: showFilterRow }"
          type="button"
          :aria-pressed="showFilterRow"
          @click="toggleFilterRow"
          title="Toggle inline column filters"
        >
          <Filter :size="15" />
          <span>Filters</span>
          <span v-if="hasActiveFilters" class="filter-count-badge">{{ activeFilterCount }}</span>
        </button>
        <button
          class="btn-outlined"
          type="button"
          :disabled="!hasActiveFilters"
          @click="handleClearAll"
          title="Clear all active filters and search"
        >
          <FilterX :size="15" />
          <span>Clear Filters</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>Export</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('newDelivery')">
          <Plus :size="16" />
          <span>New Delivery (DN)</span>
        </button>
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load Delivery Notes</h4>
      <p class="state-desc">{{ props.errorDetail || 'There was an issue connecting to the server. Please try again.' }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Explicit State 2: Skeleton Loading State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="56px" class="mb-2" v-for="i in 5" :key="i" />
    </div>

    <!-- Explicit State 3: Empty State -->
    <div v-else-if="props.deliveries.length === 0" class="state-card empty-card">
      <Truck :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No Delivery Notes found</h4>
      <p class="state-desc">Create delivery notes to issue and dispatch inventory to depositors.</p>
      <button class="btn-primary" type="button" @click="emit('newDelivery')">
        <Plus :size="16" />
        <span>New Delivery (DN)</span>
      </button>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.deliveries"
        v-model:filters="filters"
        :filterDisplay="showFilterRow ? 'row' : 'menu'"
        paginator
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        sortMode="multiple"
        removableSort
        size="small"
        stripedRows
        dataKey="id"
        responsiveLayout="scroll"
        class="custom-datatable"
      >
        <Column field="dn_number" header="DN No." sortable>
          <template #body="{ data }">
            <span class="code-link clickable" @click="emit('view', data)">{{ data.dn_number }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter DN No."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="dispatch_date" header="Dispatch Date" sortable>
          <template #filter="{ filterModel, filterCallback }">
            <DatePicker
              v-model="filterModel.value"
              @update:modelValue="(val) => { filterModel.value = formatDateFilter(val); filterCallback() }"
              dateFormat="yy-mm-dd"
              placeholder="YYYY-MM-DD"
              class="p-column-filter"
              size="small"
              showClear
            />
          </template>
        </Column>

        <Column field="party_name" header="Party" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.party_name }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter party..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="vehicle_number" header="Vehicle No.">
          <template #body="{ data }">
            <span>{{ data.vehicle_number || '-' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter vehicle..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column header="Total Qty">
          <template #body="{ data }">
            <span class="num-val">{{ formatQty(computeTotalQty(data)) }}</span>
          </template>
        </Column>

        <Column field="status" header="Status" sortable>
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="{
                success: data.status === 'POSTED',
                warning: data.status === 'DRAFT',
                danger: data.status === 'CANCELLED'
              }"
            >
              {{ data.status }}
            </span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <Select
              v-model="filterModel.value"
              @change="filterCallback()"
              :options="statusFilterOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Status"
              class="p-column-filter"
              size="small"
              showClear
            />
          </template>
        </Column>

        <Column header="Actions">
          <template #body="{ data }">
            <div class="row-actions">
              <button class="icon-btn" title="View details" type="button" @click="emit('view', data)">
                <Eye :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn"
                title="Post Delivery Note"
                type="button"
                @click="confirmPost(data)"
              >
                <FileCheck :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn danger-hover"
                title="Cancel Delivery Note"
                type="button"
                @click="confirmCancel(data)"
              >
                <XCircle :size="16" />
              </button>
              <a
                :href="`/api/delivery-notes/${data.id}/pdf/`"
                target="_blank"
                rel="noopener"
                class="icon-btn"
                title="PDF"
                aria-label="PDF"
              >
                <Printer :size="16" />
              </a>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.code-link.clickable {
  cursor: pointer;
}

.master-list-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.icon-muted {
  color: var(--text-secondary);
  font-size: 13px;
}

.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.state-icon {
  margin-bottom: 4px;
}

.state-icon.text-danger {
  color: var(--status-danger-color);
}

.state-icon.text-muted {
  color: var(--text-secondary);
}

.state-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.state-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 380px;
  margin-bottom: 8px;
}

.skeleton-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 20px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Skeleton from 'primevue/skeleton'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Plus, Download, Phone, Mail, AlertCircle, RefreshCw, Users } from 'lucide-vue-next'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters } from '../../composables/useTableFilters'
import type { PartyOutput } from '../../api/party'

interface Props {
  parties: PartyOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedType: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedType': [type: string]
  openCreate: []
  retry: []
}>()

const typeOptions = [
  { label: 'All Types', value: 'all' },
  { label: 'Depositors', value: 'DEPOSITOR' },
  { label: 'Vendors', value: 'VENDOR' },
  { label: 'Transporters', value: 'TRANSPORTER' }
]

const typeFilterOptions = [
  { label: 'Depositor', value: 'DEPOSITOR' },
  { label: 'Vendor', value: 'VENDOR' },
  { label: 'Transporter', value: 'TRANSPORTER' }
]

function buildDefaultFilters() {
  return {
    code: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    type_display: { value: null, matchMode: FilterMatchMode.CONTAINS },
    phone: { value: null, matchMode: FilterMatchMode.CONTAINS },
    email: { value: null, matchMode: FilterMatchMode.CONTAINS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (props.searchQuery && props.searchQuery.trim() !== '') count++
  if (props.selectedType && props.selectedType !== 'all') count++
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
  emit('update:selectedType', 'all')
}

const handleExport = () => {
  const headers = ['Code', 'Party Name', 'Type', 'Phone', 'Email', 'GSTIN', 'Address']
  const rows = props.parties.map((p) => [
    p.code,
    p.name,
    p.type_display || p.type,
    p.phone || '-',
    p.email || '-',
    p.gstin || '-',
    p.address || '-'
  ])
  exportToCsv('parties.csv', headers, rows)
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
            placeholder="Search party name, code..."
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedType"
          @update:modelValue="emit('update:selectedType', $event)"
          :options="typeOptions"
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
        <button class="btn-primary" type="button" @click="emit('openCreate')">
          <Plus :size="16" />
          <span>Add Party</span>
        </button>
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load parties</h4>
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
    <div v-else-if="props.parties.length === 0" class="state-card empty-card">
      <Users :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No parties registered</h4>
      <p class="state-desc">Add depositors, vendors, or transporters to manage inventory and transactions.</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Plus :size="16" />
        <span>Add New Party</span>
      </button>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.parties"
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
        <Column field="code" header="Code" sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Code"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="name" header="Party Name" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.name }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Name"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="type_display" header="Type" sortable>
          <template #body="{ data }">
            <span>{{ data.type_display || data.type }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <Select
              v-model="filterModel.value"
              @change="filterCallback()"
              :options="typeFilterOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Type"
              class="p-column-filter"
              size="small"
              showClear
            />
          </template>
        </Column>

        <Column field="phone" header="Phone">
          <template #body="{ data }">
            <div v-if="data.phone" class="cell-flex">
              <Phone :size="14" class="icon-muted" />
              <span>{{ data.phone }}</span>
            </div>
            <span v-else>-</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Phone"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="email" header="Email">
          <template #body="{ data }">
            <div v-if="data.email" class="cell-flex">
              <Mail :size="14" class="icon-muted" />
              <span>{{ data.email }}</span>
            </div>
            <span v-else>-</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Email"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="gstin" header="GSTIN">
          <template #body="{ data }">
            <span>{{ data.gstin || '-' }}</span>
          </template>
        </Column>

        <Column field="address" header="Address">
          <template #body="{ data }">
            <span>{{ data.address || '-' }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.master-list-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.cell-flex {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon-muted {
  color: var(--text-secondary);
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

<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Download, AlertCircle, RefreshCw, Package } from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import type { LotOutput } from '../../api/lot'
import type { FacilityOutput } from '../../api/facility'
import type { ChamberOutput, FloorOutput, BlockOutput } from '../../api/location'
import type { PartyOutput } from '../../api/party'

interface Props {
  lots: LotOutput[]
  facilities?: FacilityOutput[]
  chambers?: ChamberOutput[]
  floors?: FloorOutput[]
  blocks?: BlockOutput[]
  parties?: PartyOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedFacilityId?: number
  selectedChamberId?: number
  selectedFloorId?: number
  selectedBlockId?: number
  selectedPartyId?: number
  selectedStatus: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedFacilityId': [id: number | undefined]
  'update:selectedChamberId': [id: number | undefined]
  'update:selectedFloorId': [id: number | undefined]
  'update:selectedBlockId': [id: number | undefined]
  'update:selectedPartyId': [id: number | undefined]
  'update:selectedStatus': [status: string]
  retry: []
}>()

const statusOptions = [
  { label: 'Active Lots', value: 'active' },
  { label: 'Depleted Lots', value: 'depleted' },
  { label: 'All Lots', value: 'all' }
]

const facilityFilterOptions = computed(() => [
  { label: 'All Cold Storages', value: undefined },
  ...(props.facilities || []).map((f) => ({ label: f.name, value: f.id }))
])

const chamberFilterOptions = computed(() => [
  { label: 'All Chambers', value: undefined },
  ...(props.chambers || []).map((c) => ({ label: c.name, value: c.id }))
])

const floorFilterOptions = computed(() => [
  { label: 'All Floors', value: undefined },
  ...(props.floors || []).map((f) => ({ label: f.name, value: f.id }))
])

const blockFilterOptions = computed(() => [
  { label: 'All Blocks', value: undefined },
  ...(props.blocks || []).map((b) => ({ label: b.name, value: b.id }))
])

const partyFilterOptions = computed(() => [
  { label: 'All Parties', value: undefined },
  ...(props.parties || []).map((p) => ({ label: `${p.name} (${p.code})`, value: p.id }))
])

function buildDefaultFilters() {
  return {
    lot_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    facility_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    location_display: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    commodity_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    inward_date: { value: null, matchMode: FilterMatchMode.CONTAINS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (props.searchQuery && props.searchQuery.trim() !== '') count++
  if (props.selectedFacilityId !== undefined) count++
  if (props.selectedChamberId !== undefined) count++
  if (props.selectedFloorId !== undefined) count++
  if (props.selectedBlockId !== undefined) count++
  if (props.selectedPartyId !== undefined) count++
  if (props.selectedStatus && props.selectedStatus !== 'active') count++
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
  emit('update:selectedFacilityId', undefined)
  emit('update:selectedChamberId', undefined)
  emit('update:selectedFloorId', undefined)
  emit('update:selectedBlockId', undefined)
  emit('update:selectedPartyId', undefined)
  emit('update:selectedStatus', 'active')
}

const handleExport = () => {
  const headers = [
    'Lot No.',
    'Cold Storage',
    'Location',
    'Party',
    'Item / Product',
    'In Date',
    'In Qty',
    'Remaining Qty',
    'Status'
  ]
  const rows = props.lots.map((lot) => [
    lot.lot_number,
    lot.facility_name || '-',
    lot.location_display || '-',
    lot.party_name || '-',
    lot.commodity_name,
    lot.inward_date,
    formatQty(lot.initial_qty),
    formatQty(lot.remaining_qty),
    lot.remaining_qty > 0 ? 'Active' : 'Consumed'
  ])
  exportToCsv('inventory_lots.csv', headers, rows)
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
            placeholder="Search lot no., item..."
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedFacilityId"
          @update:modelValue="emit('update:selectedFacilityId', $event)"
          :options="facilityFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          placeholder="Cold Storage"
        />
        <Select
          :modelValue="selectedChamberId"
          @update:modelValue="emit('update:selectedChamberId', $event)"
          :options="chamberFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          placeholder="Chamber"
        />
        <Select
          :modelValue="selectedFloorId"
          @update:modelValue="emit('update:selectedFloorId', $event)"
          :options="floorFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedChamberId === undefined"
          placeholder="Floor"
        />
        <Select
          :modelValue="selectedBlockId"
          @update:modelValue="emit('update:selectedBlockId', $event)"
          :options="blockFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedFloorId === undefined"
          placeholder="Block"
        />
        <Select
          :modelValue="selectedPartyId"
          @update:modelValue="emit('update:selectedPartyId', $event)"
          :options="partyFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedFacilityId === undefined"
          :placeholder="selectedFacilityId === undefined ? 'Select a cold storage to filter by party' : 'Select Party'"
        />
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
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load inventory lots</h4>
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
    <div v-else-if="props.lots.length === 0" class="state-card empty-card">
      <Package :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No inventory lots found</h4>
      <p class="state-desc">Post a Goods Receipt Note (GRN) to populate stock inventory.</p>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.lots"
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
        <Column field="lot_number" header="Lot No." sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.lot_number }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Lot No."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="facility_name" header="Cold Storage" sortable>
          <template #body="{ data }">
            <span>{{ data.facility_name || '-' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Storage"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="party_name" header="Party" sortable>
          <template #body="{ data }">
            <span class="party-name" v-if="data.party_name">{{ data.party_name }}</span>
            <span v-else>-</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Party"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="commodity_name" header="Item / Product" sortable>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Item"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="location_display" header="Location" sortable>
          <template #body="{ data }">
            <span>{{ data.location_display || '—' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter Location"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="inward_date" header="In Date" sortable>
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

        <Column field="initial_qty" header="In Qty" sortable>
          <template #body="{ data }">
            <span class="num-val">{{ formatQty(data.initial_qty) }}</span>
          </template>
        </Column>

        <Column field="remaining_qty" header="Remaining Qty" sortable>
          <template #body="{ data }">
            <span class="num-val text-bold">{{ formatQty(data.remaining_qty) }}</span>
          </template>
        </Column>

        <Column header="Status">
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="data.remaining_qty > 0 ? 'success' : 'danger'"
            >
              {{ data.remaining_qty > 0 ? 'Active' : 'Consumed' }}
            </span>
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

.text-bold {
  font-weight: 700;
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

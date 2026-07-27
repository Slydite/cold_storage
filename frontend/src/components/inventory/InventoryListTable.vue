<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import { useI18n } from 'vue-i18n'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Download, AlertCircle, RefreshCw, Package, Eye } from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import { useToast } from 'primevue/usetoast'
import { fetchGrn } from '../../api/grn'
import type { GrnOutput } from '../../api/generated/types.gen'
import GrnDetailDialog from '../grn/GrnDetailDialog.vue'
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

const toast = useToast()
const { t } = useI18n()

const selectedGrn = ref<GrnOutput | null>(null)
const showGrnDetail = ref(false)
const fetchingLotId = ref<number | null>(null)

async function handleViewGrn(lot: LotOutput) {
  fetchingLotId.value = lot.id
  try {
    const grn = await fetchGrn(lot.grn_id)
    selectedGrn.value = grn
    showGrnDetail.value = true
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('grn.failedToLoad'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 5000
    })
  } finally {
    fetchingLotId.value = null
  }
}

const statusOptions = computed(() => [
  { label: t('inventory.activeLots'), value: 'active' },
  { label: t('inventory.depletedLots'), value: 'depleted' },
  { label: t('inventory.allLots'), value: 'all' }
])

const facilityFilterOptions = computed(() => [
  { label: t('common.allFacilities'), value: undefined },
  ...(props.facilities || []).map((f) => ({ label: f.name, value: f.id }))
])

const chamberFilterOptions = computed(() => [
  { label: t('common.allChambers'), value: undefined },
  ...(props.chambers || []).map((c) => ({ label: c.name, value: c.id }))
])

const floorFilterOptions = computed(() => [
  { label: t('common.allFloors'), value: undefined },
  ...(props.floors || []).map((f) => ({ label: f.name, value: f.id }))
])

const blockFilterOptions = computed(() => [
  { label: t('common.allBlocks'), value: undefined },
  ...(props.blocks || []).map((b) => ({ label: b.name, value: b.id }))
])

const partyFilterOptions = computed(() => [
  { label: t('common.allParties'), value: undefined },
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
    t('inventory.lotNo'),
    t('inventory.coldStorage'),
    t('inventory.location'),
    t('inventory.party'),
    t('inventory.itemProduct'),
    t('inventory.inDate'),
    t('inventory.inQty'),
    t('inventory.remainingQty'),
    t('common.status')
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
    lot.remaining_qty > 0 ? t('status.active') : t('inventory.consumed')
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
            :placeholder="t('inventory.searchPlaceholder')"
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
          :placeholder="t('inventory.coldStorage')"
        />
        <Select
          :modelValue="selectedChamberId"
          @update:modelValue="emit('update:selectedChamberId', $event)"
          :options="chamberFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :placeholder="t('locations.chamber')"
        />
        <Select
          :modelValue="selectedFloorId"
          @update:modelValue="emit('update:selectedFloorId', $event)"
          :options="floorFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedChamberId === undefined"
          :placeholder="t('locations.floor')"
        />
        <Select
          :modelValue="selectedBlockId"
          @update:modelValue="emit('update:selectedBlockId', $event)"
          :options="blockFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedFloorId === undefined"
          :placeholder="t('locations.block')"
        />
        <Select
          :modelValue="selectedPartyId"
          @update:modelValue="emit('update:selectedPartyId', $event)"
          :options="partyFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :disabled="selectedFacilityId === undefined"
          :placeholder="selectedFacilityId === undefined ? t('inventory.selectFacilityToFilterParty') : t('inventory.party')"
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
          <span>{{ t('common.filter') }}</span>
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
          <span>{{ t('common.clearFilters') }}</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>{{ t('common.export') }}</span>
        </button>
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">{{ t('inventory.failedToLoad') }}</h4>
      <p class="state-desc">{{ props.errorDetail || t('errors.generic') }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>{{ t('common.retry') }}</span>
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
      <h4 class="state-title">{{ t('inventory.noLotsFound') }}</h4>
      <p class="state-desc">{{ t('inventory.noLotsDesc') }}</p>
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
        <Column :header="t('common.actions')" style="width: 80px">
          <template #body="{ data }">
            <button
              class="icon-btn"
              :disabled="fetchingLotId !== null"
              :title="t('common.details')"
              type="button"
              @click="handleViewGrn(data)"
            >
              <i v-if="fetchingLotId === data.id" class="pi pi-spin pi-spinner" style="font-size: 1rem"></i>
              <Eye v-else :size="16" />
            </button>
          </template>
        </Column>

        <Column field="lot_number" :header="t('inventory.lotNo')" sortable>
          <template #body="{ data }">
            <span class="code-link clickable" @click="handleViewGrn(data)">{{ data.lot_number }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="`${t('common.filter')} ${t('inventory.lotNo')}`"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="facility_name" :header="t('inventory.coldStorage')" sortable>
          <template #body="{ data }">
            <span>{{ data.facility_name || '-' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="`${t('common.filter')} ${t('inventory.coldStorage')}`"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="party_name" :header="t('inventory.party')" sortable>
          <template #body="{ data }">
            <span class="party-name" v-if="data.party_name">{{ data.party_name }}</span>
            <span v-else>-</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="`${t('common.filter')} ${t('inventory.party')}`"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="commodity_name" :header="t('inventory.itemProduct')" sortable>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="`${t('common.filter')} ${t('common.commodity')}`"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="location_display" :header="t('inventory.location')" sortable>
          <template #body="{ data }">
            <span>{{ data.location_display || '—' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="`${t('common.filter')} ${t('inventory.location')}`"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="inward_date" :header="t('inventory.inDate')" sortable>
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

        <Column field="initial_qty" :header="t('inventory.inQty')" sortable>
          <template #body="{ data }">
            <span class="num-val">{{ formatQty(data.initial_qty) }}</span>
          </template>
        </Column>

        <Column field="remaining_qty" :header="t('inventory.remainingQty')" sortable>
          <template #body="{ data }">
            <span class="num-val text-bold">{{ formatQty(data.remaining_qty) }}</span>
          </template>
        </Column>

        <Column :header="t('common.status')">
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="data.remaining_qty > 0 ? 'success' : 'danger'"
            >
              {{ data.remaining_qty > 0 ? t('status.active') : t('inventory.consumed') }}
            </span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- GRN Detail Dialog -->
    <GrnDetailDialog
      v-model:visible="showGrnDetail"
      :grn="selectedGrn"
    />
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

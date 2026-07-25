<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Skeleton from 'primevue/skeleton'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Download, Plus, AlertCircle, RefreshCw, Layers } from 'lucide-vue-next'
import { formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters } from '../../composables/useTableFilters'
import type { RateCardOutput } from '../../api/billing'

interface Props {
  rateCards: RateCardOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  openCreate: []
  retry: []
}>()

const searchQuery = ref('')
const activeFilter = ref<'all' | 'active' | 'inactive'>('all')

const activeOptions = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Active Only', value: 'active' },
  { label: 'Inactive Only', value: 'inactive' }
]

function buildDefaultFilters() {
  return {
    commodity_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    weight_category_display: { value: null, matchMode: FilterMatchMode.CONTAINS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (searchQuery.value.trim() !== '') count++
  if (activeFilter.value !== 'all') count++
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
  searchQuery.value = ''
  activeFilter.value = 'all'
}

const filteredRateCards = computed(() => {
  let list = props.rateCards
  if (activeFilter.value === 'active') {
    list = list.filter((r) => r.is_active !== false)
  } else if (activeFilter.value === 'inactive') {
    list = list.filter((r) => r.is_active === false)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(
      (r) =>
        r.commodity_name.toLowerCase().includes(q) ||
        r.commodity_code.toLowerCase().includes(q) ||
        r.weight_category_display.toLowerCase().includes(q) ||
        (r.party_name && r.party_name.toLowerCase().includes(q)) ||
        (!r.party_name && 'default'.includes(q))
    )
  }
  return list
})

const handleExport = () => {
  const headers = ['Commodity', 'Code', 'Applies To', 'Weight Category', 'Rate (₹/bag/month)', 'Effective From', 'Active']
  const rows = filteredRateCards.value.map((rc) => [
    rc.commodity_name,
    rc.commodity_code,
    rc.party_name || 'Default',
    rc.weight_category_display,
    formatCurrency(Number(rc.rate_per_bag_per_month)),
    rc.effective_from,
    rc.is_active !== false ? 'Yes' : 'No'
  ])
  exportToCsv('rate_cards.csv', headers, rows)
}
</script>

<template>
  <div class="rate-card-table-wrapper">
    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search commodity, party, or category..."
            class="custom-search-input"
          />
        </div>
        <Select
          v-model="activeFilter"
          :options="activeOptions"
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
          <span>Export CSV</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('openCreate')">
          <Plus :size="16" />
          <span>New Rate Card</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load Rate Cards</h4>
      <p class="state-desc">{{ props.errorDetail || 'There was an issue connecting to the server. Please try again.' }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Loading Skeleton State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="48px" class="mb-2" v-for="i in 4" :key="i" />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredRateCards.length === 0" class="state-card empty-card">
      <Layers :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No rate cards yet</h4>
      <p class="state-desc">No rate cards found. Add a rate card to enable storage rent calculations for incoming lots.</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Plus :size="16" />
        <span>Add Rate Card</span>
      </button>
    </div>

    <!-- Happy Path: DataTable -->
    <div v-else class="table-card">
      <DataTable
        :value="filteredRateCards"
        v-model:filters="filters"
        :filterDisplay="showFilterRow ? 'row' : 'menu'"
        paginator
        :rows="5"
        :rowsPerPageOptions="[5, 10, 25]"
        sortMode="multiple"
        removableSort
        size="small"
        stripedRows
        dataKey="id"
        responsiveLayout="scroll"
      >
        <Column field="commodity_name" header="Commodity" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.commodity_name }}</span>
            <span class="code-sub"> ({{ data.commodity_code }})</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter commodity..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="party_name" header="Applies To" sortable>
          <template #body="{ data }">
            <span v-if="data.party_name" class="party-name">{{ data.party_name }}</span>
            <span v-else class="status-pill info">Default (All Parties)</span>
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

        <Column field="weight_category_display" header="Weight Category" sortable>
          <template #body="{ data }">
            <span>{{ data.weight_category_display }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter category..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="rate_per_bag_per_month" header="Rate / Bag / Month" sortable>
          <template #body="{ data }">
            <span class="num-val bold-val">{{ formatCurrency(Number(data.rate_per_bag_per_month)) }}</span>
          </template>
        </Column>

        <Column field="effective_from" header="Effective From" sortable />

        <Column field="is_active" header="Active" sortable>
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="data.is_active !== false ? 'success' : 'warning'"
            >
              {{ data.is_active !== false ? 'Active' : 'Inactive' }}
            </span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.rate-card-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-sub {
  font-size: 12px;
  color: var(--text-secondary);
}

.bold-val {
  font-weight: 700;
  color: var(--accent-primary);
}

.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 36px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.state-icon.text-danger {
  color: var(--status-danger-color);
}

.state-icon.text-muted {
  color: var(--text-secondary);
}

.state-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.state-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  max-width: 360px;
  margin-bottom: 6px;
}

.skeleton-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>

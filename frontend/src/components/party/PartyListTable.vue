<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Filter,
  FilterX,
  Download,
  Plus,
  AlertCircle,
  RefreshCw,
  Users
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n()

const typeFilterOptions = computed(() => [
  { label: t('common.allTypes'), value: 'all' },
  { label: t('parties.depositorCustomer'), value: 'DEPOSITOR' },
  { label: t('parties.vendor'), value: 'VENDOR' },
  { label: t('parties.transporter'), value: 'TRANSPORTER' }
])

function buildDefaultFilters() {
  return {
    code: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    type: { value: null, matchMode: FilterMatchMode.EQUALS },
    phone: { value: null, matchMode: FilterMatchMode.CONTAINS },
    email: { value: null, matchMode: FilterMatchMode.CONTAINS },
    gstin: { value: null, matchMode: FilterMatchMode.CONTAINS }
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
  const headers = [
    t('parties.code'),
    t('parties.partyName'),
    t('parties.partyType'),
    t('parties.phone'),
    t('parties.email'),
    t('parties.gstin')
  ]
  const rows = props.parties.map((p) => [
    p.code,
    p.name,
    p.type,
    p.phone || '-',
    p.email || '-',
    p.gstin || '-'
  ])
  exportToCsv('parties.csv', headers, rows)
}

const getTypeSeverity = (type?: string) => {
  switch (type) {
    case 'DEPOSITOR':
      return 'info'
    case 'VENDOR':
      return 'warn'
    case 'TRANSPORTER':
      return 'secondary'
    default:
      return 'secondary'
  }
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
            :placeholder="t('parties.searchPlaceholder')"
            class="custom-search-input"
          />
        </div>

        <Select
          :modelValue="selectedType"
          @update:modelValue="emit('update:selectedType', $event)"
          :options="typeFilterOptions"
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
          <span>{{ t('common.clear') }}</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>{{ t('common.export') }}</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('openCreate')">
          <Plus :size="16" />
          <span>{{ t('parties.addParty') }}</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">{{ t('parties.failedToLoad') }}</h4>
      <p class="state-desc">{{ props.errorDetail || t('errors.network') }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>{{ t('common.retry') }}</span>
      </button>
    </div>

    <!-- Skeleton Loading State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="56px" class="mb-2" v-for="i in 5" :key="i" />
    </div>

    <!-- Empty State -->
    <div v-else-if="props.parties.length === 0" class="state-card empty-card">
      <Users :size="40" class="state-icon text-muted" />
      <h4 class="state-title">{{ t('parties.noPartiesRegistered') }}</h4>
      <p class="state-desc">{{ t('parties.noPartiesDesc') }}</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Plus :size="16" />
        <span>{{ t('parties.addNewParty') }}</span>
      </button>
    </div>

    <!-- DataTable View -->
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
        <Column field="code" :header="t('parties.code')" sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="name" :header="t('parties.partyName')" sortable>
          <template #body="{ data }">
            <strong class="party-name">{{ data.name }}</strong>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              placeholder="Filter..."
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="type" :header="t('parties.partyType')" sortable>
          <template #body="{ data }">
            <Tag
              :value="t(`partyType.${data.type}`, data.type)"
              :severity="getTypeSeverity(data.type)"
            />
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <Select
              v-model="filterModel.value"
              @change="filterCallback()"
              :options="typeFilterOptions.filter(o => o.value !== 'all')"
              optionLabel="label"
              optionValue="value"
              :placeholder="t('parties.partyType')"
              class="p-column-filter"
              size="small"
              showClear
            />
          </template>
        </Column>

        <Column field="phone" :header="t('parties.phone')" sortable>
          <template #body="{ data }">
            <span>{{ data.phone || '—' }}</span>
          </template>
        </Column>

        <Column field="email" :header="t('parties.email')" sortable>
          <template #body="{ data }">
            <span>{{ data.email || '—' }}</span>
          </template>
        </Column>

        <Column field="gstin" :header="t('parties.gstin')" sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.gstin || '—' }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.master-list-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

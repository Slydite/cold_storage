<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Filter,
  Download,
  Plus,
  Eye,
  AlertCircle,
  RefreshCw,
  Package,
  FileCheck,
  XCircle
} from 'lucide-vue-next'
import { chamberOptions } from '../../constants/chambers'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { GrnOutput } from '../../api/grn'

interface Props {
  grns: GrnOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedChamber: string
  selectedPeriod: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedChamber': [chamber: string]
  'update:selectedPeriod': [period: string]
  openCreate: []
  retry: []
  view: [grn: GrnOutput]
  post: [id: number]
  cancel: [id: number]
}>()

const periodOptions = [
  { label: 'This Month', value: 'this_month' },
  { label: 'Today', value: 'today' },
  { label: 'All Time', value: 'all_time' }
]

const filters = ref({
  grn_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
  receipt_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
  party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  status: { value: null, matchMode: FilterMatchMode.EQUALS }
})

function computeNetWeight(grn: GrnOutput): number {
  if (!grn.lots || grn.lots.length === 0) return 0
  return grn.lots.reduce((sum, lot) => {
    const qty = lot.initial_qty || 0
    const unitW = lot.unit_weight ? parseFloat(lot.unit_weight) : 1
    return sum + qty * unitW
  }, 0)
}

const handleExport = () => {
  const headers = ['GRN No.', 'GRN Date', 'Party', 'Net Weight (MT)', 'Status']
  const rows = props.grns.map((grn) => [
    grn.grn_number,
    grn.receipt_date,
    grn.party_name,
    formatQty(computeNetWeight(grn)),
    grn.status || '-'
  ])
  exportToCsv('grns.csv', headers, rows)
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
            placeholder="Search GRN no., party..."
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedChamber"
          @update:modelValue="emit('update:selectedChamber', $event)"
          :options="chamberOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
        />
        <Select
          :modelValue="selectedPeriod"
          @update:modelValue="emit('update:selectedPeriod', $event)"
          :options="periodOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
        />
      </div>

      <div class="toolbar-actions">
        <button class="btn-outlined" type="button">
          <Filter :size="15" />
          <span>Filters</span>
        </button>
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>Export</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('openCreate')">
          <Plus :size="16" />
          <span>New GRN</span>
        </button>
      </div>
    </div>

    <!-- Explicit State 1: Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load GRN records</h4>
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
    <div v-else-if="props.grns.length === 0" class="state-card empty-card">
      <Package :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No Goods Receipt Notes found</h4>
      <p class="state-desc">Get started by recording your first inward inventory GRN entry.</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Plus :size="16" />
        <span>Create New GRN</span>
      </button>
    </div>

    <!-- Happy Path: DataTable View -->
    <div v-else class="table-card">
      <DataTable
        :value="props.grns"
        v-model:filters="filters"
        filterDisplay="menu"
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
        <Column field="grn_number" header="GRN No." sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.grn_number }}</span>
          </template>
        </Column>

        <Column field="receipt_date" header="GRN Date" sortable />

        <Column field="party_name" header="Party" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.party_name }}</span>
          </template>
        </Column>

        <Column header="Net Weight (MT)">
          <template #body="{ data }">
            <span class="num-val">{{ formatQty(computeNetWeight(data)) }}</span>
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
                title="Post GRN"
                type="button"
                @click="emit('post', data.id)"
              >
                <FileCheck :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn danger-hover"
                title="Cancel GRN"
                type="button"
                @click="emit('cancel', data.id)"
              >
                <XCircle :size="16" />
              </button>
            </div>
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
  transition: all 0.25s ease;
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

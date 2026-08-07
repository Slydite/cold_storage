<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
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
  Package,
  FileCheck,
  XCircle,
  Printer,
  Pencil
} from 'lucide-vue-next'
import { formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import { downloadPdf } from '../../utils/downloadPdf'
import type { GrnOutput } from '../../api/grn'
import type { ChamberOutput } from '../../api/location'

interface Props {
  grns: GrnOutput[]
  chambers: ChamberOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
  searchQuery: string
  selectedChamberId?: number
  selectedPeriod: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [query: string]
  'update:selectedChamberId': [chamberId: number | undefined]
  'update:selectedPeriod': [period: string]
  openCreate: []
  retry: []
  view: [grn: GrnOutput]
  edit: [grn: GrnOutput]
  post: [id: number]
  cancel: [id: number]
}>()

const toast = useToast()
const { t } = useI18n()
const downloadingId = ref<number | null>(null)

async function handleDownloadPdf(id: number, docNumber: string) {
  downloadingId.value = id
  try {
    await downloadPdf(`/api/grns/${id}/pdf/`, `${docNumber}.pdf`)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.pdfFailed'),
      detail: err instanceof Error ? err.message : t('common.pdfFailed'),
      life: 5000
    })
  } finally {
    downloadingId.value = null
  }
}

const periodOptions = computed(() => [
  { label: t('common.all'), value: 'all_time' },
  { label: t('common.date'), value: 'this_month' }
])

const statusFilterOptions = computed(() => [
  { label: t('status.posted'), value: 'POSTED' },
  { label: t('status.draft'), value: 'DRAFT' },
  { label: t('status.cancelled'), value: 'CANCELLED' }
])

function buildDefaultFilters() {
  return {
    grn_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    receipt_date: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS }
  }
}

const chamberFilterOptions = computed(() => [
  { label: t('common.allChambers'), value: undefined as number | undefined },
  ...props.chambers.map((c) => ({ label: c.name, value: c.id as number | undefined }))
])

const extraActiveCount = computed(() => {
  let count = 0
  if (props.searchQuery && props.searchQuery.trim() !== '') count++
  if (props.selectedChamberId !== undefined) count++
  if (props.selectedPeriod && props.selectedPeriod !== 'this_month') count++
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
  emit('update:selectedChamberId', undefined)
  emit('update:selectedPeriod', 'this_month')
}

function computeNetWeight(grn: GrnOutput): number {
  if (!grn.lots || grn.lots.length === 0) return 0
  return grn.lots.reduce((sum, lot) => {
    const qty = lot.initial_qty || 0
    const unitW = lot.unit_weight ? parseFloat(lot.unit_weight) : 1
    return sum + qty * unitW
  }, 0)
}

const handleExport = () => {
  const headers = [
    t('grn.grnNumber'),
    t('common.date'),
    t('grn.party'),
    t('grn.totalNetWeightMt'),
    t('common.status')
  ]
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
            :placeholder="t('grn.searchPlaceholder')"
            class="custom-search-input"
          />
        </div>
        <Select
          :modelValue="selectedChamberId"
          @update:modelValue="emit('update:selectedChamberId', $event ?? undefined)"
          :options="chamberFilterOptions"
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
          <span>{{ t('grn.create') }}</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">{{ t('grn.failedToLoad') }}</h4>
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
    <div v-else-if="props.grns.length === 0" class="state-card empty-card">
      <Package :size="40" class="state-icon text-muted" />
      <h4 class="state-title">{{ t('grn.noGrnsFound') }}</h4>
      <p class="state-desc">{{ t('grn.noGrnsDesc') }}</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Plus :size="16" />
        <span>{{ t('grn.createNewGrn') }}</span>
      </button>
    </div>

    <!-- DataTable View & Mobile Cards -->
    <template v-else>
      <div class="table-card hide-on-mobile">
        <DataTable
          :value="props.grns"
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
          <Column :header="t('common.actions')">
            <template #body="{ data }">
              <div class="row-actions">
                <button class="icon-btn" :title="t('common.details')" type="button" @click="emit('view', data)">
                  <Eye :size="16" />
                </button>
                <button
                  v-if="data.status === 'DRAFT'"
                  class="icon-btn"
                  :title="t('common.edit')"
                  type="button"
                  @click="emit('edit', data)"
                >
                  <Pencil :size="16" />
                </button>
                <button
                  v-if="data.status === 'DRAFT'"
                  class="icon-btn"
                  :title="t('grn.postTooltip')"
                  type="button"
                  @click="emit('post', data.id)"
                >
                  <FileCheck :size="16" />
                </button>
                <button
                  v-if="data.status === 'DRAFT'"
                  class="icon-btn danger-hover"
                  :title="t('grn.cancelTooltip')"
                  type="button"
                  @click="emit('cancel', data.id)"
                >
                  <XCircle :size="16" />
                </button>
                <button
                  class="icon-btn"
                  title="PDF"
                  aria-label="PDF"
                  type="button"
                  :disabled="downloadingId === data.id"
                  @click="handleDownloadPdf(data.id, data.grn_number)"
                >
                  <Printer :size="16" />
                </button>
              </div>
            </template>
          </Column>

          <Column field="grn_number" :header="t('grn.grnNumber')" sortable style="min-width: 11rem">
            <template #body="{ data }">
              <span class="code-link clickable doc-number" @click="emit('view', data)">{{ data.grn_number }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText
                v-model="filterModel.value"
                type="text"
                @input="filterCallback()"
                :placeholder="t('grn.filterPlaceholder')"
                class="p-column-filter"
                size="small"
              />
            </template>
          </Column>

          <Column field="receipt_date" :header="t('common.date')" sortable>
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

          <Column field="party_name" :header="t('grn.party')" sortable>
            <template #body="{ data }">
              <span class="party-name">{{ data.party_name }}</span>
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

          <Column :header="t('grn.totalNetWeightMt')">
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(computeNetWeight(data)) }}</span>
            </template>
          </Column>

          <Column field="status" :header="t('common.status')" sortable>
            <template #body="{ data }">
              <span
                class="status-pill"
                :class="{
                  success: data.status === 'POSTED',
                  warning: data.status === 'DRAFT',
                  danger: data.status === 'CANCELLED'
                }"
              >
                {{ t(`status.${(data.status || 'draft').toLowerCase()}`) }}
              </span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <Select
                v-model="filterModel.value"
                @change="filterCallback()"
                :options="statusFilterOptions"
                optionLabel="label"
                optionValue="value"
                :placeholder="t('common.status')"
                class="p-column-filter"
                size="small"
                showClear
              />
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Mobile Card Layout -->
      <div class="mobile-list-cards show-on-mobile">
        <div v-for="data in props.grns" :key="data.id" class="mobile-list-card">
          <div class="card-header clickable" @click="emit('view', data)">
            <span class="card-title doc-number">{{ data.grn_number }}</span>
            <span
              class="status-pill"
              :class="{
                success: data.status === 'POSTED',
                warning: data.status === 'DRAFT',
                danger: data.status === 'CANCELLED'
              }"
            >
              {{ t(`status.${(data.status || 'draft').toLowerCase()}`) }}
            </span>
          </div>
          <div class="card-body">
            <div class="card-row">
              <span class="card-label">{{ t('common.date') }}:</span>
              <span class="card-value">{{ data.receipt_date }}</span>
            </div>
            <div class="card-row">
              <span class="card-label">{{ t('grn.party') }}:</span>
              <span class="card-value">{{ data.party_name }}</span>
            </div>
            <div class="card-row">
              <span class="card-label">{{ t('grn.totalNetWeightMt') }}:</span>
              <span class="card-value num-val">{{ formatQty(computeNetWeight(data)) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-outlined btn-sm" :title="t('common.details')" type="button" @click="emit('view', data)">
              <Eye :size="15" />
              <span>{{ t('common.details') }}</span>
            </button>
            <button
              v-if="data.status === 'DRAFT'"
              class="btn-outlined btn-sm"
              :title="t('common.edit')"
              type="button"
              @click="emit('edit', data)"
            >
              <Pencil :size="15" />
              <span>{{ t('common.edit') }}</span>
            </button>
            <button
              v-if="data.status === 'DRAFT'"
              class="btn-outlined btn-sm"
              :title="t('grn.postTooltip')"
              type="button"
              @click="emit('post', data.id)"
            >
              <FileCheck :size="15" />
              <span>{{ t('grn.postTooltip') }}</span>
            </button>
            <button
              v-if="data.status === 'DRAFT'"
              class="btn-outlined btn-sm danger-hover"
              :title="t('grn.cancelTooltip')"
              type="button"
              @click="emit('cancel', data.id)"
            >
              <XCircle :size="15" />
              <span>{{ t('grn.cancelTooltip') }}</span>
            </button>
            <button
              class="btn-outlined btn-sm"
              title="PDF"
              aria-label="PDF"
              type="button"
              :disabled="downloadingId === data.id"
              @click="handleDownloadPdf(data.id, data.grn_number)"
            >
              <Printer :size="15" />
              <span>{{ downloadingId === data.id ? '...' : 'PDF' }}</span>
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.code-link.clickable {
  cursor: pointer;
}
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

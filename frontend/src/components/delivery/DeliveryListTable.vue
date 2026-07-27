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
import Tag from 'primevue/tag'
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
import { downloadPdf } from '../../utils/downloadPdf'
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
  view: [dn: DeliveryNoteOutput]
  post: [id: number]
  cancel: [id: number]
}>()

const toast = useToast()
const { t } = useI18n()
const downloadingId = ref<number | null>(null)

async function handleDownloadPdf(id: number, docNumber: string) {
  downloadingId.value = id
  try {
    await downloadPdf(`/api/deliveries/${id}/pdf/`, `${docNumber}.pdf`)
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

const statusOptions = computed(() => [
  { label: t('common.allStatuses'), value: 'all' },
  { label: t('status.posted'), value: 'POSTED' },
  { label: t('status.draft'), value: 'DRAFT' },
  { label: t('status.cancelled'), value: 'CANCELLED' }
])

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

function computeTotalQuantity(dn: DeliveryNoteOutput): number {
  if (!dn.lines || dn.lines.length === 0) return 0
  return dn.lines.reduce((sum, line) => sum + (line.qty || 0), 0)
}

const handleExport = () => {
  const headers = [
    t('delivery.deliveryNumber'),
    t('delivery.dispatchDate'),
    t('delivery.customerParty'),
    t('delivery.vehicleNo'),
    t('delivery.totalDispatchQty'),
    t('common.status')
  ]
  const rows = props.deliveries.map((dn) => [
    dn.dn_number,
    dn.dispatch_date,
    dn.party_name,
    dn.vehicle_number || '-',
    formatQty(computeTotalQuantity(dn), 0),
    dn.status || '-'
  ])
  exportToCsv('deliveries.csv', headers, rows)
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
            :placeholder="t('delivery.searchPlaceholder')"
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
        <button class="btn-primary" type="button" @click="emit('newDelivery')">
          <Plus :size="16" />
          <span>{{ t('delivery.newDeliveryDn') }}</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">{{ t('delivery.failedToLoad') }}</h4>
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
    <div v-else-if="props.deliveries.length === 0" class="state-card empty-card">
      <Truck :size="40" class="state-icon text-muted" />
      <h4 class="state-title">{{ t('delivery.noDeliveriesFound') }}</h4>
      <p class="state-desc">{{ t('delivery.noDeliveriesDesc') }}</p>
      <button class="btn-primary" type="button" @click="emit('newDelivery')">
        <Plus :size="16" />
        <span>{{ t('delivery.newDeliveryDn') }}</span>
      </button>
    </div>

    <!-- DataTable View -->
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
        <Column field="dn_number" :header="t('delivery.deliveryNumber')" sortable>
          <template #body="{ data }">
            <span class="code-link clickable" @click="emit('view', data)">{{ data.dn_number }}</span>
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

        <Column field="dispatch_date" :header="t('delivery.dispatchDate')" sortable>
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

        <Column field="party_name" :header="t('delivery.customerParty')" sortable>
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

        <Column field="vehicle_number" :header="t('delivery.vehicleNo')" sortable>
          <template #body="{ data }">
            <span>{{ data.vehicle_number || '-' }}</span>
          </template>
        </Column>

        <Column :header="t('delivery.totalDispatchQty')">
          <template #body="{ data }">
            <strong class="num-val">{{ formatQty(computeTotalQuantity(data), 0) }}</strong>
          </template>
        </Column>

        <Column field="status" :header="t('common.status')" sortable>
          <template #body="{ data }">
            <Tag
              :value="t(`status.${(data.status || 'draft').toLowerCase()}`)"
              :severity="data.status === 'POSTED' ? 'success' : data.status === 'CANCELLED' ? 'danger' : 'warn'"
            />
          </template>
        </Column>

        <Column :header="t('common.actions')">
          <template #body="{ data }">
            <div class="row-actions">
              <button class="icon-btn" :title="t('common.details')" type="button" @click="emit('view', data)">
                <Eye :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn"
                title="Post DN"
                type="button"
                @click="emit('post', data.id)"
              >
                <FileCheck :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn danger-hover"
                title="Cancel DN"
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
                @click="handleDownloadPdf(data.id, data.dn_number)"
              >
                <Printer :size="16" />
              </button>
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

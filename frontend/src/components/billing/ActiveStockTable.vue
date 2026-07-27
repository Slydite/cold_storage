<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import { FilterMatchMode } from '@primevue/core/api'
import { Search, Filter, FilterX, Download, Eye } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { formatCurrency, formatQty } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import { useTableFilters, formatDateFilter } from '../../composables/useTableFilters'
import { useChamberList } from '../../composables/useLocations'
import { useFacility } from '../../composables/useFacility'
import { useToast } from 'primevue/usetoast'
import { fetchGrn } from '../../api/grn'
import type { GrnOutput } from '../../api/generated/types.gen'
import GrnDetailDialog from '../grn/GrnDetailDialog.vue'
import type { LotOutput } from '../../api/lot'

const props = defineProps<{
  lots: LotOutput[]
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

const searchQuery = ref('')
const selectedChamberId = ref<number | undefined>(undefined)

function buildDefaultFilters() {
  return {
    lot_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
    party_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    commodity_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    inward_date: { value: null, matchMode: FilterMatchMode.CONTAINS }
  }
}

const extraActiveCount = computed(() => {
  let count = 0
  if (searchQuery.value.trim() !== '') count++
  if (selectedChamberId.value !== undefined) count++
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

const { facilityId } = useFacility()
const chambersQuery = useChamberList({ facilityId })

const chamberFilterOptions = computed(() => [
  { label: t('common.allChambers'), value: undefined },
  ...(chambersQuery.data.value || []).map((c) => ({ label: c.name, value: c.id }))
])

const filteredLots = computed(() => {
  return props.lots.filter((lot) => {
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim()
      const matchSearch =
        lot.lot_number.toLowerCase().includes(q) ||
        (lot.party_name && lot.party_name.toLowerCase().includes(q)) ||
        lot.commodity_name.toLowerCase().includes(q)
      if (!matchSearch) return false
    }
    if (selectedChamberId.value !== undefined) {
      if (lot.chamber_ref_id !== selectedChamberId.value) return false
    }
    return true
  })
})

function handleClearAll() {
  clearFilters()
  searchQuery.value = ''
  selectedChamberId.value = undefined
}

const handleExport = () => {
  const headers = [
    t('inventory.lotNo'),
    t('inventory.party'),
    t('grn.commodityProduct'),
    t('inventory.location'),
    t('inventory.remainingQty'),
    t('billing.agreedRentRate')
  ]
  const rows = filteredLots.value.map((lot) => [
    lot.lot_number,
    lot.party_name || '-',
    lot.commodity_name,
    lot.location_display || [lot.chamber_name || lot.chamber, lot.floor_name || lot.floor].filter(Boolean).join(' / ') || '-',
    formatQty(lot.remaining_qty, 0),
    lot.rent_rate_per_unit ? t('billing.rentRatePerUnit', { rate: formatCurrency(Number(lot.rent_rate_per_unit)) }) : '-'
  ])
  exportToCsv('active_stock.csv', headers, rows)
}
</script>

<template>
  <div class="billing-section">
    <div class="section-header">
      <h3 class="section-title">{{ t('billing.accruingStockTitle') }}</h3>
      <p class="section-desc">{{ t('billing.accruingStockDesc') }}</p>
    </div>

    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('inventory.searchPlaceholder')"
            class="custom-search-input"
          />
        </div>

        <Select
          v-model="selectedChamberId"
          :options="chamberFilterOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
          :placeholder="t('locations.chamber')"
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
      </div>
    </div>

    <div class="table-card">
      <div v-if="filteredLots.length === 0" class="empty-section">
        <p>{{ t('common.noRecordsFound') }}</p>
      </div>

      <DataTable
        v-else
        :value="filteredLots"
        v-model:filters="filters"
        :filterDisplay="showFilterRow ? 'row' : 'menu'"
        size="small"
        stripedRows
        paginator
        :rows="8"
        :rowsPerPageOptions="[8, 20, 50]"
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
              :placeholder="t('common.filter')"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="party_name" :header="t('inventory.party')" sortable>
          <template #body="{ data }">
            <strong>{{ data.party_name || '—' }}</strong>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="t('common.filter')"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column field="commodity_name" :header="t('grn.commodityProduct')" sortable>
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              type="text"
              @input="filterCallback()"
              :placeholder="t('common.filter')"
              class="p-column-filter"
              size="small"
            />
          </template>
        </Column>

        <Column :header="t('inventory.location')">
          <template #body="{ data }">
            <span>{{ data.location_display || [data.chamber_name || data.chamber, data.floor_name || data.floor].filter(Boolean).join(' / ') || '—' }}</span>
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

        <Column field="remaining_qty" :header="t('inventory.remainingQty')">
          <template #body="{ data }">
            <strong class="num-val">{{ formatQty(data.remaining_qty, 0) }} {{ data.commodity_unit ? t(`units.${data.commodity_unit}`, data.commodity_unit) : '' }}</strong>
          </template>
        </Column>

        <Column field="rent_rate_per_unit" :header="t('billing.agreedRentRate')">
          <template #body="{ data }">
            <span class="num-val">
              {{ data.rent_rate_per_unit ? t('billing.rentRatePerUnit', { rate: formatCurrency(Number(data.rent_rate_per_unit)) }) : '—' }}
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
.billing-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
}

.empty-section {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>

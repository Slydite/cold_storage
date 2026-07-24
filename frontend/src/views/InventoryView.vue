<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import { Search, Filter, Download } from 'lucide-vue-next'
import { chamberOptions } from '../constants/chambers'
import { formatQty } from '../utils/format'
import { useSearchFilter } from '../composables/useSearchFilter'

const selectedChamber = ref('all')
const selectedStatus = ref('active')

const statusOptions = [
  { label: 'Active Lots', value: 'active' },
  { label: 'Depleted Lots', value: 'depleted' },
  { label: 'All Lots', value: 'all' }
]

const lots = ref([
  { id: '1', lotNo: 'LOT-000086', product: 'Frozen Green Peas', party: 'Shree Traders', chamber: 'Chamber A', inDate: '20 May 2024', totalQty: 2.500, remainingQty: 1.750, status: 'Active' },
  { id: '2', lotNo: 'LOT-000085', product: 'Frozen Sweet Corn', party: 'Shree Traders', chamber: 'Chamber A', inDate: '20 May 2024', totalQty: 2.000, remainingQty: 2.000, status: 'Active' },
  { id: '3', lotNo: 'LOT-000084', product: 'Frozen Cauliflower', party: 'Shree Traders', chamber: 'Chamber B', inDate: '20 May 2024', totalQty: 3.000, remainingQty: 0.500, status: 'Active' },
  { id: '4', lotNo: 'LOT-000083', product: 'Frozen Okra', party: 'Kisan Exports', chamber: 'Chamber C', inDate: '18 May 2024', totalQty: 1.800, remainingQty: 1.200, status: 'Active' },
  { id: '5', lotNo: 'LOT-000082', product: 'Frozen Mixed Veg', party: 'Kisan Exports', chamber: 'Chamber C', inDate: '18 May 2024', totalQty: 2.250, remainingQty: 1.750, status: 'Active' }
])

const { searchQuery, filtered: searchedLots } = useSearchFilter(lots, (lot, query) =>
  lot.lotNo.toLowerCase().includes(query) ||
  lot.product.toLowerCase().includes(query) ||
  lot.party.toLowerCase().includes(query)
)

const filteredLots = computed(() =>
  searchedLots.value.filter(
    (lot) => selectedChamber.value === 'all' || lot.chamber === selectedChamber.value
  )
)
</script>

<template>
  <div class="page-container">
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search lot no., item, party..."
            class="custom-search-input"
          />
        </div>
        <Select v-model="selectedChamber" :options="chamberOptions" optionLabel="label" optionValue="value" class="toolbar-select" />
        <Select v-model="selectedStatus" :options="statusOptions" optionLabel="label" optionValue="value" class="toolbar-select" />
      </div>

      <div class="toolbar-actions">
        <button class="btn-outlined"><Filter :size="15" /><span>Filters</span></button>
        <button class="btn-outlined"><Download :size="15" /><span>Export</span></button>
      </div>
    </div>

    <div class="table-card">
      <DataTable :value="filteredLots" paginator :rows="5" responsiveLayout="scroll" class="custom-datatable">
        <Column field="lotNo" header="Lot No." sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.lotNo }}</span>
          </template>
        </Column>

        <Column field="product" header="Item / Product" sortable />
        <Column field="party" header="Party" sortable />
        <Column field="chamber" header="Chamber" sortable />
        <Column field="inDate" header="In Date" sortable />

        <Column field="totalQty" header="In Qty (MT)" sortable>
          <template #body="{ data }">
            <span class="num-val">{{ formatQty(data.totalQty) }}</span>
          </template>
        </Column>

        <Column field="remainingQty" header="Remaining Qty (MT)" sortable>
          <template #body="{ data }">
            <span class="num-val text-bold">{{ formatQty(data.remainingQty) }}</span>
          </template>
        </Column>

        <Column field="status" header="Status">
          <template #body="{ data }">
            <span class="status-pill success">{{ data.status }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.text-bold {
  font-weight: 700;
}
</style>

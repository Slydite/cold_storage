<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import { Search, Plus, Download, Phone } from 'lucide-vue-next'
import { useSearchFilter } from '../composables/useSearchFilter'

const selectedType = ref('all')

const typeOptions = [
  { label: 'All Parties', value: 'all' },
  { label: 'Customers', value: 'customer' },
  { label: 'Suppliers', value: 'supplier' }
]

const parties = ref([
  { id: '1', name: 'Shree Traders', code: 'PRT-001', type: 'Customer', contact: 'Rajesh Shah', phone: '+91 98250 12345', email: 'rajesh@shreetraders.com', activeLots: 12, balance: '₹ 1,45,200' },
  { id: '2', name: 'Kisan Exports', code: 'PRT-002', type: 'Customer', contact: 'Vikram Patel', phone: '+91 98980 67890', email: 'info@kisanexports.in', activeLots: 8, balance: '₹ 84,500' },
  { id: '3', name: 'Arctic Foods', code: 'PRT-003', type: 'Supplier', contact: 'Suresh Kumar', phone: '+91 94260 54321', email: 'suresh@arcticfoods.com', activeLots: 5, balance: '₹ 0' },
  { id: '4', name: 'Global Frozen Pvt Ltd', code: 'PRT-004', type: 'Customer', contact: 'Animesh Roy', phone: '+91 97129 11223', email: 'contact@globalfrozen.com', activeLots: 15, balance: '₹ 3,20,000' }
])

const { searchQuery, filtered: filteredParties } = useSearchFilter(parties, (p, query) =>
  p.name.toLowerCase().includes(query) || p.code.toLowerCase().includes(query)
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
            placeholder="Search party name, code..."
            class="custom-search-input"
          />
        </div>
        <Select v-model="selectedType" :options="typeOptions" optionLabel="label" optionValue="value" class="toolbar-select" />
      </div>

      <div class="toolbar-actions">
        <button class="btn-outlined"><Download :size="15" /><span>Export</span></button>
        <button class="btn-primary"><Plus :size="16" /><span>Add Party</span></button>
      </div>
    </div>

    <div class="table-card">
      <DataTable :value="filteredParties" paginator :rows="5" responsiveLayout="scroll" class="custom-datatable">
        <Column field="code" header="Code" sortable>
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" header="Party Name" sortable>
          <template #body="{ data }">
            <span class="party-name">{{ data.name }}</span>
          </template>
        </Column>

        <Column field="type" header="Type" sortable />
        <Column field="contact" header="Contact Person" />

        <Column field="phone" header="Phone">
          <template #body="{ data }">
            <div class="cell-flex"><Phone :size="14" class="icon-muted" /><span>{{ data.phone }}</span></div>
          </template>
        </Column>

        <Column field="activeLots" header="Active Lots" sortable>
          <template #body="{ data }">
            <span class="num-val">{{ data.activeLots }}</span>
          </template>
        </Column>

        <Column field="balance" header="Outstanding (₹)" sortable>
          <template #body="{ data }">
            <span class="num-val highlight">{{ data.balance }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.cell-flex {
  display: flex;
  align-items: center;
  gap: 6px;
}
.icon-muted {
  color: var(--text-secondary);
}
.highlight {
  font-weight: 700;
  color: var(--status-warning-color);
}
</style>

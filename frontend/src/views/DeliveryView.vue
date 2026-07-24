<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Search, Plus, Download } from 'lucide-vue-next'

const deliveries = ref([
  { id: '1', dnNo: 'DN-000089', date: '20 May 2024', party: 'Shree Traders', vehicleNo: 'GJ 05 AB 9988', netWeight: 1.250, status: 'Posted' },
  { id: '2', dnNo: 'DN-000088', date: '19 May 2024', party: 'Kisan Exports', vehicleNo: 'GJ 01 CD 4321', netWeight: 2.000, status: 'Posted' },
  { id: '3', dnNo: 'DN-000087', date: '17 May 2024', party: 'Global Frozen', vehicleNo: 'GJ 03 EF 5566', netWeight: 0.850, status: 'Draft' }
])
</script>

<template>
  <div class="page-container">
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input type="text" placeholder="Search DN no., party..." class="custom-search-input" />
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="btn-outlined"><Download :size="15" /><span>Export</span></button>
        <button class="btn-primary"><Plus :size="16" /><span>New Delivery (DN)</span></button>
      </div>
    </div>

    <div class="table-card">
      <DataTable :value="deliveries" paginator :rows="5" responsiveLayout="scroll">
        <Column field="dnNo" header="DN No.">
          <template #body="{ data }">
            <span class="code-link">{{ data.dnNo }}</span>
          </template>
        </Column>
        <Column field="date" header="Dispatch Date" />
        <Column field="party" header="Party" />
        <Column field="vehicleNo" header="Vehicle No." />
        <Column field="netWeight" header="Net Weight (MT)">
          <template #body="{ data }">
            <span class="num-val">{{ data.netWeight.toFixed(3) }}</span>
          </template>
        </Column>
        <Column field="status" header="Status">
          <template #body="{ data }">
            <span class="status-pill" :class="data.status === 'Posted' ? 'success' : 'warning'">{{ data.status }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.page-container { display: flex; flex-direction: column; gap: 16px; }
.list-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 14px 18px; box-shadow: var(--shadow-card); }
.toolbar-search { display: flex; align-items: center; gap: 10px; flex: 1; }
.search-input-wrapper { position: relative; flex: 1; display: flex; align-items: center; }
.search-icon { position: absolute; left: 12px; color: var(--text-secondary); }
.custom-search-input { width: 100%; padding: 9px 12px 9px 36px; border-radius: 8px; border: 1px solid var(--border-subtle); background: var(--bg-page); color: var(--text-primary); font-size: 13px; }
.toolbar-actions { display: flex; gap: 10px; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; padding: 9px 18px; border-radius: 10px; background-color: var(--accent-primary); color: #ffffff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outlined { display: inline-flex; align-items: center; gap: 8px; padding: 9px 14px; border-radius: 10px; background-color: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border-subtle); font-size: 13px; cursor: pointer; }
.table-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 12px; box-shadow: var(--shadow-card); }
.code-link { font-weight: 700; color: var(--accent-primary); }
.num-val { font-feature-settings: "tnum"; }
</style>

<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Plus, Download, Search } from 'lucide-vue-next'

const invoices = ref([
  { id: '1', invNo: 'INV-000256', date: '20 May 2024', party: 'Shree Traders', amount: '₹ 1,45,200', tax: '₹ 26,136', status: 'Posted' },
  { id: '2', invNo: 'INV-000255', date: '19 May 2024', party: 'Kisan Exports', amount: '₹ 84,500', tax: '₹ 15,210', status: 'Posted' },
  { id: '3', invNo: 'INV-000254', date: '15 May 2024', party: 'Arctic Foods', amount: '₹ 45,000', tax: '₹ 8,100', status: 'Draft' }
])
</script>

<template>
  <div class="page-container">
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input type="text" placeholder="Search invoice no., party..." class="custom-search-input" />
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="btn-outlined"><Download :size="15" /><span>Export</span></button>
        <button class="btn-primary"><Plus :size="16" /><span>Generate GST Invoice</span></button>
      </div>
    </div>

    <div class="table-card">
      <DataTable :value="invoices" responsiveLayout="scroll">
        <Column field="invNo" header="Invoice No.">
          <template #body="{ data }">
            <span class="code-link">{{ data.invNo }}</span>
          </template>
        </Column>
        <Column field="date" header="Invoice Date" />
        <Column field="party" header="Party Name" />
        <Column field="amount" header="Subtotal (₹)">
          <template #body="{ data }"><span class="num-val">{{ data.amount }}</span></template>
        </Column>
        <Column field="tax" header="GST Tax (18%)">
          <template #body="{ data }"><span class="num-val">{{ data.tax }}</span></template>
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

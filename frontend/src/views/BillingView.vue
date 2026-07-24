<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { Calculator, Download } from 'lucide-vue-next'

const billingHistory = ref([
  { id: '1', period: 'May 2024', runDate: '20 May 2024', partiesBilled: 14, totalWeight: '1,245.60 MT', totalRent: '₹ 4,85,200', status: 'Completed' },
  { id: '2', period: 'April 2024', runDate: '30 Apr 2024', partiesBilled: 12, totalWeight: '1,180.20 MT', totalRent: '₹ 4,52,000', status: 'Completed' }
])
</script>

<template>
  <div class="page-container">
    <div class="list-toolbar">
      <div>
        <h3 class="toolbar-title">Rent Calculation & Billing Runs</h3>
        <p class="toolbar-desc">Calculate automated monthly storage charges based on occupied space & duration.</p>
      </div>
      <div class="toolbar-actions">
        <button class="btn-outlined"><Download :size="15" /><span>Export Log</span></button>
        <button class="btn-primary"><Calculator :size="16" /><span>Execute Rent Run</span></button>
      </div>
    </div>

    <div class="table-card">
      <DataTable :value="billingHistory" responsiveLayout="scroll">
        <Column field="period" header="Billing Period" />
        <Column field="runDate" header="Execution Date" />
        <Column field="partiesBilled" header="Parties Billed" />
        <Column field="totalWeight" header="Total Weight" />
        <Column field="totalRent" header="Total Rent (₹)">
          <template #body="{ data }">
            <span class="num-val bold-val">{{ data.totalRent }}</span>
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
.page-container { display: flex; flex-direction: column; gap: 16px; }
.list-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 16px 20px; box-shadow: var(--shadow-card); }
.toolbar-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.toolbar-desc { font-size: 12px; color: var(--text-secondary); }
.toolbar-actions { display: flex; gap: 10px; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; padding: 9px 18px; border-radius: 10px; background-color: var(--accent-primary); color: #ffffff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outlined { display: inline-flex; align-items: center; gap: 8px; padding: 9px 14px; border-radius: 10px; background-color: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border-subtle); font-size: 13px; cursor: pointer; }
.table-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 12px; box-shadow: var(--shadow-card); }
.num-val { font-feature-settings: "tnum"; }
.bold-val { font-weight: 700; color: var(--accent-primary); }
</style>

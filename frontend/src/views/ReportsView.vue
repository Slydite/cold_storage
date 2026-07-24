<script setup lang="ts">
import { BarChart3, Download, FileText, PieChart } from 'lucide-vue-next'

const reportCards = [
  { title: 'Chamber Stock Occupancy', desc: 'Detailed tonnage distribution per chamber & temperature zone.', icon: PieChart },
  { title: 'Party Aging Ledger', desc: 'Outstanding balances and rent accrual breakdown per customer.', icon: FileText },
  { title: 'Inward vs Outward Movement', desc: 'Monthly GRN vs DN tonnage throughput report.', icon: BarChart3 }
]
</script>

<template>
  <div class="page-container">
    <div class="reports-grid">
      <div v-for="rep in reportCards" :key="rep.title" class="report-card">
        <div class="card-top">
          <div class="report-icon-box">
            <component :is="rep.icon" :size="24" />
          </div>
          <div>
            <h4 class="rep-title">{{ rep.title }}</h4>
            <p class="rep-desc">{{ rep.desc }}</p>
          </div>
        </div>
        <div class="card-bottom">
          <button class="btn-outlined"><Download :size="15" /><span>Export PDF / Excel</span></button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { display: flex; flex-direction: column; gap: 16px; }
.reports-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.report-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; gap: 20px; box-shadow: var(--shadow-card); }
.card-top { display: flex; align-items: flex-start; gap: 16px; }
.report-icon-box { width: 44px; height: 44px; border-radius: 12px; background: var(--accent-primary-light); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rep-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.rep-desc { font-size: 12.5px; color: var(--text-secondary); margin-top: 4px; }
.card-bottom { display: flex; justify-content: flex-end; }
.btn-outlined { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 10px; background-color: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border-subtle); font-size: 12.5px; cursor: pointer; }
</style>

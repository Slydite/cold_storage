<script setup lang="ts">
import { Receipt, Warehouse } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { formatCurrency, formatQty } from '../../utils/format'

defineProps<{
  totalOutstandingAmount: number
  outstandingCount: number
  totalAccruingBags: number
  activeLotsCount: number
}>()

const { t } = useI18n()
</script>

<template>
  <div class="metrics-grid">
    <div class="metric-card highlight-card">
      <div class="metric-icon-wrap">
        <Receipt :size="22" class="icon-accent" />
      </div>
      <div class="metric-content">
        <span class="metric-label">{{ t('billing.totalOutstandingDue') }}</span>
        <strong class="metric-val text-danger">{{ formatCurrency(totalOutstandingAmount) }}</strong>
        <span class="metric-sub">{{ t('billing.pendingInvoicesCount', { count: outstandingCount }) }}</span>
      </div>
    </div>

    <div class="metric-card">
      <div class="metric-icon-wrap">
        <Warehouse :size="22" class="icon-secondary" />
      </div>
      <div class="metric-content">
        <span class="metric-label">{{ t('billing.stockAccruingRent') }}</span>
        <strong class="metric-val">{{ formatQty(totalAccruingBags, 0) }} {{ t('common.units') }}</strong>
        <span class="metric-sub">{{ t('billing.accruingUnitsCount', { count: activeLotsCount }) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.metric-icon-wrap {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: var(--bg-surface-hover);
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-accent {
  color: var(--accent-primary);
}

.icon-secondary {
  color: var(--text-secondary);
}

.metric-content {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.metric-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 2px 0;
}

.metric-sub {
  font-size: 12px;
  color: var(--text-secondary);
}

.text-danger {
  color: var(--status-danger-color);
}

@media (max-width: 640px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>

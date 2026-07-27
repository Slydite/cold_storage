<script setup lang="ts">
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useI18n } from 'vue-i18n'
import { formatCurrency, formatQty } from '../../utils/format'
import type { LotOutput } from '../../api/lot'

defineProps<{
  lots: LotOutput[]
}>()

const { t } = useI18n()
</script>

<template>
  <div class="billing-section">
    <div class="section-header">
      <h3 class="section-title">{{ t('billing.accruingStockTitle') }}</h3>
      <p class="section-desc">{{ t('billing.accruingStockDesc') }}</p>
    </div>

    <div class="table-card">
      <div v-if="lots.length === 0" class="empty-section">
        <p>{{ t('billing.noActiveStock') }}</p>
      </div>

      <DataTable
        v-else
        :value="lots"
        size="small"
        stripedRows
        paginator
        :rows="8"
        responsiveLayout="scroll"
        class="custom-datatable"
      >
        <Column field="lot_number" :header="t('inventory.lotNo')">
          <template #body="{ data }">
            <span class="code-link">{{ data.lot_number }}</span>
          </template>
        </Column>

        <Column field="party_name" :header="t('inventory.party')">
          <template #body="{ data }">
            <strong>{{ data.party_name || '—' }}</strong>
          </template>
        </Column>

        <Column field="commodity_name" :header="t('grn.commodityProduct')" />

        <Column :header="t('inventory.location')">
          <template #body="{ data }">
            <span>{{ data.location_display || [data.chamber_name || data.chamber, data.floor_name || data.floor].filter(Boolean).join(' / ') || '—' }}</span>
          </template>
        </Column>

        <Column field="inward_date" :header="t('inventory.inDate')" />

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

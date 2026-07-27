<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Info } from 'lucide-vue-next'
import { useFacility } from '../composables/useFacility'
import StockSummaryCard from '../components/reports/StockSummaryCard.vue'
import RegisterExportCard from '../components/reports/RegisterExportCard.vue'

const { t } = useI18n()
const { facilityId } = useFacility()
</script>

<template>
  <div class="page-container">
    <div class="reports-header-banner">
      <div class="banner-content">
        <h3 class="banner-title">{{ t('reports.bannerTitle') }}</h3>
        <p class="banner-desc">
          {{ t('reports.bannerDesc') }}
        </p>
      </div>
    </div>

    <div class="reports-grid">
      <!-- 1. Stock Summary -->
      <StockSummaryCard :facilityId="facilityId" />

      <!-- 2. GRN Register -->
      <RegisterExportCard
        :title="t('reports.grnRegisterTitle')"
        :description="t('reports.grnRegisterDesc')"
        endpoint="/api/reports/grn-register/"
        reportType="grn"
        :facilityId="facilityId"
      />

      <!-- 3. DN Register -->
      <RegisterExportCard
        :title="t('reports.dnRegisterTitle')"
        :description="t('reports.dnRegisterDesc')"
        endpoint="/api/reports/dn-register/"
        reportType="dn"
        :facilityId="facilityId"
      />

      <!-- 4. Invoice Register -->
      <RegisterExportCard
        :title="t('reports.gstRegisterTitle')"
        :description="t('reports.gstRegisterDesc')"
        endpoint="/api/reports/invoices/"
        reportType="invoice"
        :facilityId="facilityId"
      />
    </div>

    <div class="reports-note">
      <Info :size="16" class="note-icon" />
      <span>
        {{ t('reports.rentRunNote') }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.reports-header-banner {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: var(--shadow-card);
}

.banner-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.banner-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.reports-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

@media (max-width: 900px) {
  .reports-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.reports-note {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--accent-primary-light);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 12.5px;
}

.note-icon {
  color: var(--accent-primary);
  flex-shrink: 0;
}
</style>

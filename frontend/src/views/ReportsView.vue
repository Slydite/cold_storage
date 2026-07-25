<script setup lang="ts">
import { useFacility } from '../composables/useFacility'
import StockSummaryCard from '../components/reports/StockSummaryCard.vue'
import RegisterExportCard from '../components/reports/RegisterExportCard.vue'
import { Info } from 'lucide-vue-next'

const { facilityId } = useFacility()
</script>

<template>
  <div class="page-container">
    <div class="reports-header-banner">
      <div class="banner-content">
        <h3 class="banner-title">Reports & Data Registers</h3>
        <p class="banner-desc">
          Generate comprehensive audit logs, register ledgers, and stock summaries. Export as CSV files or view quick inline previews.
        </p>
      </div>
    </div>

    <div class="reports-grid">
      <!-- 1. Stock Summary -->
      <StockSummaryCard :facilityId="facilityId" />

      <!-- 2. GRN Register -->
      <RegisterExportCard
        title="GRN Inward Register"
        description="Complete inward goods movement log filtered by date range and status."
        endpoint="/api/reports/grn-register/"
        reportType="grn"
        :facilityId="facilityId"
      />

      <!-- 3. DN Register -->
      <RegisterExportCard
        title="Delivery Note Register"
        description="Complete outward goods movement log filtered by date range and status."
        endpoint="/api/reports/dn-register/"
        reportType="dn"
        :facilityId="facilityId"
      />

      <!-- 4. Invoice Register -->
      <RegisterExportCard
        title="GST Invoice Register"
        description="Comprehensive GST invoice ledger including party GSTIN snapshots and total amounts."
        endpoint="/api/reports/invoices/"
        reportType="invoice"
        :facilityId="facilityId"
      />
    </div>

    <div class="reports-note">
      <Info :size="16" class="note-icon" />
      <span>
        Looking for Rent Run specific reports? Detailed per-run breakdown reports can be exported directly from individual Rent Run details on the <strong>Billing</strong> page.
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

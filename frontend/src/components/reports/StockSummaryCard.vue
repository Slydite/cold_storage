<script setup lang="ts">
import { ref } from 'vue'
import { PieChart, Download, Eye, AlertCircle } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { fetchReportJson, downloadReportCsv } from '../../composables/useReportExport'
import { formatQty } from '../../utils/format'

interface Props {
  facilityId?: number
}

interface CommodityRow {
  commodity__name?: string
  name?: string
  total_qty?: number
  total_bags?: number
  [key: string]: unknown
}

interface ChamberRow {
  chamber?: string
  total_qty?: number
  total_bags?: number
  [key: string]: unknown
}

interface StockSummaryData {
  by_commodity?: CommodityRow[]
  by_chamber?: ChamberRow[]
}

const props = defineProps<Props>()
const { t } = useI18n()
const toast = useToast()

const loadingJson = ref(false)
const downloadingCsv = ref(false)
const showBreakdown = ref(false)
const reportData = ref<StockSummaryData | null>(null)
const errorDetail = ref<string | null>(null)

async function handleViewBreakdown() {
  if (showBreakdown.value && reportData.value) {
    showBreakdown.value = false
    return
  }

  loadingJson.value = true
  errorDetail.value = null
  try {
    const data = await fetchReportJson<StockSummaryData>('/api/reports/stock-summary/', {
      facility_id: props.facilityId
    })
    reportData.value = data
    showBreakdown.value = true
  } catch (err) {
    errorDetail.value = err instanceof Error ? err.message : t('reports.failedToLoad')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: errorDetail.value,
      life: 4000
    })
  } finally {
    loadingJson.value = false
  }
}

async function handleDownloadCsv() {
  downloadingCsv.value = true
  try {
    await downloadReportCsv(
      '/api/reports/stock-summary/',
      { facility_id: props.facilityId },
      'stock_summary.csv'
    )
    toast.add({
      severity: 'success',
      summary: t('reports.downloadStarted'),
      detail: t('reports.downloadStartedDetail'),
      life: 3000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.exportFailed'),
      detail: err instanceof Error ? err.message : t('common.exportFailed'),
      life: 4000
    })
  } finally {
    downloadingCsv.value = false
  }
}
</script>

<template>
  <div class="report-card">
    <div class="card-top">
      <div class="report-icon-box">
        <PieChart :size="24" />
      </div>
      <div class="title-area">
        <h4 class="rep-title">{{ t('reports.stockOccupancySummary') }}</h4>
        <p class="rep-desc">{{ t('reports.stockOccupancyDesc') }}</p>
      </div>
    </div>

    <div v-if="errorDetail" class="card-error">
      <AlertCircle :size="16" />
      <span>{{ errorDetail }}</span>
    </div>

    <div v-if="showBreakdown && reportData" class="breakdown-container">
      <div class="breakdown-section">
        <h5 class="section-title">{{ t('reports.byCommodity') }}</h5>
        <div v-if="!reportData.by_commodity || reportData.by_commodity.length === 0" class="muted-text">
          {{ t('reports.noStockByCommodity') }}
        </div>
        <table v-else class="mini-table">
          <thead>
            <tr>
              <th>{{ t('common.commodity') }}</th>
              <th class="text-right">{{ t('reports.totalBags') }}</th>
              <th class="text-right">{{ t('reports.qtyMt') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in reportData.by_commodity" :key="i">
              <td>{{ item.commodity_name || t('common.uncategorized') }}</td>
              <td class="text-right num-val">{{ item.total_qty ?? '-' }}</td>
              <td class="text-right num-val">{{ formatQty(Number(item.total_weight_kg || 0) / 1000) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="breakdown-section">
        <h5 class="section-title">{{ t('reports.byChamber') }}</h5>
        <div v-if="!reportData.by_chamber || reportData.by_chamber.length === 0" class="muted-text">
          {{ t('reports.noStockByChamber') }}
        </div>
        <table v-else class="mini-table">
          <thead>
            <tr>
              <th>{{ t('locations.chamber') }}</th>
              <th class="text-right">{{ t('reports.totalBags') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in reportData.by_chamber" :key="i">
              <td>{{ item.chamber || t('common.unassigned') }}</td>
              <td class="text-right num-val">{{ item.total_qty ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card-bottom">
      <button
        class="btn-outlined"
        type="button"
        @click="handleViewBreakdown"
        :disabled="loadingJson"
      >
        <Eye :size="15" />
        <span>{{ loadingJson ? t('common.loading') : showBreakdown ? t('common.hidePreview') : t('common.viewPreview') }}</span>
      </button>

      <button
        class="btn-primary"
        type="button"
        @click="handleDownloadCsv"
        :disabled="downloadingCsv"
      >
        <Download :size="15" />
        <span>{{ downloadingCsv ? t('common.downloading') : t('common.downloadCsv') }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.report-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.report-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.title-area {
  flex: 1;
}

.rep-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.rep-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.card-error {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--status-danger-bg);
  color: var(--status-danger-color);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12.5px;
}

.breakdown-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px;
}

.breakdown-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.muted-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.mini-table th,
.mini-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.mini-table th {
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-surface);
}

.text-right {
  text-align: right;
}

.num-val {
  font-feature-settings: 'tnum';
  font-weight: 600;
}

.card-bottom {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: auto;
}
</style>

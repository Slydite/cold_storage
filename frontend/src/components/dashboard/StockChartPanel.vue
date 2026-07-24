<script setup lang="ts">
import { ref, computed } from 'vue'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  LinearScale,
  CategoryScale
} from 'chart.js'
import { useThemeStore } from '../../stores/theme'
import type { StockGroup } from '../../composables/useDashboardStats'

ChartJS.register(Title, Tooltip, Legend, BarElement, LinearScale, CategoryScale)

const props = defineProps<{
  stockByCommodity: StockGroup[]
  stockByChamber: StockGroup[]
  loading: boolean
}>()

const groupBy = ref<'commodity' | 'chamber'>('commodity')
const groupOptions = [
  { label: 'By Commodity', value: 'commodity' },
  { label: 'By Chamber', value: 'chamber' }
]

const themeStore = useThemeStore()

const currentData = computed(() => {
  return groupBy.value === 'commodity' ? props.stockByCommodity : props.stockByChamber
})

const hasData = computed(() => currentData.value.length > 0 && currentData.value.some((item) => item.qty > 0))

const chartData = computed(() => {
  const isDark = themeStore.theme === 'dark'
  const barColor = isDark ? 'rgba(168, 85, 247, 0.75)' : 'rgba(249, 115, 22, 0.75)'
  const hoverColor = isDark ? '#A855F7' : '#F97316'

  const labels = currentData.value.map((item) => item.label)
  const data = currentData.value.map((item) => item.qty)

  return {
    labels,
    datasets: [
      {
        label: 'Stock (MT)',
        data,
        backgroundColor: barColor,
        hoverBackgroundColor: hoverColor,
        borderRadius: 6,
        maxBarThickness: 48
      }
    ]
  }
})

const chartOptions = computed(() => {
  const isDark = themeStore.theme === 'dark'
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'
  const textColor = isDark ? '#8E84B0' : '#6B6B7A'

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: isDark ? '#18112F' : '#FFFFFF',
        titleColor: isDark ? '#F5F3FF' : '#1B1B23',
        bodyColor: isDark ? '#8E84B0' : '#6B6B7A',
        borderColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: (context: { raw: unknown }) => `Stock: ${context.raw} MT`
        }
      }
    },
    scales: {
      x: {
        grid: { color: gridColor },
        ticks: { color: textColor, font: { family: 'Inter', size: 12 } }
      },
      y: {
        beginAtZero: true,
        grid: { color: gridColor, borderDash: [4, 4] },
        ticks: {
          color: textColor,
          font: { family: 'Inter', size: 12 },
          callback: (value: number | string) => `${value} MT`
        }
      }
    }
  }
})
</script>

<template>
  <div class="card-panel chart-panel">
    <div class="panel-header">
      <div>
        <h3 class="panel-title">Stock Breakdown (MT)</h3>
      </div>
      <Select
        v-model="groupBy"
        :options="groupOptions"
        optionLabel="label"
        optionValue="value"
        class="range-select"
      />
    </div>

    <div class="chart-container">
      <Skeleton v-if="loading" width="100%" height="100%" />
      <div v-else-if="!hasData" class="empty-chart">
        <span>No active stock available to display</span>
      </div>
      <Bar v-else :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<style scoped>
.card-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.range-select {
  font-size: 12.5px !important;
  border-radius: 8px !important;
  background: var(--bg-page) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}

.chart-container {
  height: 290px;
  position: relative;
  width: 100%;
}

.empty-chart {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13.5px;
  background: var(--bg-page);
  border-radius: 12px;
  border: 1px dashed var(--border-subtle);
}
</style>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import {
  Package,
  Boxes,
  IndianRupee,
  AlertCircle,
  Plus,
  Truck,
  FileCheck2,
  Calculator,
  RotateCw,
  Receipt,
  UserCheck
} from 'lucide-vue-next'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
  Filler
} from 'chart.js'
import { useThemeStore } from '../stores/theme'

ChartJS.register(Title, Tooltip, Legend, LineElement, LinearScale, PointElement, CategoryScale, Filler)

const router = useRouter()
const themeStore = useThemeStore()

const timeRange = ref('30')
const rangeOptions = [
  { label: 'Last 7 Days', value: '7' },
  { label: 'Last 30 Days', value: '30' },
  { label: 'Last 90 Days', value: '90' }
]

// Stat Cards Data matching target mockup exactly
const stats = [
  {
    title: 'Total Stock (MT)',
    value: '1,245.60',
    trend: '4.35%',
    trendUp: true,
    badgeClass: 'badge-purple',
    icon: Package
  },
  {
    title: 'Active Lots',
    value: '86',
    trend: '5.13%',
    trendUp: true,
    badgeClass: 'badge-green',
    icon: Boxes
  },
  {
    title: 'Storage Value (₹)',
    value: '₹ 32,48,750',
    trend: '3.24%',
    trendUp: true,
    badgeClass: 'badge-blue',
    icon: IndianRupee
  },
  {
    title: 'Overdue Rent (₹)',
    value: '₹ 2,78,450',
    trend: '8.12%',
    trendUp: false,
    badgeClass: 'badge-red',
    icon: AlertCircle
  }
]

// Recent Activities Data
const activities = [
  {
    id: 1,
    title: 'GRN GRN-000123 created',
    user: 'Admin User',
    time: '10 min ago',
    icon: UserCheck,
    badgeClass: 'badge-green'
  },
  {
    id: 2,
    title: 'DN DN-000089 created',
    user: 'Admin User',
    time: '35 min ago',
    icon: Truck,
    badgeClass: 'badge-blue'
  },
  {
    id: 3,
    title: 'Invoice INV-000256 generated',
    user: 'Admin User',
    time: '1 hr ago',
    icon: FileCheck2,
    badgeClass: 'badge-purple'
  },
  {
    id: 4,
    title: 'Rent run (May 2024) completed',
    user: 'System',
    time: '2 hrs ago',
    icon: RotateCw,
    badgeClass: 'badge-blue'
  },
  {
    id: 5,
    title: 'Payment received from',
    highlightParty: 'Shree Traders',
    user: 'Accounts',
    time: '3 hrs ago',
    icon: Receipt,
    badgeClass: 'badge-green'
  }
]

// Chart Data matching the exact sinusoidal wave of target mockup
const chartData = computed(() => {
  const isDark = themeStore.theme === 'dark'
  const strokeColor = isDark ? '#A855F7' : '#F97316'
  const fillColor = isDark ? 'rgba(168, 85, 247, 0.18)' : 'rgba(249, 115, 22, 0.12)'

  return {
    labels: ['1 May', '8 May', '15 May', '22 May', '29 May'],
    datasets: [
      {
        label: 'Stock (MT)',
        data: [980, 1420, 1260, 1680, 1450],
        borderColor: strokeColor,
        borderWidth: 3.5,
        tension: 0.45,
        fill: true,
        backgroundColor: fillColor,
        pointBackgroundColor: strokeColor,
        pointRadius: 0,
        pointHoverRadius: 6
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
        padding: 12
      }
    },
    scales: {
      x: {
        grid: { color: gridColor },
        ticks: { color: textColor, font: { family: 'Inter', size: 12 } }
      },
      y: {
        min: 0,
        max: 2000,
        grid: { color: gridColor, borderDash: [4, 4] },
        ticks: {
          color: textColor,
          font: { family: 'Inter', size: 12 },
          stepSize: 500,
          callback: (value: any) => {
            if (value === 0) return '0'
            if (value === 500) return '500'
            if (value === 1000) return '1K'
            if (value === 1500) return '1.5K'
            if (value === 2000) return '2K'
            return value
          }
        }
      }
    }
  }
})

const quickActions = [
  {
    title: 'New GRN',
    subtitle: 'Record Inward',
    icon: Plus,
    path: '/grn?action=create',
    badgeClass: 'badge-purple'
  },
  {
    title: 'New Delivery',
    subtitle: 'Record Outward',
    icon: Truck,
    path: '/delivery?action=create',
    badgeClass: 'badge-green'
  },
  {
    title: 'Generate Invoice',
    subtitle: 'Create GST Invoice',
    icon: FileCheck2,
    path: '/invoicing?action=create',
    badgeClass: 'badge-blue'
  },
  {
    title: 'Rent Run',
    subtitle: 'Calculate Rent',
    icon: Calculator,
    path: '/billing?action=rent_run',
    badgeClass: 'badge-gold',
    hasArtwork: true
  }
]

const triggerQuickAction = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="dashboard-page">
    <!-- Stat Cards Grid -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.title" class="stat-card">
        <div class="stat-header">
          <span class="stat-title">{{ stat.title }}</span>
          <div class="stat-icon-circle" :class="stat.badgeClass">
            <component :is="stat.icon" :size="20" />
          </div>
        </div>
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-trend-line">
          <span class="trend-pill" :class="stat.trendUp ? 'trend-up' : 'trend-down'">
            ▲ {{ stat.trend }}
          </span>
          <span class="trend-context">vs last month</span>
        </div>
      </div>
    </div>

    <!-- Main Content Two-Column Grid -->
    <div class="dashboard-content-grid">
      <!-- Stock Trend Chart Card -->
      <div class="card-panel chart-panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Stock Trend (MT)</h3>
          </div>
          <Select
            v-model="timeRange"
            :options="rangeOptions"
            optionLabel="label"
            optionValue="value"
            class="range-select"
          />
        </div>
        <div class="chart-container">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- Recent Activities Card -->
      <div class="card-panel activities-panel">
        <div class="panel-header">
          <h3 class="panel-title">Recent Activities</h3>
          <router-link to="/reports" class="view-all-link">
            <span>View all</span>
          </router-link>
        </div>
        <div class="activities-list">
          <div v-for="act in activities" :key="act.id" class="activity-item">
            <div class="activity-icon-badge" :class="act.badgeClass">
              <component :is="act.icon" :size="16" />
            </div>
            <div class="activity-details">
              <div class="activity-title">
                <span>{{ act.title }} </span>
                <span v-if="act.highlightParty" class="party-highlight">{{ act.highlightParty }}</span>
              </div>
              <div class="activity-meta">by {{ act.user }}</div>
            </div>
            <div class="activity-time">{{ act.time }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions Section -->
    <div class="quick-actions-section">
      <h3 class="section-title">Quick Actions</h3>
      <div class="actions-grid">
        <button
          v-for="action in quickActions"
          :key="action.title"
          class="action-card-btn"
          :class="{ 'has-art-bg': action.hasArtwork }"
          @click="triggerQuickAction(action.path)"
        >
          <div class="action-icon-box" :class="action.badgeClass">
            <component :is="action.icon" :size="20" />
          </div>
          <div class="action-text">
            <span class="action-title">{{ action.title }}</span>
            <span class="action-subtitle">{{ action.subtitle }}</span>
          </div>

          <!-- Warehouse Artwork overlay for Rent Run card -->
          <div v-if="action.hasArtwork" class="art-overlay-image">
            <img src="/warehouse_art.png" alt="Warehouse Artwork" class="art-img" />
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Stat Cards Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-title {
  font-size: 13.5px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Badge variants matching mockup colors */
.badge-purple {
  background: rgba(139, 92, 246, 0.25);
  color: #A855F7;
}

.badge-green {
  background: rgba(34, 197, 94, 0.2);
  color: #22C55E;
}

.badge-blue {
  background: rgba(59, 130, 246, 0.2);
  color: #3B82F6;
}

.badge-red {
  background: rgba(239, 68, 68, 0.2);
  color: #EF4444;
}

.badge-gold {
  background: rgba(245, 158, 11, 0.25);
  color: #F59E0B;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 14px;
  letter-spacing: -0.5px;
  font-feature-settings: "tnum";
}

.stat-trend-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 12.5px;
}

.trend-pill {
  font-weight: 700;
}

.trend-up {
  color: #22C55E;
}

.trend-down {
  color: #EF4444;
}

.trend-context {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Two-column grid */
.dashboard-content-grid {
  display: grid;
  grid-template-columns: 1.8fr 1fr;
  gap: 20px;
}

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

.view-all-link {
  font-size: 13px;
  font-weight: 600;
  color: #A855F7;
  text-decoration: none;
}

.view-all-link:hover {
  text-decoration: underline;
}

.activities-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.activity-icon-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.activity-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.party-highlight {
  color: #22C55E;
  font-weight: 700;
}

.activity-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.activity-time {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  font-weight: 500;
}

/* Quick Actions Section */
.quick-actions-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.action-card-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 22px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: all 0.15s ease;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.action-card-btn:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
  background-color: var(--bg-surface-hover);
}

.action-icon-box {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 2;
}

.action-text {
  display: flex;
  flex-direction: column;
  z-index: 2;
}

.action-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.action-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

/* Art Overlay background for Rent Run button */
.action-card-btn.has-art-bg {
  background: linear-gradient(135deg, var(--bg-surface) 30%, rgba(245, 158, 11, 0.15) 100%);
}

.art-overlay-image {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 140px;
  pointer-events: none;
  opacity: 0.35;
  mix-blend-mode: luminosity;
  overflow: hidden;
}

.art-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

@media (max-width: 1200px) {
  .stats-grid, .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .dashboard-content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .stats-grid, .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>

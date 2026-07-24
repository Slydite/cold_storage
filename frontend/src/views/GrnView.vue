<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Skeleton from 'primevue/skeleton'
import { useToast } from 'primevue/usetoast'
import {
  Search,
  Filter,
  Download,
  Plus,
  Trash2,
  Eye,
  Package,
  AlertCircle,
  RefreshCw,
  FileCheck
} from 'lucide-vue-next'
import { chamberOptions } from '../constants/chambers'
import { formatQty, formatCurrency } from '../utils/format'
import { useSearchFilter } from '../composables/useSearchFilter'

const route = useRoute()
const toast = useToast()

// View state management
const loading = ref(false)
const errorState = ref(false)
const isPanelOpen = ref(false)

// Search & Filter state
const selectedChamber = ref('all')
const selectedPeriod = ref('this_month')

const periodOptions = [
  { label: 'This Month', value: 'this_month' },
  { label: 'Today', value: 'today' },
  { label: 'All Time', value: 'all_time' }
]

// Mock GRN List Data
interface GrnItem {
  id: string
  grnNo: string
  date: string
  party: string
  chamber: string
  netWeight: number
  status: 'Draft' | 'Posted' | 'Cancelled'
}

const grnList = ref<GrnItem[]>([
  { id: '1', grnNo: 'GRN-000123', date: '20 May 2024', party: 'Shree Traders', chamber: 'Chamber A', netWeight: 7.500, status: 'Draft' },
  { id: '2', grnNo: 'GRN-000122', date: '19 May 2024', party: 'Kisan Exports', chamber: 'Chamber B', netWeight: 5.250, status: 'Posted' },
  { id: '3', grnNo: 'GRN-000121', date: '18 May 2024', party: 'Arctic Foods', chamber: 'Chamber C', netWeight: 3.800, status: 'Posted' },
  { id: '4', grnNo: 'GRN-000120', date: '18 May 2024', party: 'Shree Traders', chamber: 'Chamber A', netWeight: 6.300, status: 'Posted' },
  { id: '5', grnNo: 'GRN-000119', date: '17 May 2024', party: 'Global Frozen', chamber: 'Chamber B', netWeight: 4.400, status: 'Cancelled' }
])

const { searchQuery, filtered: searchedGrns } = useSearchFilter(grnList, (item, query) =>
  item.grnNo.toLowerCase().includes(query) || item.party.toLowerCase().includes(query)
)

const filteredGrns = computed(() =>
  searchedGrns.value.filter(
    (item) => selectedChamber.value === 'all' || item.chamber === selectedChamber.value
  )
)

// Create GRN Form state
interface LineItem {
  id: number
  product: string
  packaging: string
  qty: number
  weight: number
  rate: number
}

const partyOptions = ['Shree Traders', 'Kisan Exports', 'Arctic Foods', 'Global Frozen']

const form = ref({
  grnDate: new Date(),
  grnNo: 'Auto (will be generated)',
  party: 'Shree Traders',
  chamber: 'Chamber A',
  driverName: 'Ramesh Bhai',
  vehicleNo: 'GJ 05 AB 1234',
  items: [
    { id: 1, product: 'Frozen Green Peas', packaging: 'Bag (25kg)', qty: 100, weight: 2.500, rate: 1850 },
    { id: 2, product: 'Frozen Sweet Corn', packaging: 'Bag (25kg)', qty: 80, weight: 2.000, rate: 1950 },
    { id: 3, product: 'Frozen Cauliflower', packaging: 'Bag (25kg)', qty: 120, weight: 3.000, rate: 1800 }
  ] as LineItem[]
})

const addItemRow = () => {
  const newId = form.value.items.length + 1
  form.value.items.push({
    id: newId,
    product: '',
    packaging: 'Bag (25kg)',
    qty: 0,
    weight: 0,
    rate: 0
  })
}

const removeItemRow = (index: number) => {
  if (form.value.items.length > 1) {
    form.value.items.splice(index, 1)
  }
}

const totalNetWeight = computed(() => {
  return form.value.items.reduce((sum, item) => sum + (Number(item.weight) || 0), 0)
})

const totalAmount = computed(() => {
  return form.value.items.reduce((sum, item) => sum + ((Number(item.weight) || 0) * (Number(item.rate) || 0)), 0)
})

const openCreatePanel = () => {
  isPanelOpen.value = true
}

const closeCreatePanel = () => {
  isPanelOpen.value = false
}

const saveGrn = (isDraft = false) => {
  const newGrnNo = `GRN-${Math.floor(100000 + Math.random() * 900000)}`
  grnList.value.unshift({
    id: String(Date.now()),
    grnNo: newGrnNo,
    date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
    party: form.value.party,
    chamber: form.value.chamber,
    netWeight: totalNetWeight.value,
    status: isDraft ? 'Draft' : 'Posted'
  })

  toast.add({
    severity: isDraft ? 'info' : 'success',
    summary: isDraft ? 'Draft Saved' : 'GRN Created',
    detail: `GRN ${newGrnNo} has been successfully ${isDraft ? 'saved as draft' : 'posted'}.`,
    life: 3000
  })

  closeCreatePanel()
}

const retryFetch = () => {
  errorState.value = false
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 600)
}

onMounted(() => {
  if (route.query.action === 'create') {
    openCreatePanel()
  }
})
</script>

<template>
  <div class="grn-page" :class="{ 'panel-active': isPanelOpen }">
    <!-- Left Master Section (List View) -->
    <div class="master-list-container">
      <!-- Toolbar Header -->
      <div class="list-toolbar">
        <div class="toolbar-search">
          <div class="search-input-wrapper">
            <Search :size="16" class="search-icon" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search GRN no., party..."
              class="custom-search-input"
            />
          </div>
          <Select
            v-model="selectedChamber"
            :options="chamberOptions"
            optionLabel="label"
            optionValue="value"
            class="toolbar-select"
          />
          <Select
            v-model="selectedPeriod"
            :options="periodOptions"
            optionLabel="label"
            optionValue="value"
            class="toolbar-select"
          />
        </div>

        <div class="toolbar-actions">
          <button class="btn-outlined">
            <Filter :size="15" />
            <span>Filters</span>
          </button>
          <button class="btn-outlined">
            <Download :size="15" />
            <span>Export</span>
          </button>
          <button class="btn-primary" @click="openCreatePanel">
            <Plus :size="16" />
            <span>New GRN</span>
          </button>
        </div>
      </div>

      <!-- Explicit State 1: Error State -->
      <div v-if="errorState" class="state-card error-card">
        <AlertCircle :size="36" class="state-icon text-danger" />
        <h4 class="state-title">Failed to load GRN records</h4>
        <p class="state-desc">There was an issue connecting to the server. Please try again.</p>
        <button class="btn-primary" @click="retryFetch">
          <RefreshCw :size="15" />
          <span>Retry</span>
        </button>
      </div>

      <!-- Explicit State 2: Skeleton Loading State -->
      <div v-else-if="loading" class="skeleton-container">
        <Skeleton height="42px" class="mb-3" />
        <Skeleton height="56px" class="mb-2" v-for="i in 5" :key="i" />
      </div>

      <!-- Explicit State 3: Empty State -->
      <div v-else-if="filteredGrns.length === 0" class="state-card empty-card">
        <Package :size="40" class="state-icon text-muted" />
        <h4 class="state-title">No Goods Receipt Notes found</h4>
        <p class="state-desc">Get started by recording your first inward inventory GRN entry.</p>
        <button class="btn-primary" @click="openCreatePanel">
          <Plus :size="16" />
          <span>Create New GRN</span>
        </button>
      </div>

      <!-- Happy Path: DataTable View -->
      <div v-else class="table-card">
        <DataTable
          :value="filteredGrns"
          paginator
          :rows="5"
          responsiveLayout="scroll"
          class="custom-datatable"
        >
          <Column field="grnNo" header="GRN No." sortable>
            <template #body="{ data }">
              <span class="code-link">{{ data.grnNo }}</span>
            </template>
          </Column>

          <Column field="date" header="GRN Date" sortable />

          <Column field="party" header="Party" sortable>
            <template #body="{ data }">
              <span class="party-name">{{ data.party }}</span>
            </template>
          </Column>

          <Column field="chamber" header="Chamber" sortable />

          <Column field="netWeight" header="Net Weight (MT)" sortable>
            <template #body="{ data }">
              <span class="num-val">{{ formatQty(data.netWeight) }}</span>
            </template>
          </Column>

          <Column field="status" header="Status">
            <template #body="{ data }">
              <span
                class="status-pill"
                :class="{
                  success: data.status === 'Posted',
                  warning: data.status === 'Draft',
                  danger: data.status === 'Cancelled'
                }"
              >
                {{ data.status }}
              </span>
            </template>
          </Column>

          <Column header="Actions">
            <template #body>
              <div class="row-actions">
                <button class="icon-btn" title="View details">
                  <Eye :size="16" />
                </button>
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Right Detail Split Panel (Create/Edit GRN Form) -->
    <transition name="panel-slide">
      <div v-if="isPanelOpen" class="detail-split-panel">
        <!-- Panel Header -->
        <div class="panel-topbar">
          <div class="breadcrumb-context">
            <span class="muted-crumb">GRN / Inward</span>
            <span class="slash-crumb">></span>
            <span class="active-crumb">Create GRN</span>
          </div>

          <div class="panel-actions">
            <button class="btn-text" @click="closeCreatePanel">Cancel</button>
            <button class="btn-outlined" @click="saveGrn(true)">Save Draft</button>
            <button class="btn-primary" @click="saveGrn(false)">
              <FileCheck :size="16" />
              <span>Save GRN</span>
            </button>
          </div>
        </div>

        <!-- Panel Form Scrollable Body -->
        <div class="panel-body">
          <!-- Header Grid Inputs -->
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">GRN Date <span class="req">*</span></label>
              <DatePicker v-model="form.grnDate" dateFormat="dd/mm/yy" showIcon class="w-full" />
            </div>

            <div class="form-group">
              <label class="form-label">GRN No.</label>
              <InputText v-model="form.grnNo" disabled class="w-full" />
            </div>

            <div class="form-group">
              <label class="form-label">Supplier / Party <span class="req">*</span></label>
              <Select v-model="form.party" :options="partyOptions" class="w-full" />
            </div>

            <div class="form-group">
              <label class="form-label">Chamber <span class="req">*</span></label>
              <Select
                v-model="form.chamber"
                :options="['Chamber A', 'Chamber B', 'Chamber C']"
                class="w-full"
              />
            </div>

            <div class="form-group">
              <label class="form-label">Driver Name</label>
              <InputText v-model="form.driverName" class="w-full" />
            </div>

            <div class="form-group">
              <label class="form-label">Vehicle No.</label>
              <InputText v-model="form.vehicleNo" class="w-full" />
            </div>
          </div>

          <!-- Items Editable Section -->
          <div class="items-section">
            <h4 class="section-subtitle">Items / Products Inward</h4>

            <div class="items-table-wrapper">
              <table class="items-table">
                <thead>
                  <tr>
                    <th width="40">#</th>
                    <th>Item / Product</th>
                    <th width="130">Packaging</th>
                    <th width="90">Qty (Units)</th>
                    <th width="110">Net Weight (MT)</th>
                    <th width="110">Rate / Unit (₹)</th>
                    <th width="110">Amount (₹)</th>
                    <th width="50"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in form.items" :key="item.id">
                    <td>{{ idx + 1 }}</td>
                    <td>
                      <InputText v-model="item.product" placeholder="Item name" class="w-full input-sm" />
                    </td>
                    <td>
                      <InputText v-model="item.packaging" class="w-full input-sm" />
                    </td>
                    <td>
                      <input type="number" v-model.number="item.qty" class="p-inputtext p-component w-full input-sm num-align" />
                    </td>
                    <td>
                      <input type="number" step="0.001" v-model.number="item.weight" class="p-inputtext p-component w-full input-sm num-align" />
                    </td>
                    <td>
                      <input type="number" v-model.number="item.rate" class="p-inputtext p-component w-full input-sm num-align" />
                    </td>
                    <td class="amount-cell">
                      {{ formatCurrency((item.weight || 0) * (item.rate || 0)) }}
                    </td>
                    <td>
                      <button class="icon-btn danger-hover" @click="removeItemRow(idx)" title="Remove item">
                        <Trash2 :size="15" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <button class="btn-outlined add-item-btn" @click="addItemRow">
              <Plus :size="15" />
              <span>Add Item</span>
            </button>
          </div>
        </div>

        <!-- Pinned Totals Summary Bar at Bottom -->
        <div class="panel-totals-bar">
          <div class="total-metric">
            <span class="metric-label">Total Net Weight (MT)</span>
            <span class="metric-value">{{ formatQty(totalNetWeight) }}</span>
          </div>

          <div class="total-metric highlight-metric">
            <span class="metric-label">Total Amount (₹)</span>
            <span class="metric-value">{{ formatCurrency(totalAmount) }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.grn-page {
  display: flex;
  gap: 20px;
  width: 100%;
  position: relative;
}

/* Master list layout scaling */
.master-list-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.25s ease;
}

.panel-active .master-list-container {
  max-width: 40%;
}

/* Explicit States */
.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.state-icon {
  margin-bottom: 4px;
}

.state-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.state-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 380px;
  margin-bottom: 8px;
}

/* Detail Split Panel (Right side ~60%) */
.detail-split-panel {
  flex: 1.5;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  position: sticky;
  top: 88px;
  overflow: hidden;
}

.panel-topbar {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-surface);
}

.breadcrumb-context {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}

.muted-crumb {
  color: var(--text-secondary);
  font-weight: 500;
}

.slash-crumb {
  color: var(--text-secondary);
}

.active-crumb {
  color: var(--text-primary);
  font-weight: 700;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.req {
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.items-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.items-table-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.items-table th {
  background: var(--bg-page);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.items-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.input-sm {
  font-size: 12px !important;
  padding: 6px 8px !important;
  border-radius: 6px !important;
}

.num-align {
  text-align: right;
}

.amount-cell {
  font-weight: 700;
  color: var(--text-primary);
  text-align: right;
  font-feature-settings: "tnum";
}

.add-item-btn {
  align-self: flex-start;
  font-size: 12.5px;
  padding: 7px 14px;
}

/* Totals Summary Bar Pinned at Bottom */
.panel-totals-bar {
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-sidebar);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 36px;
}

.total-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.metric-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  font-feature-settings: "tnum";
}

.highlight-metric .metric-value {
  color: var(--accent-primary);
  font-size: 20px;
}

/* Slide animation */
.panel-slide-enter-active, .panel-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.panel-slide-enter-from, .panel-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>

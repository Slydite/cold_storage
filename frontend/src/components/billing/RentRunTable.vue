<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { useConfirm } from 'primevue/useconfirm'
import { FilterMatchMode } from '@primevue/core/api'
import {
  Search,
  Download,
  Calculator,
  Eye,
  FileCheck,
  XCircle,
  AlertCircle,
  RefreshCw,
  Receipt
} from 'lucide-vue-next'
import { formatCurrency } from '../../utils/format'
import { exportToCsv } from '../../utils/csvExport'
import type { RentRunOutput } from '../../api/billing'

interface Props {
  rentRuns: RentRunOutput[]
  loading: boolean
  error: boolean
  errorDetail?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  openCreate: []
  retry: []
  view: [rentRun: RentRunOutput]
  post: [id: number]
  cancel: [id: number]
}>()

const confirm = useConfirm()

const searchQuery = ref('')
const statusFilter = ref<string>('all')

const statusOptions = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Posted', value: 'POSTED' },
  { label: 'Cancelled', value: 'CANCELLED' }
]

const filters = ref({
  status: { value: null, matchMode: FilterMatchMode.EQUALS }
})

const filteredRentRuns = computed(() => {
  let list = props.rentRuns
  if (statusFilter.value !== 'all') {
    list = list.filter((r) => r.status === statusFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(
      (r) =>
        `#${r.id}`.includes(q) ||
        r.period_start.includes(q) ||
        r.period_end.includes(q) ||
        r.run_date.includes(q) ||
        (r.status && r.status.toLowerCase().includes(q))
    )
  }
  return list
})

const handleExport = () => {
  const headers = ['Rent Run ID', 'Period Start', 'Period End', 'Execution Date', 'Lots Count', 'Total Amount (₹)', 'Status']
  const rows = filteredRentRuns.value.map((r) => [
    `#${r.id}`,
    r.period_start,
    r.period_end,
    r.run_date,
    r.lines ? r.lines.length : 0,
    formatCurrency(Number(r.total_amount)),
    r.status || '-'
  ])
  exportToCsv('rent_runs.csv', headers, rows)
}

const handlePostConfirm = (id: number) => {
  confirm.require({
    message: 'Posting this Rent Run will finalize billing figures for this period. Do you want to proceed?',
    header: 'Post Rent Run',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Post Rent Run',
      severity: 'success'
    },
    accept: () => {
      emit('post', id)
    }
  })
}

const handleCancelConfirm = (id: number) => {
  confirm.require({
    message: 'Are you sure you want to cancel this Rent Run?',
    header: 'Cancel Rent Run',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Keep Rent Run',
      severity: 'secondary',
      outlined: true
    },
    acceptProps: {
      label: 'Yes, Cancel',
      severity: 'danger'
    },
    accept: () => {
      emit('cancel', id)
    }
  })
}
</script>

<template>
  <div class="rent-run-table-wrapper">
    <!-- Toolbar Header -->
    <div class="list-toolbar">
      <div class="toolbar-search">
        <div class="search-input-wrapper">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search period, date, status..."
            class="custom-search-input"
          />
        </div>
        <Select
          v-model="statusFilter"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          class="toolbar-select"
        />
      </div>

      <div class="toolbar-actions">
        <button class="btn-outlined" type="button" @click="handleExport">
          <Download :size="15" />
          <span>Export CSV</span>
        </button>
        <button class="btn-primary" type="button" @click="emit('openCreate')">
          <Calculator :size="16" />
          <span>Execute Rent Run</span>
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="props.error" class="state-card error-card">
      <AlertCircle :size="36" class="state-icon text-danger" />
      <h4 class="state-title">Failed to load Rent Runs</h4>
      <p class="state-desc">{{ props.errorDetail || 'There was an issue connecting to the server. Please try again.' }}</p>
      <button class="btn-primary" type="button" @click="emit('retry')">
        <RefreshCw :size="15" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Loading Skeleton State -->
    <div v-else-if="props.loading" class="skeleton-container">
      <Skeleton height="42px" class="mb-3" />
      <Skeleton height="56px" class="mb-2" v-for="i in 4" :key="i" />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredRentRuns.length === 0" class="state-card empty-card">
      <Receipt :size="40" class="state-icon text-muted" />
      <h4 class="state-title">No rent runs yet</h4>
      <p class="state-desc">No rent calculation runs have been executed for this period. Run one to bill storage charges.</p>
      <button class="btn-primary" type="button" @click="emit('openCreate')">
        <Calculator :size="16" />
        <span>Execute Rent Run</span>
      </button>
    </div>

    <!-- Happy Path: DataTable -->
    <div v-else class="table-card">
      <DataTable
        :value="filteredRentRuns"
        v-model:filters="filters"
        paginator
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        sortMode="multiple"
        removableSort
        size="small"
        stripedRows
        dataKey="id"
        responsiveLayout="scroll"
      >
        <Column field="id" header="Run ID" sortable>
          <template #body="{ data }">
            <span class="code-link">#{{ data.id }}</span>
          </template>
        </Column>

        <Column field="period_start" header="Billing Period" sortable>
          <template #body="{ data }">
            <span class="period-text">{{ data.period_start }} &rarr; {{ data.period_end }}</span>
          </template>
        </Column>

        <Column field="run_date" header="Execution Date" sortable />

        <Column header="Lots Billed">
          <template #body="{ data }">
            <span class="num-val">{{ data.lines ? data.lines.length : 0 }}</span>
          </template>
        </Column>

        <Column field="total_amount" header="Total Rent (₹)" sortable>
          <template #body="{ data }">
            <span class="num-val bold-val">{{ formatCurrency(Number(data.total_amount)) }}</span>
          </template>
        </Column>

        <Column field="status" header="Status" sortable>
          <template #body="{ data }">
            <span
              class="status-pill"
              :class="{
                success: data.status === 'POSTED',
                warning: data.status === 'DRAFT',
                danger: data.status === 'CANCELLED'
              }"
            >
              {{ data.status }}
            </span>
          </template>
        </Column>

        <Column header="Actions">
          <template #body="{ data }">
            <div class="row-actions">
              <button
                class="icon-btn"
                title="View rent run line details"
                type="button"
                @click="emit('view', data)"
              >
                <Eye :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn"
                title="Post rent run (finalize figures)"
                type="button"
                @click="handlePostConfirm(data.id)"
              >
                <FileCheck :size="16" />
              </button>
              <button
                v-if="data.status === 'DRAFT'"
                class="icon-btn danger-hover"
                title="Cancel rent run"
                type="button"
                @click="handleCancelConfirm(data.id)"
              >
                <XCircle :size="16" />
              </button>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.rent-run-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.period-text {
  font-weight: 500;
  color: var(--text-primary);
}

.bold-val {
  font-weight: 700;
  color: var(--accent-primary);
}

.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 36px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.state-icon.text-danger {
  color: var(--status-danger-color);
}

.state-icon.text-muted {
  color: var(--text-secondary);
}

.state-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.state-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  max-width: 380px;
  margin-bottom: 6px;
}

.skeleton-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 12px;
}
</style>

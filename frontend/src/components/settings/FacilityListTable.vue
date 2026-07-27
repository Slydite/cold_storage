<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import { useI18n } from 'vue-i18n'
import { Plus, RefreshCw, CheckCircle2 } from 'lucide-vue-next'
import { useFacility } from '../../composables/useFacility'
import FacilityCreateDialog from './FacilityCreateDialog.vue'

const { t } = useI18n()
const { facilities, selectedFacilityId, setSelectedFacilityId, isLoading, isError, refetch } =
  useFacility()

const isCreateDialogOpen = ref(false)
</script>

<template>
  <div class="facility-list-wrapper">
    <div class="list-toolbar">
      <div>
        <h3 class="toolbar-title">{{ t('settings.coldStorageFacilities') }}</h3>
        <p class="toolbar-desc">{{ t('settings.coldStorageFacilitiesDesc') }}</p>
      </div>

      <button type="button" class="btn-primary" @click="isCreateDialogOpen = true">
        <Plus :size="16" />
        <span>{{ t('settings.addFacility') }}</span>
      </button>
    </div>

    <div class="table-card">
      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="p-4">
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" />
      </div>

      <!-- Error State -->
      <div v-else-if="isError" class="error-state">
        <p>{{ t('errors.failedToLoadFacility') }}</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>{{ t('common.retry') }}</span>
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="facilities.length === 0" class="empty-state">
        <h3>{{ t('settings.noFacilitiesRegistered') }}</h3>
        <p>{{ t('settings.noFacilitiesDesc') }}</p>
        <button type="button" class="btn-primary" @click="isCreateDialogOpen = true">
          <Plus :size="16" />
          <span>{{ t('settings.addFacility') }}</span>
        </button>
      </div>

      <!-- Data Table -->
      <DataTable
        v-else
        :value="facilities"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column :header="t('common.actions')" alignFrozen="left">
          <template #body="{ data }">
            <button
              v-if="data.id !== selectedFacilityId"
              type="button"
              class="btn-outlined btn-xs"
              @click="setSelectedFacilityId(data.id)"
            >
              <CheckCircle2 :size="14" />
              <span>{{ t('common.setWorking') }}</span>
            </button>
            <span v-else class="working-badge">{{ t('common.currentlySelected') }}</span>
          </template>
        </Column>

        <Column field="code" :header="t('common.code')">
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" :header="t('locations.facility') + ' ' + t('common.name')">
          <template #body="{ data }">
            <div class="facility-name-cell">
              <span class="name-text">{{ data.name }}</span>
              <Tag
                v-if="data.id === selectedFacilityId"
                :value="t('common.activeWorkingFacility')"
                severity="success"
                class="ml-2"
              />
            </div>
          </template>
        </Column>

        <Column field="phone" :header="t('common.phone')">
          <template #body="{ data }">
            {{ data.phone || data.factory_phone || '-' }}
          </template>
        </Column>

        <Column field="gstin" :header="t('common.gstin')">
          <template #body="{ data }">
            {{ data.gstin || '-' }}
          </template>
        </Column>
      </DataTable>
    </div>

    <FacilityCreateDialog
      v-model:visible="isCreateDialogOpen"
      @created="refetch()"
    />
  </div>
</template>

<style scoped>
.facility-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.toolbar-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.facility-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-text {
  font-weight: 600;
  color: var(--text-primary);
}

.btn-xs {
  padding: 5px 10px;
  font-size: 12px;
  border-radius: 6px;
}

.working-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--status-success-color);
}

.error-state,
.empty-state {
  padding: 36px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
}

.p-4 {
  padding: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>

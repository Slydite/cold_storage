<script setup lang="ts">
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { Building, Layers, Package, Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import FacilityForm from '../components/settings/FacilityForm.vue'
import FacilityListTable from '../components/settings/FacilityListTable.vue'
import ChamberManager from '../components/settings/ChamberManager.vue'
import FloorManager from '../components/settings/FloorManager.vue'
import BlockManager from '../components/settings/BlockManager.vue'
import CommodityManager from '../components/settings/CommodityManager.vue'
import UserManager from '../components/settings/UserManager.vue'

const { t } = useI18n()
</script>

<template>
  <div class="page-container settings-page">
    <header class="settings-header">
      <h2 class="page-title">{{ t('settings.settingsTitle') }}</h2>
      <p class="page-subtitle">{{ t('settings.settingsSubtitle') }}</p>
    </header>

    <Tabs value="facility" class="settings-tabs">
      <TabList class="custom-tab-list">
        <Tab value="facility" class="tab-item">
          <Building :size="16" />
          <span>{{ t('settings.facilityManagement') }}</span>
        </Tab>
        <Tab value="locations" class="tab-item">
          <Layers :size="16" />
          <span>{{ t('settings.locationsTab') }}</span>
        </Tab>
        <Tab value="commodities" class="tab-item">
          <Package :size="16" />
          <span>{{ t('settings.commoditiesTab') }}</span>
        </Tab>
        <Tab value="users" class="tab-item">
          <Users :size="16" />
          <span>{{ t('settings.userAccountsTab') }}</span>
        </Tab>
      </TabList>

      <TabPanels class="custom-tab-panels">
        <TabPanel value="facility">
          <div class="facility-tab-content">
            <FacilityForm />
            <FacilityListTable />
          </div>
        </TabPanel>

        <TabPanel value="locations">
          <div class="locations-tab-content">
            <ChamberManager />
            <FloorManager />
            <BlockManager />
          </div>
        </TabPanel>

        <TabPanel value="commodities">
          <CommodityManager />
        </TabPanel>

        <TabPanel value="users">
          <UserManager />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

.settings-tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.custom-tab-list {
  display: flex;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 6px;
  box-shadow: var(--shadow-card);
  overflow-x: auto;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border: none;
  background: transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.tab-item:hover {
  color: var(--text-primary);
  background: var(--bg-surface-hover);
}

.tab-item[aria-selected="true"],
.tab-item.p-tab-active {
  color: #ffffff;
  background: var(--accent-primary);
}

.custom-tab-panels {
  padding: 0;
  background: transparent;
}

.facility-tab-content,
.locations-tab-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 640px) {
  .custom-tab-list {
    padding: 4px;
  }
  .tab-item {
    padding: 7px 12px;
    font-size: 12px;
  }
}
</style>

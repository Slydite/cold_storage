<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
import { FileCheck2, Truck, Activity } from 'lucide-vue-next'
import type { ActivityItem } from '../../composables/useDashboardStats'

defineProps<{
  activities: ActivityItem[]
  loading: boolean
}>()
</script>

<template>
  <div class="card-panel activities-panel">
    <div class="panel-header">
      <h3 class="panel-title">Recent Activities</h3>
      <router-link to="/grn" class="view-all-link">
        <span>View all</span>
      </router-link>
    </div>

    <div v-if="loading" class="activities-list">
      <div v-for="n in 5" :key="n" class="activity-item">
        <Skeleton shape="circle" size="36px" />
        <div class="activity-details">
          <Skeleton width="70%" height="1rem" style="margin-bottom: 4px" />
          <Skeleton width="40%" height="0.8rem" />
        </div>
      </div>
    </div>

    <div v-else-if="activities.length === 0" class="empty-activities">
      <Activity :size="28" class="empty-icon" />
      <span>No recent activity recorded yet</span>
    </div>

    <div v-else class="activities-list">
      <div v-for="act in activities" :key="act.id" class="activity-item">
        <div class="activity-icon-badge" :class="act.badgeClass">
          <FileCheck2 v-if="act.type === 'grn'" :size="16" />
          <Truck v-else :size="16" />
        </div>
        <div class="activity-details">
          <div class="activity-title">
            <span>{{ act.title }}</span>
          </div>
          <div v-if="act.partyName" class="activity-meta">
            Party: <span class="party-name">{{ act.partyName }}</span>
          </div>
        </div>
        <div class="activity-time">{{ act.time }}</div>
      </div>
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

.view-all-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-primary);
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

.badge-purple {
  background: var(--badge-violet-bg);
  color: var(--badge-violet-color);
}

.badge-blue {
  background: var(--badge-blue-bg);
  color: var(--badge-blue-color);
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

.activity-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.party-name {
  color: var(--text-primary);
  font-weight: 500;
}

.activity-time {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  font-weight: 500;
}

.empty-activities {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.empty-icon {
  opacity: 0.5;
}
</style>

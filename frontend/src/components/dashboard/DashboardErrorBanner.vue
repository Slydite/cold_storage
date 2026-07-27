<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { AlertTriangle, RefreshCw } from 'lucide-vue-next'

defineProps<{
  message: string
}>()

const emit = defineEmits<{
  (e: 'retry'): void
}>()

const { t } = useI18n()
</script>

<template>
  <div class="error-banner">
    <div class="error-info">
      <AlertTriangle :size="20" class="error-icon" />
      <span>{{ message }}</span>
    </div>
    <button class="btn-retry" @click="emit('retry')" type="button">
      <RefreshCw :size="14" />
      <span>{{ t('common.retry') }}</span>
    </button>
  </div>
</template>

<style scoped>
.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--status-danger-bg);
  border: 1px solid var(--status-danger-color);
  color: var(--status-danger-color);
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 13.5px;
  font-weight: 500;
}

.error-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.error-icon {
  flex-shrink: 0;
}

.btn-retry {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: var(--status-danger-color);
  color: #ffffff;
  border: none;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.btn-retry:hover {
  opacity: 0.9;
}
</style>

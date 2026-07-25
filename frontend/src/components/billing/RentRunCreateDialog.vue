<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import { Calculator } from 'lucide-vue-next'
import { useRentRunForm } from '../../composables/useRentRunForm'
import type { RentRunOutput } from '../../api/billing'

interface Props {
  visible: boolean
  facilityId: number | undefined
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: [rentRun: RentRunOutput]
}>()

const facilityIdRef = computed(() => props.facilityId)

const {
  period_start,
  periodStartProps,
  period_end,
  periodEndProps,
  errors,
  submitForm,
  isSubmitting,
  resetForm
} = useRentRunForm(facilityIdRef, (createdRun) => {
  emit('update:visible', false)
  emit('created', createdRun)
})

const handleClose = () => {
  resetForm()
  emit('update:visible', false)
}

const handleRun = () => {
  submitForm()
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    header="Execute Rent Run"
    :style="{ width: '440px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div class="form-dialog-body">
      <p class="dialog-hint">
        Select the billing period. Storage rent will be prorated by days stored for each active lot matching a valid rate card.
      </p>

      <div class="form-group">
        <label class="form-label">Period Start Date <span class="req">*</span></label>
        <DatePicker
          v-model="period_start"
          v-bind="periodStartProps"
          dateFormat="dd/mm/yy"
          showIcon
          class="w-full"
          :invalid="!!errors.period_start"
        />
        <small v-if="errors.period_start" class="field-error">{{ errors.period_start }}</small>
      </div>

      <div class="form-group">
        <label class="form-label">Period End Date <span class="req">*</span></label>
        <DatePicker
          v-model="period_end"
          v-bind="periodEndProps"
          dateFormat="dd/mm/yy"
          showIcon
          class="w-full"
          :invalid="!!errors.period_end"
        />
        <small v-if="errors.period_end" class="field-error">{{ errors.period_end }}</small>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-actions">
        <button class="btn-text" type="button" @click="handleClose">Cancel</button>
        <button
          class="btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="handleRun"
        >
          <Calculator :size="16" />
          <span>{{ isSubmitting ? 'Calculating...' : 'Calculate & Run Rent' }}</span>
        </button>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.form-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

.dialog-hint {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.4;
  background: var(--bg-surface-hover);
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.req {
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.field-error {
  color: var(--status-danger-color);
  font-size: 11.5px;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}
</style>

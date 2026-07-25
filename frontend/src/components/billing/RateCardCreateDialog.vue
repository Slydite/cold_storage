<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Checkbox from 'primevue/checkbox'
import { useQuery } from '@tanstack/vue-query'
import { fetchCommodities } from '../../api/commodity'
import { useRateCardForm } from '../../composables/useRateCardForm'

interface Props {
  visible: boolean
  facilityId: number | undefined
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: []
}>()

const facilityIdRef = computed(() => props.facilityId)

const commoditiesQuery = useQuery({
  queryKey: computed(() => ['commodities', props.facilityId]),
  queryFn: () => fetchCommodities({ facilityId: props.facilityId! }),
  enabled: computed(() => !!props.facilityId && props.visible)
})

const commodities = computed(() => commoditiesQuery.data.value || [])

const weightCategoryOptions = [
  { label: '20 kg Bag (KG_20)', value: 'KG_20' },
  { label: '50 kg Bag (KG_50)', value: 'KG_50' },
  { label: 'Other Weight Category (OTHER)', value: 'OTHER' }
]

const {
  commodity_id,
  commodityIdProps,
  weight_category,
  weightCategoryProps,
  rate_per_bag_per_month,
  ratePerBagProps,
  effective_from,
  effectiveFromProps,
  is_active,
  isActiveProps,
  errors,
  submitForm,
  isSubmitting,
  resetForm
} = useRateCardForm(facilityIdRef, () => {
  emit('update:visible', false)
  emit('created')
})

const handleClose = () => {
  resetForm()
  emit('update:visible', false)
}

const handleSave = () => {
  submitForm()
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="emit('update:visible', $event)"
    modal
    header="Create Rate Card"
    :style="{ width: '460px', maxWidth: '95vw' }"
    :dismissableMask="true"
    @hide="handleClose"
  >
    <div class="form-dialog-body">
      <div class="form-group">
        <label class="form-label">Commodity <span class="req">*</span></label>
        <Select
          v-model="commodity_id"
          v-bind="commodityIdProps"
          :options="commodities"
          optionLabel="name"
          optionValue="id"
          placeholder="Select Commodity"
          :loading="commoditiesQuery.isLoading.value"
          class="w-full"
          :invalid="!!errors.commodity_id"
        />
        <small v-if="errors.commodity_id" class="field-error">{{ errors.commodity_id }}</small>
      </div>

      <div class="form-group">
        <label class="form-label">Weight Category <span class="req">*</span></label>
        <Select
          v-model="weight_category"
          v-bind="weightCategoryProps"
          :options="weightCategoryOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Select Weight Category"
          class="w-full"
          :invalid="!!errors.weight_category"
        />
        <small v-if="errors.weight_category" class="field-error">{{ errors.weight_category }}</small>
      </div>

      <div class="form-group">
        <label class="form-label">Rate / Bag / Month (₹) <span class="req">*</span></label>
        <InputNumber
          v-model="rate_per_bag_per_month"
          v-bind="ratePerBagProps"
          mode="currency"
          currency="INR"
          locale="en-IN"
          :min="0.01"
          :minFractionDigits="2"
          :maxFractionDigits="2"
          placeholder="e.g. ₹ 25.00"
          class="w-full"
          :invalid="!!errors.rate_per_bag_per_month"
        />
        <small v-if="errors.rate_per_bag_per_month" class="field-error">{{ errors.rate_per_bag_per_month }}</small>
      </div>

      <div class="form-group">
        <label class="form-label">Effective From <span class="req">*</span></label>
        <DatePicker
          v-model="effective_from"
          v-bind="effectiveFromProps"
          dateFormat="dd/mm/yy"
          showIcon
          class="w-full"
          :invalid="!!errors.effective_from"
        />
        <small v-if="errors.effective_from" class="field-error">{{ errors.effective_from }}</small>
      </div>

      <div class="form-group-checkbox">
        <Checkbox
          v-model="is_active"
          v-bind="isActiveProps"
          :binary="true"
          inputId="is_active_cb"
        />
        <label for="is_active_cb" class="checkbox-label">Active (enable for rent runs)</label>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-actions">
        <button class="btn-text" type="button" @click="handleClose">Cancel</button>
        <button
          class="btn-primary"
          type="button"
          :disabled="isSubmitting"
          @click="handleSave"
        >
          <span>{{ isSubmitting ? 'Saving...' : 'Save Rate Card' }}</span>
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

.form-group-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.checkbox-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}
</style>

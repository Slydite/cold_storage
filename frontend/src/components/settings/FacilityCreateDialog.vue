<script setup lang="ts">
import { watch, computed, toRef } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useCreateFacility } from '../../composables/useFacilities'
import { useHistoryDismiss } from '../../composables/useHistoryDismiss'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: []
}>()

const visibleRef = toRef(props, 'visible')
useHistoryDismiss(visibleRef, () => {
  emit('update:visible', false)
})

const { t } = useI18n()
const toast = useToast()
const createFacilityMutation = useCreateFacility()

const facilitySchema = computed(() =>
  z.object({
    name: z.string().min(1, t('validation.facilityNameRequired')),
    address: z.string().optional(),
    gstin: z.string().optional(),
    phone: z.string().optional(),
    factory_phone: z.string().optional(),
    bank_account_no: z.string().optional(),
    bank_ifsc: z.string().optional(),
    terms_and_conditions: z.string().optional()
  })
)

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(facilitySchema.value)),
  initialValues: {
    name: '',
    address: '',
    gstin: '',
    phone: '',
    factory_phone: '',
    bank_account_no: '',
    bank_ifsc: '',
    terms_and_conditions: ''
  }
})

const [name, nameProps] = defineField('name')
const [address, addressProps] = defineField('address')
const [gstin, gstinProps] = defineField('gstin')
const [phone, phoneProps] = defineField('phone')
const [factory_phone, factoryPhoneProps] = defineField('factory_phone')
const [bank_account_no, bankAccountNoProps] = defineField('bank_account_no')
const [bank_ifsc, bankIfscProps] = defineField('bank_ifsc')
const [terms_and_conditions, termsProps] = defineField('terms_and_conditions')

watch(
  () => props.visible,
  (val) => {
    if (val) {
      resetForm({
        values: {
          name: '',
          address: '',
          gstin: '',
          phone: '',
          factory_phone: '',
          bank_account_no: '',
          bank_ifsc: '',
          terms_and_conditions: ''
        }
      })
    }
  }
)

const onSubmit = handleSubmit(async (values) => {
  try {
    await createFacilityMutation.mutateAsync({
      name: values.name,
      address: values.address || undefined,
      gstin: values.gstin || undefined,
      phone: values.phone || undefined,
      factory_phone: values.factory_phone || undefined,
      bank_account_no: values.bank_account_no || undefined,
      bank_ifsc: values.bank_ifsc || undefined,
      terms_and_conditions: values.terms_and_conditions || undefined
    })
    toast.add({
      severity: 'success',
      summary: t('settings.facilityCreatedSummary'),
      detail: t('settings.facilityCreatedDetail', { name: values.name }),
      life: 3000
    })
    emit('update:visible', false)
    emit('created')
  } catch (err) {
    const msg = err instanceof Error ? err.message : t('settings.facilityCreateFailed')
    toast.add({
      severity: 'error',
      summary: t('settings.facilityCreateFailed'),
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :header="t('settings.addWorkingFacility')"
    :style="{ width: '560px' }"
  >
    <form @submit.prevent="onSubmit" class="dialog-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="new-fac-name">{{ t('locations.facility') }} {{ t('common.name') }} <span class="required">*</span></label>
          <InputText
            id="new-fac-name"
            v-model="name"
            v-bind="nameProps"
            :placeholder="t('locations.facility')"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="new-fac-gstin">{{ t('common.gstin') }}</label>
          <InputText
            id="new-fac-gstin"
            v-model="gstin"
            v-bind="gstinProps"
            placeholder="e.g. 24AAAAA0000A1Z5"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-phone">{{ t('settings.officePhone') }}</label>
          <InputText
            id="new-fac-phone"
            v-model="phone"
            v-bind="phoneProps"
            :placeholder="t('settings.officePhone')"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-factory-phone">{{ t('settings.factoryGatePhone') }}</label>
          <InputText
            id="new-fac-factory-phone"
            v-model="factory_phone"
            v-bind="factoryPhoneProps"
            :placeholder="t('settings.factoryGatePhone')"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-bank-ac">{{ t('settings.bankAccountNo') }}</label>
          <InputText
            id="new-fac-bank-ac"
            v-model="bank_account_no"
            v-bind="bankAccountNoProps"
            :placeholder="t('settings.bankAccountNo')"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-bank-ifsc">{{ t('settings.bankIfscCode') }}</label>
          <InputText
            id="new-fac-bank-ifsc"
            v-model="bank_ifsc"
            v-bind="bankIfscProps"
            placeholder="e.g. SBIN0013139"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="new-fac-address">{{ t('settings.facilityAddress') }}</label>
          <InputText
            id="new-fac-address"
            v-model="address"
            v-bind="addressProps"
            :placeholder="t('settings.facilityAddress')"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="new-fac-terms">{{ t('settings.termsConditions') }}</label>
          <Textarea
            id="new-fac-terms"
            v-model="terms_and_conditions"
            v-bind="termsProps"
            rows="2"
            :placeholder="t('settings.termsConditions')"
            class="w-full"
          />
        </div>
      </div>

      <div class="dialog-actions">
        <button
          type="button"
          class="btn-outlined"
          @click="emit('update:visible', false)"
          :disabled="createFacilityMutation.isPending.value"
        >
          {{ t('common.cancel') }}
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="createFacilityMutation.isPending.value"
        >
          {{ createFacilityMutation.isPending.value ? t('common.loading') : t('settings.addFacility') }}
        </button>
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.span-2 {
  grid-column: span 2;
}

@media (max-width: 500px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: span 1;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--status-danger-color);
}

.field-error {
  font-size: 12px;
  color: var(--status-danger-color);
}

.w-full {
  width: 100%;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>

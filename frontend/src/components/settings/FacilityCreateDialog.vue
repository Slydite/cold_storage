<script setup lang="ts">
import { watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useCreateFacility } from '../../composables/useFacilities'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  created: []
}>()

const toast = useToast()
const createFacilityMutation = useCreateFacility()

const facilitySchema = z.object({
  name: z.string().min(1, 'Facility name is required'),
  code: z.string().min(1, 'Facility code is required'),
  address: z.string().optional(),
  gstin: z.string().optional(),
  phone: z.string().optional(),
  factory_phone: z.string().optional(),
  bank_account_no: z.string().optional(),
  bank_ifsc: z.string().optional(),
  terms_and_conditions: z.string().optional()
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(facilitySchema),
  initialValues: {
    name: '',
    code: '',
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
const [code, codeProps] = defineField('code')
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
          code: '',
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
      code: values.code,
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
      summary: 'Facility Created',
      detail: `Facility "${values.name}" created successfully`,
      life: 3000
    })
    emit('update:visible', false)
    emit('created')
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Failed to create facility'
    toast.add({
      severity: 'error',
      summary: 'Creation Failed',
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
    header="Add Working Facility"
    :style="{ width: '560px' }"
  >
    <form @submit.prevent="onSubmit" class="dialog-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="new-fac-name">Facility Name <span class="required">*</span></label>
          <InputText
            id="new-fac-name"
            v-model="name"
            v-bind="nameProps"
            placeholder="e.g. Main Cold Storage"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="new-fac-code">Facility Code <span class="required">*</span></label>
          <InputText
            id="new-fac-code"
            v-model="code"
            v-bind="codeProps"
            placeholder="e.g. FAC-01"
            class="w-full"
            :class="{ 'p-invalid': errors.code }"
          />
          <span v-if="errors.code" class="field-error">{{ errors.code }}</span>
        </div>

        <div class="form-group">
          <label for="new-fac-gstin">GSTIN</label>
          <InputText
            id="new-fac-gstin"
            v-model="gstin"
            v-bind="gstinProps"
            placeholder="e.g. 24AAAAA0000A1Z5"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-phone">Phone</label>
          <InputText
            id="new-fac-phone"
            v-model="phone"
            v-bind="phoneProps"
            placeholder="Office phone"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-factory-phone">Factory Phone</label>
          <InputText
            id="new-fac-factory-phone"
            v-model="factory_phone"
            v-bind="factoryPhoneProps"
            placeholder="Gate phone"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-bank-ac">Bank Account No.</label>
          <InputText
            id="new-fac-bank-ac"
            v-model="bank_account_no"
            v-bind="bankAccountNoProps"
            placeholder="A/C number"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="new-fac-bank-ifsc">Bank IFSC</label>
          <InputText
            id="new-fac-bank-ifsc"
            v-model="bank_ifsc"
            v-bind="bankIfscProps"
            placeholder="e.g. SBIN0013139"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="new-fac-address">Address</label>
          <InputText
            id="new-fac-address"
            v-model="address"
            v-bind="addressProps"
            placeholder="Facility location"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="new-fac-terms">Terms & Conditions</label>
          <Textarea
            id="new-fac-terms"
            v-model="terms_and_conditions"
            v-bind="termsProps"
            rows="2"
            placeholder="Terms for invoices/GRN"
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
          Cancel
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="createFacilityMutation.isPending.value"
        >
          {{ createFacilityMutation.isPending.value ? 'Creating...' : 'Create Facility' }}
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

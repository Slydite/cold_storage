<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import type { TypeEnum } from '../../api/party'

interface Props {
  visible: boolean
  loading?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  submit: [
    values: {
      name: string
      type: TypeEnum
      phone?: string
      email?: string
      address?: string
      gstin?: string
    }
  ]
}>()

const { t } = useI18n()

const typeOptions = computed(() => [
  { label: t('parties.depositorCustomer'), value: 'DEPOSITOR' },
  { label: t('parties.vendor'), value: 'VENDOR' },
  { label: t('parties.transporter'), value: 'TRANSPORTER' }
])

const partySchema = computed(() =>
  z.object({
    name: z.string().min(1, t('validation.nameRequired')),
    type: z.enum(['DEPOSITOR', 'VENDOR', 'TRANSPORTER']),
    phone: z.string().optional(),
    email: z.string().email(t('validation.invalidEmail')).or(z.literal('')).optional(),
    address: z.string().optional(),
    gstin: z.string().optional()
  })
)

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(partySchema.value)),
  initialValues: {
    name: '',
    type: 'DEPOSITOR' as TypeEnum,
    phone: '',
    email: '',
    address: '',
    gstin: ''
  }
})

const [name, nameProps] = defineField('name')
const [type] = defineField('type')
const [phone, phoneProps] = defineField('phone')
const [email, emailProps] = defineField('email')
const [address, addressProps] = defineField('address')
const [gstin, gstinProps] = defineField('gstin')

const onSubmit = handleSubmit((values) => {
  emit('submit', {
    name: values.name,
    type: values.type,
    phone: values.phone || undefined,
    email: values.email || undefined,
    address: values.address || undefined,
    gstin: values.gstin || undefined
  })
  resetForm()
})

const handleCancel = () => {
  resetForm()
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="(val) => emit('update:visible', val)"
    modal
    :header="t('parties.addNewParty')"
    :style="{ width: '500px', maxWidth: '95vw' }"
  >
    <form @submit.prevent="onSubmit" class="dialog-form">
      <div class="form-group">
        <label for="party-name" class="form-label">{{ t('parties.partyName') }} <span class="req">*</span></label>
        <InputText
          id="party-name"
          v-model="name"
          v-bind="nameProps"
          placeholder="e.g. Ramesh Traders"
          class="w-full"
          :class="{ 'p-invalid': errors.name }"
        />
        <small v-if="errors.name" class="field-error">{{ errors.name }}</small>
      </div>

      <div class="form-group">
        <label for="party-type" class="form-label">{{ t('parties.partyType') }} <span class="req">*</span></label>
        <Select
          id="party-type"
          v-model="type"
          :options="typeOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
        />
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label for="party-phone" class="form-label">{{ t('parties.phone') }}</label>
          <InputText
            id="party-phone"
            v-model="phone"
            v-bind="phoneProps"
            placeholder="e.g. 9876543210"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="party-email" class="form-label">{{ t('parties.email') }}</label>
          <InputText
            id="party-email"
            v-model="email"
            v-bind="emailProps"
            type="email"
            placeholder="e.g. ramesh@traders.com"
            class="w-full"
            :class="{ 'p-invalid': errors.email }"
          />
          <small v-if="errors.email" class="field-error">{{ errors.email }}</small>
        </div>
      </div>

      <div class="form-group">
        <label for="party-gstin" class="form-label">{{ t('parties.gstin') }}</label>
        <InputText
          id="party-gstin"
          v-model="gstin"
          v-bind="gstinProps"
          placeholder="e.g. 24AAAAA0000A1Z5"
          class="w-full"
        />
      </div>

      <div class="form-group">
        <label for="party-address" class="form-label">{{ t('parties.address') }}</label>
        <Textarea
          id="party-address"
          v-model="address"
          v-bind="addressProps"
          rows="2"
          placeholder="Full address details..."
          class="w-full"
        />
      </div>

      <div class="dialog-actions">
        <button type="button" class="btn-outlined" @click="handleCancel">
          {{ t('common.cancel') }}
        </button>
        <button type="submit" class="btn-primary" :disabled="props.loading">
          {{ t('parties.addParty') }}
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
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.req {
  color: var(--status-danger-color);
}

.field-error {
  font-size: 11.5px;
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

@media (max-width: 500px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

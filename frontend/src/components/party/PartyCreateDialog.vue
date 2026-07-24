<script setup lang="ts">
import { watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import type { TypeEnum } from '../../api/party'

interface Props {
  visible: boolean
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  submit: [values: { name: string; code: string; type: TypeEnum; phone?: string; email?: string }]
}>()

const partySchema = z.object({
  name: z.string().min(1, 'Name is required'),
  code: z.string().min(1, 'Code is required'),
  type: z.enum(['DEPOSITOR', 'VENDOR', 'TRANSPORTER'], {
    message: 'Type is required'
  }),
  phone: z.string().optional(),
  email: z.string().email('Invalid email address').or(z.literal('')).optional()
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(partySchema),
  initialValues: {
    name: '',
    code: '',
    type: 'DEPOSITOR' as TypeEnum,
    phone: '',
    email: ''
  }
})

const [name, nameAttrs] = defineField('name')
const [code, codeAttrs] = defineField('code')
const [type] = defineField('type')
const [phone, phoneAttrs] = defineField('phone')
const [email, emailAttrs] = defineField('email')

const typeOptions = [
  { label: 'Depositor / Customer', value: 'DEPOSITOR' },
  { label: 'Vendor', value: 'VENDOR' },
  { label: 'Transporter', value: 'TRANSPORTER' }
]

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      resetForm({
        values: {
          name: '',
          code: '',
          type: 'DEPOSITOR',
          phone: '',
          email: ''
        }
      })
    }
  }
)

const onSubmit = handleSubmit((values) => {
  emit('submit', {
    name: values.name,
    code: values.code,
    type: values.type,
    phone: values.phone || undefined,
    email: values.email || undefined
  })
})
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    header="Add New Party"
    :style="{ width: '450px' }"
  >
    <form @submit.prevent="onSubmit" class="party-form">
      <div class="form-field">
        <label for="party-name">Party Name <span class="required">*</span></label>
        <input
          id="party-name"
          v-model="name"
          v-bind="nameAttrs"
          type="text"
          placeholder="e.g. Shree Traders"
          class="form-input"
          :class="{ 'has-error': errors.name }"
        />
        <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
      </div>

      <div class="form-field">
        <label for="party-code">Party Code <span class="required">*</span></label>
        <input
          id="party-code"
          v-model="code"
          v-bind="codeAttrs"
          type="text"
          placeholder="e.g. PRT-001"
          class="form-input"
          :class="{ 'has-error': errors.code }"
        />
        <span v-if="errors.code" class="field-error">{{ errors.code }}</span>
      </div>

      <div class="form-field">
        <label for="party-type">Party Type <span class="required">*</span></label>
        <Select
          id="party-type"
          v-model="type"
          :options="typeOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
        />
        <span v-if="errors.type" class="field-error">{{ errors.type }}</span>
      </div>

      <div class="form-field">
        <label for="party-phone">Phone Number</label>
        <input
          id="party-phone"
          v-model="phone"
          v-bind="phoneAttrs"
          type="text"
          placeholder="e.g. +91 98250 12345"
          class="form-input"
          :class="{ 'has-error': errors.phone }"
        />
        <span v-if="errors.phone" class="field-error">{{ errors.phone }}</span>
      </div>

      <div class="form-field">
        <label for="party-email">Email Address</label>
        <input
          id="party-email"
          v-model="email"
          v-bind="emailAttrs"
          type="email"
          placeholder="e.g. info@shreetraders.com"
          class="form-input"
          :class="{ 'has-error': errors.email }"
        />
        <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
      </div>

      <div class="dialog-actions">
        <button
          type="button"
          class="btn-outlined"
          @click="emit('update:visible', false)"
          :disabled="loading"
        >
          Cancel
        </button>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Saving...' : 'Save Party' }}
        </button>
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.party-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--status-danger-color);
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-page);
  color: var(--text-primary);
  font-size: 13px;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.form-input.has-error {
  border-color: var(--status-danger-color);
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
  margin-top: 12px;
}
</style>

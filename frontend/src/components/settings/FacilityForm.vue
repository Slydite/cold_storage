<script setup lang="ts">
import { watch, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Skeleton from 'primevue/skeleton'
import { Save, RefreshCw, Building } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useFacility } from '../../composables/useFacility'
import { useUpdateFacility } from '../../composables/useFacilities'

const toast = useToast()
const { facilityId, facilities, isLoading, isError, refetch } = useFacility()
const updateFacilityMutation = useUpdateFacility()

const currentFacility = computed(() => {
  if (!facilityId.value) return null
  return facilities.value.find((f) => f.id === facilityId.value) ?? null
})

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
  currentFacility,
  (fac) => {
    if (fac) {
      resetForm({
        values: {
          name: fac.name ?? '',
          code: fac.code ?? '',
          address: fac.address ?? '',
          gstin: fac.gstin ?? '',
          phone: fac.phone ?? '',
          factory_phone: fac.factory_phone ?? '',
          bank_account_no: fac.bank_account_no ?? '',
          bank_ifsc: fac.bank_ifsc ?? '',
          terms_and_conditions: fac.terms_and_conditions ?? ''
        }
      })
    }
  },
  { immediate: true }
)

const onSubmit = handleSubmit(async (values) => {
  if (!currentFacility.value) return
  try {
    await updateFacilityMutation.mutateAsync({
      id: currentFacility.value.id,
      body: {
        name: values.name,
        code: values.code,
        address: values.address || undefined,
        gstin: values.gstin || undefined,
        phone: values.phone || undefined,
        factory_phone: values.factory_phone || undefined,
        bank_account_no: values.bank_account_no || undefined,
        bank_ifsc: values.bank_ifsc || undefined,
        terms_and_conditions: values.terms_and_conditions || undefined
      }
    })
    toast.add({
      severity: 'success',
      summary: 'Saved',
      detail: 'Facility details updated successfully',
      life: 3000
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Failed to update facility details'
    toast.add({
      severity: 'error',
      summary: 'Update Failed',
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <div class="facility-form-wrapper">
    <!-- Loading Skeleton -->
    <div v-if="isLoading" class="skeleton-container">
      <Skeleton height="32px" width="200px" class="mb-4" />
      <div class="form-grid">
        <Skeleton height="40px" v-for="n in 8" :key="n" />
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="isError" class="state-card error-state">
      <p class="error-msg">Failed to load facility data.</p>
      <button type="button" class="btn-outlined" @click="refetch()">
        <RefreshCw :size="14" />
        <span>Retry</span>
      </button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!currentFacility" class="state-card empty-state">
      <Building :size="40" class="empty-icon" />
      <h3>No Facility Selected</h3>
      <p>Please select a working facility from the sidebar or list table.</p>
    </div>

    <!-- Form Content -->
    <form v-else @submit.prevent="onSubmit" class="facility-card">
      <div class="card-header">
        <div>
          <h3 class="card-title">Facility Profile & Details</h3>
          <p class="card-desc">
            Edit master details for <strong>{{ currentFacility.name }}</strong> (Code: {{ currentFacility.code }}).
          </p>
        </div>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label for="fac-name">Facility Name <span class="required">*</span></label>
          <InputText
            id="fac-name"
            v-model="name"
            v-bind="nameProps"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="fac-code">Facility Code <span class="required">*</span></label>
          <InputText
            id="fac-code"
            v-model="code"
            v-bind="codeProps"
            class="w-full"
            :class="{ 'p-invalid': errors.code }"
          />
          <span v-if="errors.code" class="field-error">{{ errors.code }}</span>
        </div>

        <div class="form-group">
          <label for="fac-gstin">GSTIN</label>
          <InputText
            id="fac-gstin"
            v-model="gstin"
            v-bind="gstinProps"
            placeholder="e.g. 24AAAAA0000A1Z5"
            class="w-full"
            :class="{ 'p-invalid': errors.gstin }"
          />
          <span v-if="errors.gstin" class="field-error">{{ errors.gstin }}</span>
        </div>

        <div class="form-group">
          <label for="fac-phone">Office Phone</label>
          <InputText
            id="fac-phone"
            v-model="phone"
            v-bind="phoneProps"
            placeholder="e.g. +91 98250 00000"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="fac-factory-phone">Factory/Gate Phone</label>
          <InputText
            id="fac-factory-phone"
            v-model="factory_phone"
            v-bind="factoryPhoneProps"
            placeholder="e.g. +91 98250 11111"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="fac-bank-ac">Bank Account No.</label>
          <InputText
            id="fac-bank-ac"
            v-model="bank_account_no"
            v-bind="bankAccountNoProps"
            placeholder="Account number"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="fac-bank-ifsc">Bank IFSC Code</label>
          <InputText
            id="fac-bank-ifsc"
            v-model="bank_ifsc"
            v-bind="bankIfscProps"
            placeholder="e.g. SBIN0001234"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="fac-address">Facility Address</label>
          <InputText
            id="fac-address"
            v-model="address"
            v-bind="addressProps"
            placeholder="Full postal address"
            class="w-full"
          />
        </div>

        <div class="form-group span-2">
          <label for="fac-terms">Terms & Conditions</label>
          <Textarea
            id="fac-terms"
            v-model="terms_and_conditions"
            v-bind="termsProps"
            rows="3"
            placeholder="Default terms printed on GRN/Invoices..."
            class="w-full"
          />
        </div>
      </div>

      <div class="actions-row">
        <button
          type="submit"
          class="btn-primary"
          :disabled="updateFacilityMutation.isPending.value"
        >
          <Save :size="16" />
          <span>{{ updateFacilityMutation.isPending.value ? 'Saving...' : 'Save Profile' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.facility-form-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.facility-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 20px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.span-2 {
  grid-column: span 2;
}

@media (max-width: 640px) {
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
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
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

.actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.state-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  color: var(--text-secondary);
}

.skeleton-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 20px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>

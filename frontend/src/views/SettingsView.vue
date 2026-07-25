<script setup lang="ts">
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { Save } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const facilityName = ref('Main Cold Storage')
const gstin = ref('24AAAAA0000A1Z5')
const address = ref('Plot 42, Cold Chain Logistics Park, GIDC Estate')
const defaultRateUnit = ref('MT')

const saveSettings = () => {
  toast.add({ severity: 'success', summary: 'Settings Saved', detail: 'Facility configuration updated successfully.', life: 3000 })
}
</script>

<template>
  <div class="page-container">
    <div class="settings-card">
      <h3 class="card-title">Facility Configuration</h3>
      <p class="card-desc">Manage multi-chamber parameters, GSTIN details, and default billing units.</p>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Facility Name</label>
          <InputText v-model="facilityName" class="w-full" />
        </div>

        <div class="form-group">
          <label class="form-label">GSTIN Number</label>
          <InputText v-model="gstin" class="w-full" />
        </div>

        <div class="form-group span-2">
          <label class="form-label">Facility Address</label>
          <InputText v-model="address" class="w-full" />
        </div>

        <div class="form-group">
          <label class="form-label">Default Rate Unit</label>
          <Select v-model="defaultRateUnit" :options="['MT', 'Bag', 'Box', 'Kg']" class="w-full" />
        </div>
      </div>

      <div class="actions-row">
        <button class="btn-primary" @click="saveSettings">
          <Save :size="16" />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { display: flex; flex-direction: column; gap: 16px; }
.settings-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; box-shadow: var(--shadow-card); display: flex; flex-direction: column; gap: 16px; max-width: 800px; }
.card-title { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.card-desc { font-size: 12.5px; color: var(--text-secondary); }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 8px; }
.span-2 { grid-column: span 2; }
@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .span-2 { grid-column: span 1; }
}
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.w-full { width: 100%; }
.actions-row { display: flex; justify-content: flex-end; margin-top: 12px; }
.btn-primary { display: inline-flex; align-items: center; gap: 8px; padding: 9px 18px; border-radius: 10px; background-color: var(--accent-primary); color: #ffffff; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }
</style>

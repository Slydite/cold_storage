<script setup lang="ts">
import { ref } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import { Plus, Edit2, RefreshCw, Box } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useFacility } from '../../composables/useFacility'
import {
  useChamberList,
  useCreateChamber,
  useUpdateChamber
} from '../../composables/useLocations'
import type { ChamberOutput } from '../../api/location'

const toast = useToast()
const { facilityId } = useFacility()

const {
  data: chambers,
  isLoading,
  isError,
  refetch
} = useChamberList({
  facilityId
})

const createChamberMutation = useCreateChamber()
const updateChamberMutation = useUpdateChamber()

const isDialogOpen = ref(false)
const editingChamber = ref<ChamberOutput | null>(null)

const chamberSchema = z.object({
  name: z.string().min(1, 'Chamber name is required'),
  sort_order: z.number(),
  is_active: z.boolean()
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(chamberSchema),
  initialValues: {
    name: '',
    sort_order: 0,
    is_active: true
  }
})

const [name, nameProps] = defineField('name')
const [sort_order] = defineField('sort_order')
const [is_active] = defineField('is_active')

const openCreateDialog = () => {
  editingChamber.value = null
  resetForm({
    values: {
      name: '',
      sort_order: (chambers.value?.length ?? 0) * 10,
      is_active: true
    }
  })
  isDialogOpen.value = true
}

const openEditDialog = (chamber: ChamberOutput) => {
  editingChamber.value = chamber
  resetForm({
    values: {
      name: chamber.name,
      sort_order: chamber.sort_order ?? 0,
      is_active: chamber.is_active ?? true
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  if (!facilityId.value) return

  try {
    if (editingChamber.value) {
      await updateChamberMutation.mutateAsync({
        id: editingChamber.value.id,
        body: {
          facility_id: facilityId.value,
          name: values.name,
          sort_order: values.sort_order,
          is_active: values.is_active
        }
      })
      toast.add({
        severity: 'success',
        summary: 'Chamber Updated',
        detail: `Chamber "${values.name}" updated successfully`,
        life: 3000
      })
    } else {
      await createChamberMutation.mutateAsync({
        facility_id: facilityId.value,
        name: values.name,
        sort_order: values.sort_order,
        is_active: values.is_active
      })
      toast.add({
        severity: 'success',
        summary: 'Chamber Created',
        detail: `Chamber "${values.name}" created successfully`,
        life: 3000
      })
    }
    isDialogOpen.value = false
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Operation failed'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <div class="chamber-manager-wrapper">
    <div class="list-toolbar">
      <div class="toolbar-left">
        <h3 class="toolbar-title">Chamber Management</h3>
        <p class="toolbar-desc">Configure top-level chambers in your storage facility.</p>
      </div>

      <div class="toolbar-right">
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>Add Chamber</span>
        </button>
      </div>
    </div>

    <div class="table-card">
      <div v-if="isLoading" class="p-4">
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" />
      </div>

      <div v-else-if="isError" class="error-state">
        <p>Failed to load chambers list.</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>Retry</span>
        </button>
      </div>

      <div v-else-if="!chambers || chambers.length === 0" class="empty-state">
        <Box :size="36" class="empty-icon" />
        <h3>No Chambers Found</h3>
        <p>Add your first chamber to start organizing facility locations.</p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>Add Chamber</span>
        </button>
      </div>

      <DataTable
        v-else
        :value="chambers"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="code" header="Code">
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" header="Chamber Name">
          <template #body="{ data }">
            <strong class="chamber-name">{{ data.name }}</strong>
          </template>
        </Column>

        <Column field="sort_order" header="Order" style="width: 90px">
          <template #body="{ data }">
            <span class="num-val">{{ data.sort_order ?? 0 }}</span>
          </template>
        </Column>

        <Column field="is_active" header="Status">
          <template #body="{ data }">
            <Tag
              :value="data.is_active !== false ? 'Active' : 'Inactive'"
              :severity="data.is_active !== false ? 'success' : 'secondary'"
            />
          </template>
        </Column>

        <Column header="Actions" alignFrozen="right" style="width: 100px">
          <template #body="{ data }">
            <button
              type="button"
              class="icon-btn"
              title="Edit Chamber"
              @click="openEditDialog(data)"
            >
              <Edit2 :size="16" />
            </button>
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="isDialogOpen"
      modal
      :header="editingChamber ? 'Edit Chamber' : 'Add New Chamber'"
      :style="{ width: '420px' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div class="form-group">
          <label for="chamber-name">Chamber Name <span class="required">*</span></label>
          <InputText
            id="chamber-name"
            v-model="name"
            v-bind="nameProps"
            placeholder="e.g. Chamber 1, Cold Room A"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="chamber-sort">Sort Order</label>
          <InputNumber
            id="chamber-sort"
            v-model="sort_order"
            :min="0"
            class="w-full"
          />
        </div>

        <div class="checkbox-group">
          <Checkbox id="chamber-active" v-model="is_active" :binary="true" />
          <label for="chamber-active" class="cursor-pointer">Active Status</label>
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="isDialogOpen = false"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="createChamberMutation.isPending.value || updateChamberMutation.isPending.value"
          >
            {{ editingChamber ? 'Update Chamber' : 'Save Chamber' }}
          </button>
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped>
.chamber-manager-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-left {
  flex: 1;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.toolbar-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.chamber-name {
  color: var(--text-primary);
  font-weight: 600;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.cursor-pointer {
  cursor: pointer;
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

.error-state,
.empty-state {
  padding: 36px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
}

.empty-icon {
  color: var(--text-secondary);
}

.p-4 {
  padding: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>

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
import { Plus, Edit2, RefreshCw, Layers } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useFacility } from '../../composables/useFacility'
import { useFloorList, useCreateFloor, useUpdateFloor } from '../../composables/useLocations'
import type { FloorOutput } from '../../api/location'

const toast = useToast()
const { facilityId } = useFacility()

const { data: floors, isLoading, isError, refetch } = useFloorList(facilityId)
const createFloorMutation = useCreateFloor()
const updateFloorMutation = useUpdateFloor()

const isDialogOpen = ref(false)
const editingFloor = ref<FloorOutput | null>(null)

const floorSchema = z.object({
  name: z.string().min(1, 'Floor name is required'),
  sort_order: z.number(),
  is_active: z.boolean()
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(floorSchema),
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
  editingFloor.value = null
  resetForm({
    values: {
      name: '',
      sort_order: (floors.value?.length ?? 0) * 10,
      is_active: true
    }
  })
  isDialogOpen.value = true
}

const openEditDialog = (floor: FloorOutput) => {
  editingFloor.value = floor
  resetForm({
    values: {
      name: floor.name,
      sort_order: floor.sort_order ?? 0,
      is_active: floor.is_active ?? true
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  if (!facilityId.value) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No working facility selected.',
      life: 4000
    })
    return
  }

  try {
    if (editingFloor.value) {
      await updateFloorMutation.mutateAsync({
        id: editingFloor.value.id,
        body: {
          name: values.name,
          sort_order: values.sort_order,
          is_active: values.is_active
        }
      })
      toast.add({
        severity: 'success',
        summary: 'Floor Updated',
        detail: `Floor "${values.name}" updated successfully`,
        life: 3000
      })
    } else {
      await createFloorMutation.mutateAsync({
        facility_id: facilityId.value,
        name: values.name,
        sort_order: values.sort_order,
        is_active: values.is_active
      })
      toast.add({
        severity: 'success',
        summary: 'Floor Created',
        detail: `Floor "${values.name}" created successfully`,
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
  <div class="floor-manager-wrapper">
    <div class="list-toolbar">
      <div>
        <h3 class="toolbar-title">Floor Management</h3>
        <p class="toolbar-desc">Configure building levels for storage organization.</p>
      </div>

      <button type="button" class="btn-primary" @click="openCreateDialog">
        <Plus :size="16" />
        <span>Add Floor</span>
      </button>
    </div>

    <div class="table-card">
      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="p-4">
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" class="mb-2" />
        <Skeleton height="40px" />
      </div>

      <!-- Error State -->
      <div v-else-if="isError" class="error-state">
        <p>Failed to load floors list.</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>Retry</span>
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="!floors || floors.length === 0" class="empty-state">
        <Layers :size="36" class="empty-icon" />
        <h3>No Floors Configured</h3>
        <p>Add floors (e.g. Ground Floor, Floor 1, Floor 2) to manage chambers.</p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>Add First Floor</span>
        </button>
      </div>

      <!-- Table -->
      <DataTable
        v-else
        :value="floors"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="sort_order" header="Order" style="width: 90px">
          <template #body="{ data }">
            <span class="num-val">{{ data.sort_order ?? 0 }}</span>
          </template>
        </Column>

        <Column field="name" header="Floor Name">
          <template #body="{ data }">
            <strong class="floor-name">{{ data.name }}</strong>
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
              title="Edit Floor"
              @click="openEditDialog(data)"
            >
              <Edit2 :size="16" />
            </button>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="isDialogOpen"
      modal
      :header="editingFloor ? 'Edit Floor' : 'Add New Floor'"
      :style="{ width: '420px' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div class="form-group">
          <label for="floor-name">Floor Name <span class="required">*</span></label>
          <InputText
            id="floor-name"
            v-model="name"
            v-bind="nameProps"
            placeholder="e.g. Ground Floor, Floor 1"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="floor-sort">Sort Order</label>
          <InputNumber
            id="floor-sort"
            v-model="sort_order"
            :min="0"
            class="w-full"
          />
        </div>

        <div class="checkbox-group">
          <Checkbox id="floor-active" v-model="is_active" :binary="true" />
          <label for="floor-active" class="cursor-pointer">Active Status</label>
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
            :disabled="createFloorMutation.isPending.value || updateFloorMutation.isPending.value"
          >
            {{ editingFloor ? 'Update Floor' : 'Save Floor' }}
          </button>
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped>
.floor-manager-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.floor-name {
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

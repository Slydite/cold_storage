<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import { Plus, Edit2, RefreshCw, Grid } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useFacility } from '../../composables/useFacility'
import {
  useChamberList,
  useFloorList,
  useBlockList,
  useCreateBlock,
  useUpdateBlock
} from '../../composables/useLocations'
import type { BlockOutput } from '../../api/location'

const toast = useToast()
const { facilityId } = useFacility()

const selectedChamberFilter = ref<number | undefined>(undefined)
const selectedFloorFilter = ref<number | undefined>(undefined)

const chamberFilterRef = computed(() => selectedChamberFilter.value)
const floorFilterRef = computed(() => selectedFloorFilter.value)

const { data: chambers } = useChamberList({ facilityId })
const { data: filterFloors } = useFloorList({
  facilityId,
  chamberId: chamberFilterRef
})
const {
  data: blocks,
  isLoading,
  isError,
  refetch
} = useBlockList({
  facilityId,
  chamberId: chamberFilterRef,
  floorId: floorFilterRef
})

const createBlockMutation = useCreateBlock()
const updateBlockMutation = useUpdateBlock()

const isDialogOpen = ref(false)
const editingBlock = ref<BlockOutput | null>(null)

const chamberOptions = computed(() => {
  if (!chambers.value) return []
  return chambers.value.map((c) => ({ label: c.name, value: c.id }))
})

const filterFloorOptions = computed(() => {
  if (!filterFloors.value) return []
  return filterFloors.value.map((f) => ({ label: f.name, value: f.id }))
})

// Dialog cascading state
const formChamberId = ref<number | null>(null)
const formChamberIdRef = computed(() => formChamberId.value ?? undefined)
const { data: dialogFloors } = useFloorList({
  facilityId,
  chamberId: formChamberIdRef
})

const dialogFloorOptions = computed(() => {
  if (!dialogFloors.value) return []
  return dialogFloors.value.map((f) => ({ label: f.name, value: f.id }))
})

const blockSchema = z.object({
  floor_id: z
    .number()
    .nullable()
    .refine((v): v is number => v != null && v > 0, { message: 'Floor selection is required' }),
  name: z.string().min(1, 'Block name is required'),
  capacity_bags: z.number().nullable().optional(),
  sort_order: z.number(),
  is_active: z.boolean()
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(blockSchema),
  initialValues: {
    floor_id: null as number | null,
    name: '',
    capacity_bags: null as number | null,
    sort_order: 0,
    is_active: true
  }
})

const [floor_id, floorIdProps] = defineField('floor_id')
const [name, nameProps] = defineField('name')
const [capacity_bags] = defineField('capacity_bags')
const [sort_order] = defineField('sort_order')
const [is_active] = defineField('is_active')

watch(formChamberId, () => {
  // Clear floor_id if it's not valid under new chamber
  if (floor_id.value && !dialogFloorOptions.value.some((f) => f.value === floor_id.value)) {
    floor_id.value = null
  }
})

const openCreateDialog = () => {
  editingBlock.value = null
  const defaultChamber = selectedChamberFilter.value || chamberOptions.value[0]?.value || null
  formChamberId.value = defaultChamber
  resetForm({
    values: {
      floor_id: selectedFloorFilter.value || null,
      name: '',
      capacity_bags: null,
      sort_order: (blocks.value?.length ?? 0) * 10,
      is_active: true
    }
  })
  isDialogOpen.value = true
}

const openEditDialog = (block: BlockOutput) => {
  editingBlock.value = block
  formChamberId.value = block.chamber_id
  resetForm({
    values: {
      floor_id: block.floor_id,
      name: block.name,
      capacity_bags: block.capacity_bags ?? null,
      sort_order: block.sort_order ?? 0,
      is_active: block.is_active ?? true
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  if (!facilityId.value) return

  try {
    if (editingBlock.value) {
      await updateBlockMutation.mutateAsync({
        id: editingBlock.value.id,
        body: {
          floor_id: values.floor_id!,
          name: values.name,
          capacity_bags: values.capacity_bags ?? undefined,
          sort_order: values.sort_order,
          is_active: values.is_active
        }
      })
      toast.add({
        severity: 'success',
        summary: 'Block Updated',
        detail: `Block "${values.name}" updated successfully`,
        life: 3000
      })
    } else {
      await createBlockMutation.mutateAsync({
        facility_id: facilityId.value,
        chamber_id: formChamberId.value || undefined,
        floor_id: values.floor_id!,
        name: values.name,
        capacity_bags: values.capacity_bags ?? undefined,
        sort_order: values.sort_order,
        is_active: values.is_active
      })
      toast.add({
        severity: 'success',
        summary: 'Block Created',
        detail: `Block "${values.name}" created successfully`,
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
  <div class="block-manager-wrapper">
    <div class="list-toolbar">
      <div class="toolbar-left">
        <h3 class="toolbar-title">Block Management</h3>
        <p class="toolbar-desc">Configure storage blocks belonging to floor and chamber levels.</p>
      </div>

      <div class="toolbar-right">
        <Select
          v-model="selectedChamberFilter"
          :options="[{ label: 'All Chambers', value: undefined }, ...chamberOptions]"
          optionLabel="label"
          optionValue="value"
          placeholder="Filter by Chamber"
          class="filter-select"
        />

        <Select
          v-model="selectedFloorFilter"
          :options="[{ label: 'All Floors', value: undefined }, ...filterFloorOptions]"
          optionLabel="label"
          optionValue="value"
          placeholder="Filter by Floor"
          class="filter-select"
        />

        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>Add Block</span>
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
        <p>Failed to load blocks list.</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>Retry</span>
        </button>
      </div>

      <div v-else-if="!blocks || blocks.length === 0" class="empty-state">
        <Grid :size="36" class="empty-icon" />
        <h3>No Blocks Found</h3>
        <p>
          {{ selectedChamberFilter || selectedFloorFilter ? 'No blocks found for the selected filters.' : 'Add your first block to start organizing lot storage locations.' }}
        </p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>Add Block</span>
        </button>
      </div>

      <DataTable
        v-else
        :value="blocks"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="code" header="Code">
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" header="Block Name">
          <template #body="{ data }">
            <strong class="block-name">{{ data.name }}</strong>
          </template>
        </Column>

        <Column field="chamber_name" header="Chamber">
          <template #body="{ data }">
            <span class="badge-subtle">{{ data.chamber_name || 'Chamber ' + data.chamber_id }}</span>
          </template>
        </Column>

        <Column field="floor_name" header="Floor">
          <template #body="{ data }">
            <span class="badge-subtle">{{ data.floor_name || 'Floor ' + data.floor_id }}</span>
          </template>
        </Column>

        <Column field="capacity_bags" header="Capacity (Bags)">
          <template #body="{ data }">
            <span class="num-val">{{ data.capacity_bags ? data.capacity_bags.toLocaleString() : 'Unspecified' }}</span>
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
              title="Edit Block"
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
      :header="editingBlock ? 'Edit Block' : 'Add New Block'"
      :style="{ width: '450px' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div class="form-group">
          <label for="block-chamber">Belongs to Chamber</label>
          <Select
            id="block-chamber"
            v-model="formChamberId"
            :options="chamberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Select Chamber"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="block-floor">Belongs to Floor <span class="required">*</span></label>
          <Select
            id="block-floor"
            v-model="floor_id"
            v-bind="floorIdProps"
            :options="dialogFloorOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Select Floor"
            class="w-full"
            :class="{ 'p-invalid': errors.floor_id }"
          />
          <span v-if="errors.floor_id" class="field-error">{{ errors.floor_id }}</span>
        </div>

        <div class="form-group">
          <label for="block-name">Block Name <span class="required">*</span></label>
          <InputText
            id="block-name"
            v-model="name"
            v-bind="nameProps"
            placeholder="e.g. Block A, Bay 1"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="block-capacity">Capacity (Bags)</label>
          <InputNumber
            id="block-capacity"
            v-model="capacity_bags"
            :min="0"
            placeholder="e.g. 2000"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="block-sort">Sort Order</label>
          <InputNumber
            id="block-sort"
            v-model="sort_order"
            :min="0"
            class="w-full"
          />
        </div>

        <div class="checkbox-group">
          <Checkbox id="block-active" v-model="is_active" :binary="true" />
          <label for="block-active" class="cursor-pointer">Active Status</label>
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
            :disabled="createBlockMutation.isPending.value || updateBlockMutation.isPending.value"
          >
            {{ editingBlock ? 'Update Block' : 'Save Block' }}
          </button>
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped>
.block-manager-wrapper {
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

.filter-select {
  min-width: 150px;
}

.block-name {
  color: var(--text-primary);
  font-weight: 600;
}

.badge-subtle {
  font-size: 13px;
  color: var(--text-secondary);
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

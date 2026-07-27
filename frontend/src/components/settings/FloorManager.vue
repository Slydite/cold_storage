<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import { Plus, Edit2, RefreshCw, Layers } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useFacility } from '../../composables/useFacility'
import {
  useChamberList,
  useFloorList,
  useCreateFloor,
  useUpdateFloor
} from '../../composables/useLocations'
import type { FloorOutput } from '../../api/location'

const toast = useToast()
const { t } = useI18n()
const { facilityId } = useFacility()

const selectedChamberFilter = ref<number | undefined>(undefined)
const chamberFilterRef = computed(() => selectedChamberFilter.value)

const { data: chambers } = useChamberList({ facilityId })
const {
  data: floors,
  isLoading,
  isError,
  refetch
} = useFloorList({
  facilityId,
  chamberId: chamberFilterRef
})

const createFloorMutation = useCreateFloor()
const updateFloorMutation = useUpdateFloor()

const isDialogOpen = ref(false)
const editingFloor = ref<FloorOutput | null>(null)

const chamberOptions = computed(() => {
  if (!chambers.value) return []
  return chambers.value.map((c) => ({ label: c.name, value: c.id }))
})

const floorSchema = computed(() =>
  z.object({
    chamber_id: z
      .number()
      .nullable()
      .refine((v): v is number => v != null && v > 0, { message: t('validation.chamberSelectionRequired') }),
    name: z.string().min(1, t('validation.floorNameRequired')),
    sort_order: z.number(),
    is_active: z.boolean()
  })
)

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(floorSchema.value)),
  initialValues: {
    chamber_id: null as number | null,
    name: '',
    sort_order: 0,
    is_active: true
  }
})

const [chamber_id, chamberIdProps] = defineField('chamber_id')
const [name, nameProps] = defineField('name')
const [sort_order] = defineField('sort_order')
const [is_active] = defineField('is_active')

const openCreateDialog = () => {
  editingFloor.value = null
  const defaultChamberId = selectedChamberFilter.value || chamberOptions.value[0]?.value || null
  resetForm({
    values: {
      chamber_id: defaultChamberId,
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
      chamber_id: floor.chamber_id,
      name: floor.name,
      sort_order: floor.sort_order ?? 0,
      is_active: floor.is_active ?? true
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  if (!facilityId.value) return

  try {
    if (editingFloor.value) {
      await updateFloorMutation.mutateAsync({
        id: editingFloor.value.id,
        body: {
          chamber_id: values.chamber_id!,
          name: values.name,
          sort_order: values.sort_order,
          is_active: values.is_active
        }
      })
      toast.add({
        severity: 'success',
        summary: t('settings.floorUpdatedSummary'),
        detail: t('settings.floorUpdatedDetail', { name: values.name }),
        life: 3000
      })
    } else {
      await createFloorMutation.mutateAsync({
        facility_id: facilityId.value,
        chamber_id: values.chamber_id!,
        name: values.name,
        sort_order: values.sort_order,
        is_active: values.is_active
      })
      toast.add({
        severity: 'success',
        summary: t('settings.floorCreatedSummary'),
        detail: t('settings.floorCreatedDetail', { name: values.name }),
        life: 3000
      })
    }
    isDialogOpen.value = false
  } catch (err) {
    const msg = err instanceof Error ? err.message : t('common.actionFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <div class="floor-manager-wrapper">
    <div class="list-toolbar">
      <div class="toolbar-left">
        <h3 class="toolbar-title">{{ t('settings.floorManagement') }}</h3>
        <p class="toolbar-desc">{{ t('settings.floorManagementDesc') }}</p>
      </div>

      <div class="toolbar-right">
        <Select
          v-model="selectedChamberFilter"
          :options="[{ label: t('common.allChambers'), value: undefined }, ...chamberOptions]"
          optionLabel="label"
          optionValue="value"
          :placeholder="t('grn.chamber')"
          class="chamber-filter-select"
        />

        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>{{ t('settings.addFloor') }}</span>
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
        <p>{{ t('grn.failedToLoad') }}</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>{{ t('common.retry') }}</span>
        </button>
      </div>

      <div v-else-if="!floors || floors.length === 0" class="empty-state">
        <Layers :size="36" class="empty-icon" />
        <h3>{{ t('settings.noFloorsConfigured') }}</h3>
        <p>{{ selectedChamberFilter ? t('common.noRecordsFound') : t('settings.noFloorsDesc') }}</p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>{{ t('settings.addFloor') }}</span>
        </button>
      </div>

      <DataTable
        v-else
        :value="floors"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="code" :header="t('common.code')">
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" :header="t('locations.floor') + ' ' + t('common.name')">
          <template #body="{ data }">
            <strong class="floor-name">{{ data.name }}</strong>
          </template>
        </Column>

        <Column field="chamber_name" :header="t('locations.chamber')">
          <template #body="{ data }">
            <span class="badge-subtle">{{ data.chamber_name || t('locations.chamber') + ' ' + data.chamber_id }}</span>
          </template>
        </Column>

        <Column field="sort_order" header="Order" style="width: 90px">
          <template #body="{ data }">
            <span class="num-val">{{ data.sort_order ?? 0 }}</span>
          </template>
        </Column>

        <Column field="is_active" :header="t('common.status')">
          <template #body="{ data }">
            <Tag
              :value="data.is_active !== false ? t('status.active') : t('status.inactive')"
              :severity="data.is_active !== false ? 'success' : 'secondary'"
            />
          </template>
        </Column>

        <Column :header="t('common.actions')" alignFrozen="right" style="width: 100px">
          <template #body="{ data }">
            <button
              type="button"
              class="icon-btn"
              :title="t('settings.editFloor')"
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
      :header="editingFloor ? t('settings.editFloor') : t('settings.addFloor')"
      :style="{ width: '450px', maxWidth: '95vw' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div class="form-group">
          <label for="floor-chamber" class="form-label">{{ t('settings.belongsToChamber') }} <span class="req">*</span></label>
          <Select
            id="floor-chamber"
            v-model="chamber_id"
            v-bind="chamberIdProps"
            :options="chamberOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('grn.chamber')"
            class="w-full"
            :class="{ 'p-invalid': errors.chamber_id }"
          />
          <span v-if="errors.chamber_id" class="field-error">{{ errors.chamber_id }}</span>
        </div>

        <div class="form-group">
          <label for="floor-name" class="form-label">{{ t('locations.floor') }} {{ t('common.name') }} <span class="req">*</span></label>
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
          <label for="floor-sort" class="form-label">Sort Order</label>
          <InputNumber
            id="floor-sort"
            v-model="sort_order"
            :min="0"
            class="w-full"
          />
        </div>

        <div class="checkbox-group">
          <Checkbox id="floor-active" v-model="is_active" :binary="true" />
          <label for="floor-active" class="cursor-pointer">{{ t('settings.activeStatus') }}</label>
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="isDialogOpen = false"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="createFloorMutation.isPending.value || updateFloorMutation.isPending.value"
          >
            {{ editingFloor ? t('common.save') : t('common.add') }}
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

.chamber-filter-select {
  min-width: 170px;
}

.floor-name {
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

.form-label {
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

.req {
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

<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Textarea from 'primevue/textarea'
import { Plus, Edit2, RefreshCw, Package } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import { useFacility } from '../../composables/useFacility'
import {
  useCommodityList,
  useCreateCommodity,
  useUpdateCommodity
} from '../../composables/useCommodities'
import type { CommodityOutput } from '../../api/commodity'

const toast = useToast()
const { t } = useI18n()
const { facilityId } = useFacility()

const { data: commodities, isLoading, isError, refetch } = useCommodityList(facilityId)

const createCommodityMutation = useCreateCommodity()
const updateCommodityMutation = useUpdateCommodity()

const isDialogOpen = ref(false)
const editingCommodity = ref<CommodityOutput | null>(null)

const unitOptions = computed(() => [
  { label: `${t('units.bags')} (Bags)`, value: 'Bags' },
  { label: `${t('units.boxes')} (Boxes)`, value: 'Boxes' },
  { label: `${t('units.mt')} (MT)`, value: 'MT' },
  { label: `${t('units.kg')} (Kg)`, value: 'Kg' },
  { label: `${t('units.crates')} (Crates)`, value: 'Crates' }
])

const commoditySchema = computed(() =>
  z.object({
    name: z.string().min(1, t('validation.commodityNameRequired')),
    unit: z.string(),
    description: z.string().optional(),
    is_active: z.boolean()
  })
)

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(commoditySchema.value)),
  initialValues: {
    name: '',
    unit: 'Bags',
    description: '',
    is_active: true
  }
})

const [name, nameProps] = defineField('name')
const [unit] = defineField('unit')
const [description, descriptionProps] = defineField('description')
const [is_active] = defineField('is_active')

const openCreateDialog = () => {
  editingCommodity.value = null
  resetForm({
    values: {
      name: '',
      unit: 'Bags',
      description: '',
      is_active: true
    }
  })
  isDialogOpen.value = true
}

const openEditDialog = (item: CommodityOutput) => {
  editingCommodity.value = item
  resetForm({
    values: {
      name: item.name,
      unit: item.unit ?? 'Bags',
      description: item.description ?? '',
      is_active: item.is_active ?? true
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  if (!facilityId.value) return

  try {
    if (editingCommodity.value) {
      await updateCommodityMutation.mutateAsync({
        id: editingCommodity.value.id,
        body: {
          facility_id: facilityId.value,
          name: values.name,
          unit: values.unit,
          description: values.description || undefined,
          is_active: values.is_active
        }
      })
      toast.add({
        severity: 'success',
        summary: t('settings.commodityUpdatedSummary'),
        detail: t('settings.commodityUpdatedDetail', { name: values.name }),
        life: 3000
      })
    } else {
      await createCommodityMutation.mutateAsync({
        facility_id: facilityId.value,
        name: values.name,
        unit: values.unit,
        description: values.description || undefined,
        is_active: values.is_active
      })
      toast.add({
        severity: 'success',
        summary: t('settings.commodityCreatedSummary'),
        detail: t('settings.commodityCreatedDetail', { name: values.name }),
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
  <div class="commodity-manager-wrapper">
    <div class="list-toolbar">
      <div>
        <h3 class="toolbar-title">{{ t('settings.commoditiesMaster') }}</h3>
        <p class="toolbar-desc">{{ t('settings.commoditiesMasterDesc') }}</p>
      </div>

      <button type="button" class="btn-primary" @click="openCreateDialog">
        <Plus :size="16" />
        <span>{{ t('settings.addCommodity') }}</span>
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
        <p>{{ t('grn.failedToLoad') }}</p>
        <button type="button" class="btn-outlined" @click="refetch()">
          <RefreshCw :size="14" />
          <span>{{ t('common.retry') }}</span>
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="!commodities || commodities.length === 0" class="empty-state">
        <Package :size="36" class="empty-icon" />
        <h3>{{ t('settings.noCommoditiesFound') }}</h3>
        <p>{{ t('settings.noCommoditiesDesc') }}</p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>{{ t('settings.addCommodity') }}</span>
        </button>
      </div>

      <!-- Table -->
      <DataTable
        v-else
        :value="commodities"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="code" :header="t('common.code')">
          <template #body="{ data }">
            <span class="code-link">{{ data.code }}</span>
          </template>
        </Column>

        <Column field="name" :header="t('grn.commodityProduct') + ' ' + t('common.name')">
          <template #body="{ data }">
            <strong class="item-name">{{ data.name }}</strong>
          </template>
        </Column>

        <Column field="unit" :header="t('common.unit')">
          <template #body="{ data }">
            {{ data.unit ? t(`units.${data.unit}`, data.unit) : t('units.bags') }}
          </template>
        </Column>

        <Column field="description" :header="t('common.description')">
          <template #body="{ data }">
            {{ data.description || '-' }}
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
              :title="t('settings.editCommodity')"
              @click="openEditDialog(data)"
            >
              <Edit2 :size="16" />
            </button>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog -->
    <Dialog
      v-model:visible="isDialogOpen"
      modal
      :header="editingCommodity ? t('settings.editCommodity') : t('settings.addCommodity')"
      :style="{ width: '450px', maxWidth: '95vw' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div class="form-group">
          <label for="comm-name" class="form-label">{{ t('grn.commodityProduct') }} {{ t('common.name') }} <span class="req">*</span></label>
          <InputText
            id="comm-name"
            v-model="name"
            v-bind="nameProps"
            placeholder="e.g. Fresh Potatoes"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>

        <div class="form-group">
          <label for="comm-unit" class="form-label">{{ t('settings.packagingUnit') }}</label>
          <Select
            id="comm-unit"
            v-model="unit"
            :options="unitOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="comm-desc" class="form-label">{{ t('common.description') }}</label>
          <Textarea
            id="comm-desc"
            v-model="description"
            v-bind="descriptionProps"
            rows="2"
            placeholder="Variety notes or handling instructions..."
            class="w-full"
          />
        </div>

        <div class="checkbox-group">
          <Checkbox id="comm-active" v-model="is_active" :binary="true" />
          <label for="comm-active" class="cursor-pointer">{{ t('settings.activeStatus') }}</label>
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
            :disabled="createCommodityMutation.isPending.value || updateCommodityMutation.isPending.value"
          >
            {{ editingCommodity ? t('common.save') : t('common.add') }}
          </button>
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped>
.commodity-manager-wrapper {
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

.item-name {
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

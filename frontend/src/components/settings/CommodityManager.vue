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
import { Plus, Edit2, RefreshCw, Package, GitMerge } from 'lucide-vue-next'
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
import {
  addCommodityAlias,
  deleteCommodityAlias,
  mergeCommodities
} from '../../api/commodity'

const toast = useToast()
const { t } = useI18n()
const { facilityId } = useFacility()

const { data: commodities, isLoading, isError, refetch } = useCommodityList(facilityId)

const createCommodityMutation = useCreateCommodity()
const updateCommodityMutation = useUpdateCommodity()

const isDialogOpen = ref(false)

import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
useHistoryDismiss(isDialogOpen, () => {
  isDialogOpen.value = false
})
const editingCommodity = ref<CommodityOutput | null>(null)

const showAliasDialog = ref(false)
const showMergeDialog = ref(false)
const selectedCommodity = ref<CommodityOutput | null>(null)
const isSubmittingAlias = ref(false)
const isSubmittingMerge = ref(false)

const aliasSchema = computed(() =>
  z.object({
    alias_name: z.string().min(1, t('validation.required'))
  })
)

const mergeSchema = computed(() =>
  z.object({
    source_commodity_id: z.number({ message: t('validation.required') })
  })
)

const { handleSubmit: handleAliasSubmit, errors: aliasErrors, defineField: defineAliasField, resetForm: resetAliasForm } = useForm({
  validationSchema: computed(() => toTypedSchema(aliasSchema.value)),
  initialValues: { alias_name: '' }
})

const { handleSubmit: handleMergeSubmit, errors: mergeErrors, defineField: defineMergeField, resetForm: resetMergeForm } = useForm({
  validationSchema: computed(() => toTypedSchema(mergeSchema.value)),
  initialValues: { source_commodity_id: undefined as number | undefined }
})

const [alias_name, aliasNameProps] = defineAliasField('alias_name')
const [source_commodity_id, sourceCommodityIdProps] = defineMergeField('source_commodity_id')

const openAddAlias = (item: CommodityOutput) => {
  selectedCommodity.value = item
  resetAliasForm({ values: { alias_name: '' } })
  showAliasDialog.value = true
}

const openMergeDialog = (item: CommodityOutput) => {
  selectedCommodity.value = item
  resetMergeForm({ values: { source_commodity_id: undefined as number | undefined } })
  showMergeDialog.value = true
}

const onAddAliasSubmit = handleAliasSubmit(async (values) => {
  if (!selectedCommodity.value) return
  isSubmittingAlias.value = true
  try {
    await addCommodityAlias(selectedCommodity.value.id, { name: values.alias_name })
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('settings.aliasSuccess'),
      life: 3000
    })
    showAliasDialog.value = false
    refetch()
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('settings.aliasFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 5000
    })
  } finally {
    isSubmittingAlias.value = false
  }
})

const onRemoveAlias = async (commodityId: number, aliasId: number) => {
  try {
    await deleteCommodityAlias(commodityId, aliasId)
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('settings.aliasDeleteSuccess'),
      life: 3000
    })
    refetch()
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('settings.aliasDeleteFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 5000
    })
  }
}

const onMergeSubmit = handleMergeSubmit(async (values) => {
  if (!selectedCommodity.value) return
  const sourceId = values.source_commodity_id
  if (sourceId === selectedCommodity.value.id) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('errors.generic'),
      life: 5000
    })
    return
  }

  isSubmittingMerge.value = true
  try {
    await mergeCommodities(selectedCommodity.value.id, { source_commodity_id: sourceId })
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('settings.mergeSuccess'),
      life: 5000
    })
    showMergeDialog.value = false
    refetch()
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: t('settings.mergeFailed'),
      detail: err instanceof Error ? err.message : t('errors.generic'),
      life: 7000
    })
  } finally {
    isSubmittingMerge.value = false
  }
})

const otherCommoditiesOptions = computed(() => {
  if (!commodities.value) return []
  return commodities.value
    .filter((c) => c.id !== selectedCommodity.value?.id)
    .map((c) => ({ label: `${c.name} (${c.code})`, value: c.id }))
})

const sourceCommodityName = computed(() => {
  if (!source_commodity_id.value || !commodities.value) return ''
  const source = commodities.value.find((c) => c.id === source_commodity_id.value)
  return source ? source.name : ''
})

const destCommodityName = computed(() => {
  return selectedCommodity.value ? selectedCommodity.value.name : ''
})

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

        <Column :header="t('settings.aliases')">
          <template #body="{ data }">
            <div class="alias-chips-container">
              <span v-for="alias in data.aliases" :key="alias.id" class="alias-chip">
                <span>{{ alias.name }}</span>
                <button
                  type="button"
                  class="alias-remove-btn"
                  @click="onRemoveAlias(data.id, alias.id)"
                  :title="t('settings.aliasDeleteSuccess')"
                >
                  ×
                </button>
              </span>
              <button
                type="button"
                class="add-alias-chip-btn"
                @click="openAddAlias(data)"
              >
                + {{ t('settings.addAlias') }}
              </button>
            </div>
          </template>
        </Column>

        <Column :header="t('common.actions')" alignFrozen="right" style="width: 120px">
          <template #body="{ data }">
            <div class="flex gap-2">
              <button
                type="button"
                class="icon-btn"
                :title="t('settings.editCommodity')"
                @click="openEditDialog(data)"
              >
                <Edit2 :size="16" />
              </button>
              <button
                type="button"
                class="icon-btn merge-btn"
                :title="t('settings.mergeCommodity')"
                @click="openMergeDialog(data)"
              >
                <GitMerge :size="16" />
              </button>
            </div>
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

    <!-- Add Alias Dialog -->
    <Dialog
      v-model:visible="showAliasDialog"
      modal
      :header="t('settings.addAlias')"
      :style="{ width: '400px', maxWidth: '90vw' }"
    >
      <form @submit.prevent="onAddAliasSubmit" class="dialog-form">
        <div class="form-group">
          <label for="alias-name-input" class="form-label">{{ t('settings.aliases') }} <span class="req">*</span></label>
          <InputText
            id="alias-name-input"
            v-model="alias_name"
            v-bind="aliasNameProps"
            placeholder="e.g. Desi Aloo"
            class="w-full"
            :invalid="!!aliasErrors.alias_name"
          />
          <span v-if="aliasErrors.alias_name" class="field-error">{{ aliasErrors.alias_name }}</span>
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="showAliasDialog = false"
            :disabled="isSubmittingAlias"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSubmittingAlias"
          >
            <i v-if="isSubmittingAlias" class="pi pi-spin pi-spinner mr-1"></i>
            <span>{{ t('common.add') }}</span>
          </button>
        </div>
      </form>
    </Dialog>

    <!-- Merge Dialog -->
    <Dialog
      v-model:visible="showMergeDialog"
      modal
      :header="t('settings.mergeCommodity')"
      :style="{ width: '450px', maxWidth: '95vw' }"
    >
      <form @submit.prevent="onMergeSubmit" class="dialog-form">
        <p class="form-help-text">
          Fold another commodity into <strong>{{ destCommodityName }}</strong>.
        </p>

        <!-- Source Commodity Select -->
        <div class="form-group">
          <label for="source-select" class="form-label">{{ t('settings.mergeSource') }} <span class="req">*</span></label>
          <Select
            id="source-select"
            v-model="source_commodity_id"
            v-bind="sourceCommodityIdProps"
            :options="otherCommoditiesOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
            filter
            :placeholder="t('settings.mergeSource')"
            :invalid="!!mergeErrors.source_commodity_id"
          />
          <span v-if="mergeErrors.source_commodity_id" class="field-error">{{ mergeErrors.source_commodity_id }}</span>
        </div>

        <!-- Dynamic Warning Message -->
        <div v-if="source_commodity_id" class="merge-warning-box">
          {{ t('settings.confirmMergeMessage', { source: sourceCommodityName, dest: destCommodityName }) }}
        </div>

        <div class="dialog-actions">
          <button
            type="button"
            class="btn-outlined"
            @click="showMergeDialog = false"
            :disabled="isSubmittingMerge"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSubmittingMerge"
          >
            <i v-if="isSubmittingMerge" class="pi pi-spin pi-spinner mr-1"></i>
            <span>{{ t('settings.mergeCommodity') }}</span>
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

.alias-chips-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.alias-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-surface-active);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
}

.alias-remove-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.alias-remove-btn:hover {
  color: var(--status-danger-color);
}

.add-alias-chip-btn {
  background: none;
  border: 1px dashed var(--border-strong);
  color: var(--accent-primary);
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-alias-chip-btn:hover {
  background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.05);
  border-color: var(--accent-primary);
}

.merge-btn {
  color: var(--accent-primary);
}

.merge-btn:hover {
  background: rgba(var(--accent-primary-rgb, 99, 102, 241), 0.08);
}

.merge-warning-box {
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: var(--text-primary);
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  margin-top: 8px;
}

.form-help-text {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: 4px;
}

.mr-1 {
  margin-right: 4px;
}
</style>

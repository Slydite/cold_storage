<script setup lang="ts">
import { ref, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Select from 'primevue/select'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { Plus, Edit2, UserCheck, UserX, RefreshCw, Users } from 'lucide-vue-next'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useI18n } from 'vue-i18n'
import {
  useUserList,
  useCreateUser,
  useUpdateUser,
  useDeactivateUser,
  useActivateUser
} from '../../composables/useUsers'
import type { UserListOutput } from '../../api/user'

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()

const { data: users, isLoading, isError, refetch } = useUserList()
const createUserMutation = useCreateUser()
const updateUserMutation = useUpdateUser()
const deactivateUserMutation = useDeactivateUser()
const activateUserMutation = useActivateUser()

const isDialogOpen = ref(false)

import { useHistoryDismiss } from '../../composables/useHistoryDismiss'
useHistoryDismiss(isDialogOpen, () => {
  isDialogOpen.value = false
})
const editingUser = ref<UserListOutput | null>(null)

const roleOptions = computed(() => [
  { label: t('settings.administrator'), value: 'ADMIN' }
])

const formSchema = computed(() => {
  const isEdit = editingUser.value !== null
  return z.object({
    username: isEdit
      ? z.string().optional()
      : z.string().min(1, t('validation.usernameRequired')),
    password: isEdit
      ? z.string().optional()
      : z.string().min(6, t('validation.passwordMin6')),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    email: z.string().email(t('validation.invalidEmail')).or(z.literal('')).optional(),
    role: z.string()
  })
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: computed(() => toTypedSchema(formSchema.value)),
  initialValues: {
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: '',
    role: 'ADMIN'
  }
})

const [username, usernameProps] = defineField('username')
const [password, passwordProps] = defineField('password')
const [first_name, firstNameProps] = defineField('first_name')
const [last_name, lastNameProps] = defineField('last_name')
const [email, emailProps] = defineField('email')
const [role] = defineField('role')

const openCreateDialog = () => {
  editingUser.value = null
  resetForm({
    values: {
      username: '',
      password: '',
      first_name: '',
      last_name: '',
      email: '',
      role: 'ADMIN'
    }
  })
  isDialogOpen.value = true
}

const openEditDialog = (u: UserListOutput) => {
  editingUser.value = u
  resetForm({
    values: {
      username: u.username,
      password: '',
      first_name: u.first_name ?? '',
      last_name: u.last_name ?? '',
      email: typeof u.email === 'string' ? u.email : '',
      role: u.role || 'ADMIN'
    }
  })
  isDialogOpen.value = true
}

const onSubmit = handleSubmit(async (values) => {
  try {
    if (editingUser.value) {
      await updateUserMutation.mutateAsync({
        id: editingUser.value.id,
        body: {
          first_name: values.first_name || undefined,
          last_name: values.last_name || undefined,
          email: values.email || undefined,
          role: (values.role as 'ADMIN') || 'ADMIN',
          password: values.password ? values.password : undefined
        }
      })
      toast.add({
        severity: 'success',
        summary: t('settings.userUpdatedSummary'),
        detail: t('settings.userUpdatedDetail', { name: editingUser.value.username }),
        life: 3000
      })
    } else {
      await createUserMutation.mutateAsync({
        username: values.username!,
        password: values.password!,
        first_name: values.first_name || undefined,
        last_name: values.last_name || undefined,
        email: values.email || undefined,
        role: (values.role as 'ADMIN') || 'ADMIN',
        is_active: true
      })
      toast.add({
        severity: 'success',
        summary: t('settings.userCreatedSummary'),
        detail: t('settings.userCreatedDetail', { name: values.username }),
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

const confirmDeactivate = (u: UserListOutput) => {
  confirm.require({
    message: t('settings.deactivateAccountMsg', { name: u.username }),
    header: t('settings.deactivateAccountHeader'),
    icon: 'pi pi-exclamation-triangle',
    rejectClass: 'p-button-secondary p-button-outlined',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await deactivateUserMutation.mutateAsync(u.id)
        toast.add({
          severity: 'success',
          summary: t('settings.userDeactivatedSummary'),
          detail: t('settings.userDeactivatedDetail', { name: u.username }),
          life: 3000
        })
      } catch (err) {
        const msg = err instanceof Error ? err.message : t('common.actionFailed')
        toast.add({
          severity: 'error',
          summary: t('common.actionFailed'),
          detail: msg,
          life: 5000
        })
      }
    }
  })
}

const confirmActivate = (u: UserListOutput) => {
  confirm.require({
    message: t('settings.activateAccountMsg', { name: u.username }),
    header: t('settings.activateAccountHeader'),
    icon: 'pi pi-info-circle',
    accept: async () => {
      try {
        await activateUserMutation.mutateAsync(u.id)
        toast.add({
          severity: 'success',
          summary: t('settings.userActivatedSummary'),
          detail: t('settings.userActivatedDetail', { name: u.username }),
          life: 3000
        })
      } catch (err) {
        const msg = err instanceof Error ? err.message : t('common.actionFailed')
        toast.add({
          severity: 'error',
          summary: t('common.actionFailed'),
          detail: msg,
          life: 5000
        })
      }
    }
  })
}

function formatDate(d?: string | null): string {
  if (!d) return t('common.never')
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d
  }
}
</script>

<template>
  <div class="user-manager-wrapper">
    <ConfirmDialog />

    <div class="list-toolbar">
      <div>
        <h3 class="toolbar-title">{{ t('settings.userAccountsAccess') }}</h3>
        <p class="toolbar-desc">{{ t('settings.userAccountsAccessDesc') }}</p>
      </div>

      <button type="button" class="btn-primary" @click="openCreateDialog">
        <Plus :size="16" />
        <span>{{ t('settings.addUser') }}</span>
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
      <div v-else-if="!users || users.length === 0" class="empty-state">
        <Users :size="36" class="empty-icon" />
        <h3>{{ t('settings.noUsersFound') }}</h3>
        <p>{{ t('settings.noUsersDesc') }}</p>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <Plus :size="16" />
          <span>{{ t('settings.addUser') }}</span>
        </button>
      </div>

      <!-- Table -->
      <DataTable
        v-else
        :value="users"
        dataKey="id"
        responsiveLayout="scroll"
        class="p-datatable-sm"
      >
        <Column field="username" :header="t('auth.username')">
          <template #body="{ data }">
            <strong class="user-name">{{ data.username }}</strong>
          </template>
        </Column>

        <Column :header="t('common.name')">
          <template #body="{ data }">
            {{ [data.first_name, data.last_name].filter(Boolean).join(' ') || '-' }}
          </template>
        </Column>

        <Column field="email" :header="t('common.email')">
          <template #body="{ data }">
            {{ data.email || '-' }}
          </template>
        </Column>

        <Column field="role" :header="t('common.type')">
          <template #body="{ data }">
            <Tag :value="data.role || 'ADMIN'" severity="info" />
          </template>
        </Column>

        <Column field="is_active" :header="t('common.status')">
          <template #body="{ data }">
            <Tag
              :value="data.is_active !== false ? t('status.active') : t('status.inactive')"
              :severity="data.is_active !== false ? 'success' : 'danger'"
            />
          </template>
        </Column>

        <Column field="last_login" :header="t('settings.lastLogin')">
          <template #body="{ data }">
            <span class="muted-text">{{ formatDate(data.last_login) }}</span>
          </template>
        </Column>

        <Column :header="t('common.actions')" alignFrozen="right" style="width: 120px">
          <template #body="{ data }">
            <div class="row-actions">
              <button
                type="button"
                class="icon-btn"
                :title="t('settings.editUser')"
                @click="openEditDialog(data)"
              >
                <Edit2 :size="16" />
              </button>

              <button
                v-if="data.is_active !== false"
                type="button"
                class="icon-btn danger-hover"
                :title="t('settings.deactivateAccountHeader')"
                @click="confirmDeactivate(data)"
              >
                <UserX :size="16" />
              </button>

              <button
                v-else
                type="button"
                class="icon-btn success-hover"
                :title="t('settings.activateAccountHeader')"
                @click="confirmActivate(data)"
              >
                <UserCheck :size="16" />
              </button>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="isDialogOpen"
      modal
      :header="editingUser ? `${t('settings.editUser')}: ${editingUser.username}` : t('settings.addUser')"
      :style="{ width: '480px', maxWidth: '95vw' }"
    >
      <form @submit.prevent="onSubmit" class="dialog-form">
        <div v-if="!editingUser" class="form-group">
          <label for="usr-username" class="form-label">{{ t('auth.username') }} <span class="req">*</span></label>
          <InputText
            id="usr-username"
            v-model="username"
            v-bind="usernameProps"
            placeholder="e.g. john_doe"
            class="w-full"
            :class="{ 'p-invalid': errors.username }"
          />
          <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label for="usr-fname" class="form-label">First Name</label>
            <InputText
              id="usr-fname"
              v-model="first_name"
              v-bind="firstNameProps"
              placeholder="e.g. John"
              class="w-full"
            />
          </div>

          <div class="form-group">
            <label for="usr-lname" class="form-label">Last Name</label>
            <InputText
              id="usr-lname"
              v-model="last_name"
              v-bind="lastNameProps"
              placeholder="e.g. Doe"
              class="w-full"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="usr-email" class="form-label">{{ t('common.email') }}</label>
          <InputText
            id="usr-email"
            v-model="email"
            v-bind="emailProps"
            type="email"
            placeholder="e.g. john@example.com"
            class="w-full"
            :class="{ 'p-invalid': errors.email }"
          />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>

        <div class="form-group">
          <label for="usr-role" class="form-label">User Role</label>
          <Select
            id="usr-role"
            v-model="role"
            :options="roleOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
        </div>

        <div class="form-group">
          <label for="usr-password" class="form-label">
            {{ editingUser ? 'New Password (leave blank to keep unchanged)' : t('auth.password') + ' *' }}
          </label>
          <Password
            id="usr-password"
            v-model="password"
            v-bind="passwordProps"
            :feedback="false"
            toggleMask
            placeholder="••••••••"
            class="w-full"
            inputClass="w-full"
            :class="{ 'p-invalid': errors.password }"
          />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
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
            :disabled="createUserMutation.isPending.value || updateUserMutation.isPending.value"
          >
            {{ editingUser ? t('common.save') : t('common.add') }}
          </button>
        </div>
      </form>
    </Dialog>
  </div>
</template>

<style scoped>
.user-manager-wrapper {
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

.user-name {
  color: var(--text-primary);
  font-weight: 600;
}

.muted-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

@media (max-width: 500px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
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

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon-btn.success-hover:hover {
  color: var(--status-success-color);
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

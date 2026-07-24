<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import { Snowflake } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()

const serverError = ref<string | null>(null)

const loginSchema = toTypedSchema(
  z.object({
    username: z.string().min(1, 'Username is required'),
    password: z.string().min(1, 'Password is required')
  })
)

const { handleSubmit, errors, defineField, isSubmitting } = useForm({
  validationSchema: loginSchema,
  initialValues: { username: '', password: '' }
})

const [username, usernameProps] = defineField('username')
const [password, passwordProps] = defineField('password')

const onSubmit = handleSubmit(async (values) => {
  serverError.value = null
  try {
    await authStore.login(values.username, values.password)
    toast.add({
      severity: 'success',
      summary: 'Welcome back',
      detail: 'Logged in successfully',
      life: 3000
    })
    const redirectPath = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirectPath)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Invalid credentials'
    serverError.value = msg
    toast.add({
      severity: 'error',
      summary: 'Login Failed',
      detail: msg,
      life: 5000
    })
  }
})
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-badge">
          <Snowflake class="logo-icon" :size="28" />
        </div>
        <h1 class="brand-title">Cold Storage</h1>
        <p class="brand-sub">Management System</p>
      </div>

      <form @submit.prevent="onSubmit" class="login-form">
        <div v-if="serverError" class="error-alert" role="alert">
          {{ serverError }}
        </div>

        <div class="form-field">
          <label for="username" class="form-label">Username</label>
          <InputText
            id="username"
            v-model="username"
            v-bind="usernameProps"
            placeholder="Enter username"
            class="full-width"
            :invalid="!!errors.username"
            autocomplete="username"
          />
          <small v-if="errors.username" class="field-error">{{ errors.username }}</small>
        </div>

        <div class="form-field">
          <label for="password" class="form-label">Password</label>
          <Password
            id="password"
            v-model="password"
            v-bind="passwordProps"
            :feedback="false"
            toggleMask
            placeholder="Enter password"
            class="full-width"
            inputClass="full-width"
            :invalid="!!errors.password"
            autocomplete="current-password"
          />
          <small v-if="errors.password" class="field-error">{{ errors.password }}</small>
        </div>

        <Button
          type="submit"
          label="Sign In"
          class="submit-btn"
          :loading="isSubmitting || authStore.isLoading"
          :disabled="isSubmitting || authStore.isLoading"
        />
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-page);
  padding: 16px;
  box-sizing: border-box;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: var(--shadow-card);
  box-sizing: border-box;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 28px;
}

.logo-badge {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background-color: var(--accent-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35);
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.brand-sub {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.error-alert {
  padding: 10px 14px;
  border-radius: 8px;
  background-color: var(--status-danger-bg);
  color: var(--status-danger-color);
  font-size: 13px;
  font-weight: 500;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.full-width {
  width: 100%;
}

.field-error {
  color: var(--status-danger-color);
  font-size: 12px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
  background-color: var(--accent-primary) !important;
  border-color: var(--accent-primary) !important;
  color: #ffffff !important;
}

.submit-btn:hover {
  background-color: var(--accent-primary-hover) !important;
  border-color: var(--accent-primary-hover) !important;
}

@media (max-width: 480px) {
  .login-card {
    padding: 24px 18px;
  }
}
</style>

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  authCsrfRetrieve,
  authLoginCreate,
  authLogoutCreate,
  authMeRetrieve,
  authTokenCreate,
  authTokenRevokeCreate
} from '../api/generated/sdk.gen'
import type { CurrentUserOutput } from '../api/generated/types.gen'
import { Capacitor } from '@capacitor/core'
import { setToken, clearToken } from '../api/authToken'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUserOutput | null>(null)
  const isLoading = ref(false)
  const authChecked = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  const fetchCurrentUser = async (): Promise<void> => {
    isLoading.value = true
    try {
      const res = await authMeRetrieve()
      if (res.data) {
        user.value = res.data
      } else {
        user.value = null
      }
    } catch {
      user.value = null
    } finally {
      isLoading.value = false
      authChecked.value = true
    }
  }

  const login = async (username: string, password: string): Promise<CurrentUserOutput> => {
    isLoading.value = true
    try {
      if (Capacitor.isNativePlatform()) {
        const res = await authTokenCreate({
          body: { username, password }
        })

        if (res.error) {
          const errorObj = res.error as { detail?: string }
          const detailMsg =
            typeof errorObj === 'object' &&
            errorObj !== null &&
            'detail' in errorObj &&
            typeof errorObj.detail === 'string'
              ? errorObj.detail
              : 'Invalid credentials. Please try again.'
          throw new Error(detailMsg)
        }

        if (res.data) {
          setToken(res.data.token)
          user.value = res.data.user
          return res.data.user
        }

        throw new Error('Login failed. Please try again.')
      } else {
        await authCsrfRetrieve()
        const res = await authLoginCreate({
          body: { username, password }
        })

        if (res.error) {
          const errorObj = res.error as { detail?: string }
          const detailMsg =
            typeof errorObj === 'object' &&
            errorObj !== null &&
            'detail' in errorObj &&
            typeof errorObj.detail === 'string'
              ? errorObj.detail
              : 'Invalid credentials. Please try again.'
          throw new Error(detailMsg)
        }

        if (res.data) {
          user.value = res.data
          return res.data
        }

        throw new Error('Login failed. Please try again.')
      }
    } finally {
      isLoading.value = false
    }
  }

  const logout = async (): Promise<void> => {
    isLoading.value = true
    try {
      if (Capacitor.isNativePlatform()) {
        await authTokenRevokeCreate()
      } else {
        await authLogoutCreate()
      }
    } finally {
      if (Capacitor.isNativePlatform()) {
        clearToken()
      }
      user.value = null
      isLoading.value = false
    }
  }

  return {
    user,
    isLoading,
    authChecked,
    isAuthenticated,
    fetchCurrentUser,
    login,
    logout
  }
})

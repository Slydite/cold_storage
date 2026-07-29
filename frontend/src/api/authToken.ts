import { Capacitor } from '@capacitor/core'
import { Preferences } from '@capacitor/preferences'

/**
 * Auth token store.
 * Backed by Capacitor Preferences (async) on native, and localStorage (sync) on web.
 *
 * For native platform, we hydrate the token into a module-level cache once at startup
 * so that getToken() can remain synchronous.
 */

const TOKEN_KEY = 'auth_token'
let cachedToken: string | null = null

export async function hydrateToken(): Promise<void> {
  if (Capacitor.isNativePlatform()) {
    try {
      const { value } = await Preferences.get({ key: TOKEN_KEY })
      cachedToken = value
    } catch (e) {
      console.error('Error hydrating token from Capacitor Preferences:', e)
      cachedToken = null
    }
  } else {
    cachedToken = localStorage.getItem(TOKEN_KEY)
  }
}

export function getToken(): string | null {
  if (Capacitor.isNativePlatform()) {
    return cachedToken
  }
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (Capacitor.isNativePlatform()) {
    cachedToken = token
    Preferences.set({ key: TOKEN_KEY, value: token }).catch((e) => {
      console.error('Error persisting token to Capacitor Preferences:', e)
    })
  } else {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function clearToken(): void {
  if (Capacitor.isNativePlatform()) {
    cachedToken = null
    Preferences.remove({ key: TOKEN_KEY }).catch((e) => {
      console.error('Error clearing token from Capacitor Preferences:', e)
    })
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

/**
 * Auth token store. Backed by localStorage today.
 *
 * Everything goes through getToken/setToken/clearToken so the backing store can
 * be swapped for Capacitor secure storage when the app is packaged, without
 * hunting down call sites.
 *
 * ONE CAVEAT for whoever does that: Capacitor's Preferences API is async,
 * whereas getToken() is sync because it is called from the request interceptor
 * in client.ts. Swapping the backing store therefore means hydrating the token
 * into a module-level variable once at startup and keeping getToken() sync,
 * rather than making it return a Promise - that would ripple into the
 * interceptor and every apiFetch call. Not done now because the web build
 * never stores a token, so the machinery would be dead code.
 */

const TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

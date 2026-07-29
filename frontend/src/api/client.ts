import { client } from './generated/client.gen'
import { getToken } from './authToken'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

client.setConfig({
  baseUrl: API_BASE_URL,
  credentials: 'include'
})

export function getCookie(name: string): string | null {
  const match = document.cookie.match(
    new RegExp('(^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
  )
  const value = match?.[2]
  return value !== undefined ? decodeURIComponent(value) : null
}

client.interceptors.request.use((request) => {
  const token = getToken()
  if (token) {
    request.headers.set('Authorization', `Token ${token}`)
  }

  const method = request.method.toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      request.headers.set('X-CSRFToken', csrfToken)
    }
  }
  return request
})

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrlClean = API_BASE_URL.replace(/\/$/, '')
  const pathClean = path.startsWith('/') ? path : `/${path}`
  const url = `${baseUrlClean}${pathClean}`

  const headers = new Headers(init?.headers)
  const token = getToken()
  if (token) {
    headers.set('Authorization', `Token ${token}`)
  }

  const method = (init?.method ?? 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      headers.set('X-CSRFToken', csrfToken)
    }
  }

  return fetch(url, {
    ...init,
    headers,
    credentials: 'include'
  })
}


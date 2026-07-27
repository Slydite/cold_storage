import { client } from './generated/client.gen'

client.setConfig({
  baseUrl: '',
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
  const method = request.method.toUpperCase()
  if (method !== 'GET' && method !== 'HEAD') {
    const token = getCookie('csrftoken')
    if (token) {
      request.headers.set('X-CSRFToken', token)
    }
  }
  return request
})

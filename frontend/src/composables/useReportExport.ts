export function buildQueryString(params: Record<string, string | number | undefined | null>): string {
  const searchParams = new URLSearchParams()
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      searchParams.append(key, String(val))
    }
  }
  const str = searchParams.toString()
  return str ? `?${str}` : ''
}

export async function downloadReportCsv(
  endpoint: string,
  params: Record<string, string | number | undefined | null>,
  defaultFilename: string = 'report.csv'
): Promise<void> {
  const queryParams = { ...params, export_format: 'csv' }
  const url = `${endpoint}${buildQueryString(queryParams)}`

  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include'
  })

  if (!response.ok) {
    let errorDetail = 'Export failed'
    try {
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        const json = await response.json()
        errorDetail = json.detail || json.message || errorDetail
      } else {
        const text = await response.text()
        if (text) errorDetail = text
      }
    } catch {
      // fallback
    }
    throw new Error(errorDetail)
  }

  const blob = await response.blob()
  let filename = defaultFilename

  const disposition = response.headers.get('content-disposition')
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(blobUrl)
}

export async function fetchReportJson<T>(
  endpoint: string,
  params: Record<string, string | number | undefined | null>
): Promise<T> {
  const queryParams = { ...params, export_format: 'json' }
  const url = `${endpoint}${buildQueryString(queryParams)}`

  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include'
  })

  if (!response.ok) {
    let errorDetail = 'Failed to fetch report data'
    try {
      const json = await response.json()
      errorDetail = json.detail || json.message || errorDetail
    } catch {
      // fallback
    }
    throw new Error(errorDetail)
  }

  return (await response.json()) as T
}

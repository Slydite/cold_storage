/**
 * Download a server-generated PDF.
 *
 * Deliberately fetches the bytes and saves them via an object URL rather than
 * pointing an <a> at the endpoint:
 *
 *  - Consistent on mobile. A plain link opened a new tab, and on phones that
 *    either previewed unpredictably or (before the service-worker denylist was
 *    added) got answered by the SPA fallback with index.html. A real download
 *    behaves the same on every device.
 *  - Errors are visible. A link navigating to a 500 shows a raw error page in a
 *    stray tab; here the caller gets a rejected promise and can toast the
 *    backend's actual message.
 *  - The filename is ours, taken from Content-Disposition when the server sends
 *    one, instead of whatever the browser infers from the URL.
 *
 * Auth is the session cookie, so `credentials: 'include'` is required. This is a
 * GET, so no CSRF header is needed (see api/client.ts, which likewise skips it
 * for safe methods).
 */
export async function downloadPdf(url: string, fallbackFilename: string): Promise<void> {
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/pdf' }
  })

  if (!res.ok) {
    // Surface the API's message when it sent one, rather than a bare status.
    let detail = `Request failed (${res.status})`
    const contentType = res.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      try {
        const body = (await res.json()) as { detail?: string }
        if (body.detail) detail = body.detail
      } catch {
        // Malformed JSON error body - keep the status-based message.
      }
    }
    throw new Error(detail)
  }

  let filename = fallbackFilename
  const disposition = res.headers.get('content-disposition')
  if (disposition) {
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
    if (match?.[1]) filename = decodeURIComponent(match[1])
  }

  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  try {
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    // Revoke on the next tick; revoking synchronously can cancel the download
    // in some browsers before it has started reading the blob.
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
  }
}

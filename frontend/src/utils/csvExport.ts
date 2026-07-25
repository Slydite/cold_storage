export function exportToCsv(
  filename: string,
  headers: string[],
  rows: (string | number | null | undefined)[][]
): void {
  const escapeCsvField = (val: string | number | null | undefined): string => {
    if (val === null || val === undefined) return '""'
    const str = String(val)
    if (/[",\n\r]/.test(str)) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  const headerLine = headers.map(escapeCsvField).join(',')
  const rowLines = rows.map((row) => row.map(escapeCsvField).join(','))
  const csvContent = [headerLine, ...rowLines].join('\r\n')

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const downloadName = filename.endsWith('.csv') ? filename : `${filename}.csv`

  link.setAttribute('href', url)
  link.setAttribute('download', downloadName)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

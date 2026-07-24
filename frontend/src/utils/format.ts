export function formatQty(value: number, decimals = 3): string {
  return value.toFixed(decimals)
}

export function formatCurrency(value: number): string {
  return `₹ ${value.toLocaleString('en-IN')}`
}

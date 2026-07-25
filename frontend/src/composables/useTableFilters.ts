import { ref, computed, type Ref, type ComputedRef } from 'vue'

export function formatDateFilter(val: unknown): string | null {
  if (!val) return null
  if (val instanceof Date) {
    const yyyy = val.getFullYear()
    const mm = String(val.getMonth() + 1).padStart(2, '0')
    const dd = String(val.getDate()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
  }
  return String(val)
}

export function useTableFilters<T extends Record<string, unknown>>(
  buildDefaults: () => T,
  extraActiveCount?: Ref<number> | ComputedRef<number> | (() => number)
) {
  const filters = ref(buildDefaults()) as Ref<T>
  const showFilterRow = ref(false)

  const activeFilterCount = computed(() => {
    let count = 0
    const filterObj = filters.value
    if (filterObj && typeof filterObj === 'object') {
      const keys = Object.keys(filterObj) as Array<keyof T>
      for (const key of keys) {
        if (key === 'global') continue
        const item = filterObj[key]
        if (item === undefined || item === null) continue
        if (typeof item === 'object' && item !== null && 'value' in item) {
          const val = (item as { value?: unknown }).value
          if (
            val !== null &&
            val !== undefined &&
            val !== '' &&
            !(Array.isArray(val) && val.length === 0)
          ) {
            count++
          }
        } else if (item !== '' && !(Array.isArray(item) && item.length === 0)) {
          count++
        }
      }
    }

    if (extraActiveCount) {
      const extra = typeof extraActiveCount === 'function' ? extraActiveCount() : extraActiveCount.value
      count += extra
    }

    return count
  })

  const hasActiveFilters = computed(() => activeFilterCount.value > 0)

  function clearFilters() {
    filters.value = buildDefaults()
  }

  function toggleFilterRow() {
    showFilterRow.value = !showFilterRow.value
  }

  return {
    filters,
    showFilterRow,
    activeFilterCount,
    hasActiveFilters,
    clearFilters,
    toggleFilterRow
  }
}

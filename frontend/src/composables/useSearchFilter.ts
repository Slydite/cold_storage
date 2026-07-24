import { ref, computed, type Ref } from 'vue'

/**
 * Generic substring search over a reactive list. Views that need extra
 * (non-text) filters should chain a further `.filter()` off the returned
 * `filtered` computed rather than growing the matcher here.
 */
export function useSearchFilter<T>(source: Ref<T[]>, matcher: (item: T, query: string) => boolean) {
  const searchQuery = ref('')

  const filtered = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()
    if (!query) return source.value
    return source.value.filter((item) => matcher(item, query))
  })

  return { searchQuery, filtered }
}

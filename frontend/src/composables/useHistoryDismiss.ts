import { watch, onUnmounted, type Ref } from 'vue'

export function useHistoryDismiss(isOpen: Ref<boolean>, close: () => void): void {
  const myStateId = Math.random().toString(36).substring(2, 9)
  let hasPushedEntry = false
  let suppressPopstate = false

  const handlePopState = (event: PopStateEvent) => {
    if (suppressPopstate) {
      suppressPopstate = false
      return
    }

    if (hasPushedEntry) {
      const state = event.state || history.state
      const currentId =
        state && typeof state === 'object'
          ? (state as Record<string, unknown>).__dismiss_id
          : null
      if (currentId !== myStateId) {
        hasPushedEntry = false
        close()
      }
    }
  }

  watch(
    isOpen,
    (newVal) => {
      if (newVal) {
        if (!hasPushedEntry) {
          hasPushedEntry = true
          history.pushState({ __dismiss: true, __dismiss_id: myStateId }, '')
          window.addEventListener('popstate', handlePopState)
        }
      } else {
        if (hasPushedEntry) {
          hasPushedEntry = false
          const state = history.state
          const currentId =
            state && typeof state === 'object'
              ? (state as Record<string, unknown>).__dismiss_id
              : null
          if (currentId === myStateId) {
            suppressPopstate = true
            history.back()
          }
          window.removeEventListener('popstate', handlePopState)
        }
      }
    },
    { flush: 'sync', immediate: true }
  )

  onUnmounted(() => {
    if (hasPushedEntry) {
      hasPushedEntry = false
      const state = history.state
      const currentId =
        state && typeof state === 'object'
          ? (state as Record<string, unknown>).__dismiss_id
          : null
      if (currentId === myStateId) {
        suppressPopstate = true
        history.back()
      }
    }
    window.removeEventListener('popstate', handlePopState)
  })
}

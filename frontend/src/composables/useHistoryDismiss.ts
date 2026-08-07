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
          // Preserve whatever vue-router keeps in history.state and only add our
          // marker. Replacing the state wholesale wipes router bookkeeping --
          // it computes navigation deltas as `history.state.position - n`, so a
          // missing position yields NaN and the router resolves a bad location,
          // which is how a click on a row could land on "/undefined".
          const current = (history.state ?? {}) as Record<string, unknown>
          const position = current.position
          history.pushState(
            {
              ...current,
              // Each entry must carry a distinct, increasing position for those
              // delta calculations to stay correct.
              ...(typeof position === 'number' ? { position: position + 1 } : {}),
              __dismiss: true,
              __dismiss_id: myStateId
            },
            ''
          )
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

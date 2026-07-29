import { ref } from 'vue'

const isOpen = ref(false)

export function useSidebar() {
  const open = () => {
    if (typeof window !== 'undefined' && window.innerWidth <= 768) return
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  const toggle = () => {
    if (typeof window !== 'undefined' && window.innerWidth <= 768) return
    isOpen.value = !isOpen.value
  }

  return {
    isOpen,
    open,
    close,
    toggle
  }
}

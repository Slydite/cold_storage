import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

export type Theme = 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  const getInitialTheme = (): Theme => {
    const saved = localStorage.getItem('cs_theme') as Theme | null
    if (saved === 'dark' || saved === 'light') {
      return saved
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  const theme = ref<Theme>(getInitialTheme())

  const toggleTheme = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
  }

  watchEffect(() => {
    document.documentElement.setAttribute('data-theme', theme.value)
    if (theme.value === 'dark') {
      document.documentElement.classList.add('app-dark')
    } else {
      document.documentElement.classList.remove('app-dark')
    }
    localStorage.setItem('cs_theme', theme.value)
  })

  return {
    theme,
    toggleTheme,
    setTheme
  }
})

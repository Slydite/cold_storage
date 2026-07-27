import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'
import i18n from '../i18n'

export type SupportedLocale = 'en' | 'hi'

export const useLocaleStore = defineStore('locale', () => {
  const getInitialLocale = (): SupportedLocale => {
    const saved = localStorage.getItem('cs_locale') as SupportedLocale | null
    if (saved === 'en' || saved === 'hi') {
      return saved
    }
    return 'en'
  }

  const locale = ref<SupportedLocale>(getInitialLocale())

  const toggleLocale = () => {
    locale.value = locale.value === 'en' ? 'hi' : 'en'
  }

  const setLocale = (newLocale: SupportedLocale) => {
    locale.value = newLocale
  }

  watchEffect(() => {
    const currentLocale = locale.value
    document.documentElement.lang = currentLocale
    localStorage.setItem('cs_locale', currentLocale)
    if (i18n.mode === 'legacy') {
      ;(i18n.global.locale as unknown as string) = currentLocale
    } else {
      ;(i18n.global.locale as unknown as { value: string }).value = currentLocale
    }
  })

  return {
    locale,
    toggleLocale,
    setLocale
  }
})

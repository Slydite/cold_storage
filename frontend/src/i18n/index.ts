import { createI18n } from 'vue-i18n'
import en, { type MessageSchema } from './locales/en'
import hi from './locales/hi'

export const i18n = createI18n<[MessageSchema], 'en' | 'hi'>({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  globalInjection: true,
  messages: {
    en,
    hi
  },
  numberFormats: {
    en: {
      currency: {
        style: 'currency',
        currency: 'INR',
        currencyDisplay: 'symbol'
      }
    },
    hi: {
      currency: {
        style: 'currency',
        currency: 'INR',
        currencyDisplay: 'symbol'
      }
    }
  },
  datetimeFormats: {
    en: {
      short: {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      },
      long: {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric'
      }
    },
    hi: {
      short: {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      },
      long: {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric'
      }
    }
  }
})

export default i18n

import type { MessageSchema } from './locales/en'

declare module 'vue-i18n' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface DefineDateTimeFormat {}
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface DefineNumberFormat {}
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface DefineLocaleMessage extends MessageSchema {}
}

import en from '@/locales/en.json'
import hi from '@/locales/hi.json'
import pa from '@/locales/pa.json'
import gu from '@/locales/gu.json'
import mr from '@/locales/mr.json'
import bn from '@/locales/bn.json'

const locales: Record<string, Record<string, string>> = { en, hi, pa, gu, mr, bn }

export function getTranslation(key: string, lang: string): string {
  const dict = locales[lang] ?? locales.en
  return dict[key] ?? locales.en[key] ?? key
}

export type TranslationKey = keyof typeof en

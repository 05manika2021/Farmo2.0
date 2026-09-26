'use client'

import { useCallback } from 'react'
import { useApp } from '@/contexts/AppContext'
import { getTranslation, type TranslationKey } from '@/lib/i18n'

export function useT() {
  const { state } = useApp()
  const lang = state.language ?? 'en'

  const t = useCallback(
    (key: TranslationKey | string) => getTranslation(key, lang),
    [lang]
  )

  return t
}

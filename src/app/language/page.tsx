'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Button from '@/components/Button'
import { useApp } from '@/contexts/AppContext'
import { useT } from '@/hooks/useT'

const LANGUAGES = [
  { code: 'hi', name: 'हिंदी', english: 'Hindi', flag: '🇮🇳' },
  { code: 'mr', name: 'मराठी', english: 'Marathi', flag: '🇮🇳' },
  { code: 'pa', name: 'ਪੰਜਾਬੀ', english: 'Punjabi', flag: '🇮🇳' },
  { code: 'gu', name: 'ગુજરાતી', english: 'Gujarati', flag: '🇮🇳' },
  { code: 'kn', name: 'ಕನ್ನಡ', english: 'Kannada', flag: '🇮🇳' },
  { code: 'te', name: 'తెలుగు', english: 'Telugu', flag: '🇮🇳' },
  { code: 'en', name: 'English', english: 'English', flag: '🇬🇧' },
]

export default function LanguagePage() {
  const router = useRouter()
  const { setLanguage } = useApp()
  const t = useT()
  const [selected, setSelected] = useState('hi')

  const handleContinue = () => {
    setLanguage(selected)
    router.push('/phone')
  }

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <div className="bg-primary px-6 pt-14 pb-8">
        <div className="flex items-center gap-3 mb-4">
          <svg width="32" height="32" viewBox="0 0 80 80" fill="none">
            <line x1="40" y1="64" x2="40" y2="18" stroke="#CFD050" strokeWidth="4" strokeLinecap="round"/>
            <ellipse cx="30" cy="30" rx="8" ry="5" fill="#CFD050" transform="rotate(-30 30 30)"/>
            <ellipse cx="50" cy="30" rx="8" ry="5" fill="white" transform="rotate(30 50 30)"/>
            <ellipse cx="40" cy="20" rx="5" ry="8" fill="#CFD050"/>
          </svg>
          <span className="text-2xl font-black text-white">Farmo</span>
        </div>
        <h1 className="text-2xl font-bold text-white mb-1">{t('language.chooseLanguage')}</h1>
        <p className="text-white/60 text-sm">{t('language.subtitle')}</p>
      </div>

      <div className="flex-1 px-4 py-5 space-y-3 overflow-y-auto no-scrollbar">
        {LANGUAGES.map((lang) => {
          const isSelected = selected === lang.code
          return (
            <button
              key={lang.code}
              onClick={() => setSelected(lang.code)}
              className={`w-full flex items-center gap-4 p-4 rounded-2xl border-2 transition-all active:scale-98 ${
                isSelected
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-card hover:border-primary/30'
              }`}
            >
              <span className="text-2xl">{lang.flag}</span>
              <div className="flex-1 text-left">
                <p className={`text-lg font-bold ${isSelected ? 'text-primary' : 'text-foreground'}`}>
                  {lang.name}
                </p>
                <p className="text-xs text-muted-foreground">{lang.english}</p>
              </div>
              {isSelected && (
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                  <circle cx="11" cy="11" r="11" fill="#18594B"/>
                  <path d="M6 11L9.5 14.5L16 8" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          )
        })}
      </div>

      <div className="px-4 pb-8 pt-3">
        <Button fullWidth size="lg" onClick={handleContinue}>
          {t('language.continue')}
        </Button>
      </div>
    </div>
  )
}

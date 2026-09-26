'use client'

import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { useT } from '@/hooks/useT'

const cropEmoji: Record<string, string> = {
  Wheat: '🌾',
  Cotton: '🪡',
  Soybean: '🌱',
}

export default function SettingsPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()

  const displayName = state.name || 'Farmer'
  const formattedPhone = state.phone
    ? '+91 XXXXX ' + String(state.phone).slice(-5)
    : '+91 XXXXX XXXXX'
  const cropTags = (state.crops || []).map((c) => `${c} ${cropEmoji[c] || '🌱'}`)

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar onBack={() => router.push('/home')} />

      <div className="bg-primary px-5 pt-2 pb-8">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center">
            <span className="text-2xl font-black text-secondary-foreground">{displayName.charAt(0).toUpperCase()}</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">{displayName}</h1>
            <p className="text-white/60 text-sm">{formattedPhone}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path d="M5 1C3.3 1 2 2.3 2 4C2 6.5 5 9 5 9C5 9 8 6.5 8 4C8 2.3 6.7 1 5 1Z" fill="#CFD050"/>
                <circle cx="5" cy="4" r="1" fill="#18594B"/>
              </svg>
              <span className="text-white/50 text-xs">{state.villageName || t('settings.locationNotSet')}</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-4 flex-wrap">
          {cropTags.length > 0 ? cropTags.map((c) => (
            <span key={c} className="text-xs font-semibold bg-white/10 text-white px-3 py-1.5 rounded-full">
              {c}
            </span>
          )) : (
            <span className="text-xs font-semibold bg-white/10 text-white px-3 py-1.5 rounded-full">
              {t('settings.noCrops')}
            </span>
          )}
        </div>
      </div>

      <div className="mx-4 -mt-4 mb-4 grid grid-cols-3 gap-2">
        {[
          { label: t('settings.queries'), value: '47' },
          { label: t('settings.marketsChecked'), value: '12' },
          { label: t('settings.daysActive'), value: '31' },
        ].map((s) => (
          <div key={s.label} className="bg-card rounded-2xl border border-border p-3 text-center shadow-sm">
            <p className="text-xl font-black text-primary">{s.value}</p>
            <p className="text-[10px] text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-4 space-y-4">
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 px-1">{t('settings.profile')}</p>
          <div className="bg-card rounded-2xl border border-border overflow-hidden">
            {[
              { icon: '👤', label: t('settings.editNameAge'), value: displayName },
              { icon: '🌾', label: t('settings.myCrops'), value: (state.crops || []).join(', ') || t('settings.noCrops') },
              { icon: '📍', label: t('settings.village'), value: state.villageName || t('settings.locationNotSet') },
            ].map((item, i, arr) => (
              <button
                key={item.label}
                className={`w-full flex items-center gap-4 px-4 py-4 text-left hover:bg-muted active:bg-muted transition-colors ${
                  i < arr.length - 1 ? 'border-b border-border' : ''
                }`}
              >
                <span className="text-xl w-8 text-center">{item.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">{item.label}</p>
                  <p className="text-xs text-muted-foreground">{item.value}</p>
                </div>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M6 4L10 8L6 12" stroke="#5A7A70" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 px-1">{t('settings.preferences')}</p>
          <div className="bg-card rounded-2xl border border-border overflow-hidden">
            {[
              { icon: '🌐', label: t('settings.language'), value: state.language || 'Hindi' },
              { icon: '🔔', label: t('settings.priceAlerts'), value: 'On · ₹2,200 threshold' },
              { icon: '📱', label: t('settings.notificationMethod'), value: 'Voice + SMS' },
            ].map((item, i, arr) => (
              <button
                key={item.label}
                className={`w-full flex items-center gap-4 px-4 py-4 text-left hover:bg-muted active:bg-muted transition-colors ${
                  i < arr.length - 1 ? 'border-b border-border' : ''
                }`}
              >
                <span className="text-xl w-8 text-center">{item.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">{item.label}</p>
                  <p className="text-xs text-muted-foreground">{item.value}</p>
                </div>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M6 4L10 8L6 12" stroke="#5A7A70" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 px-1">{t('settings.support')}</p>
          <div className="bg-card rounded-2xl border border-border overflow-hidden">
            {[
              { icon: '❓', label: t('settings.helpFaq') },
              { icon: '📞', label: t('settings.callHelpline') },
              { icon: '⭐', label: t('settings.rateFarmo') },
              { icon: '🔒', label: t('settings.privacy') },
            ].map((item, i, arr) => (
              <button
                key={item.label}
                className={`w-full flex items-center gap-4 px-4 py-4 text-left hover:bg-muted active:bg-muted transition-colors ${
                  i < arr.length - 1 ? 'border-b border-border' : ''
                }`}
              >
                <span className="text-xl w-8 text-center">{item.icon}</span>
                <p className="flex-1 text-sm font-semibold text-foreground">{item.label}</p>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M6 4L10 8L6 12" stroke="#5A7A70" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            ))}
          </div>
        </div>

        <div className="text-center pt-2 pb-2">
          <p className="text-xs text-muted-foreground">Farmo v1.0.0 · {t('settings.madeForFarmers')} 🇮🇳</p>
        </div>
      </div>

      <BottomNav active="settings" />
    </div>
  )
}

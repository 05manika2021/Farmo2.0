'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Button from '@/components/Button'
import { useApp } from '@/contexts/AppContext'
import { reverseGeocode } from '@/lib/api'
import { useT } from '@/hooks/useT'

interface DetectedLocation {
  latitude: number
  longitude: number
  village?: string | null
  locality?: string | null
  district?: string | null
  state?: string | null
  display_name?: string | null
}

export default function LocationPage() {
  const router = useRouter()
  const { state, setLocation } = useApp()
  const t = useT()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detected, setDetected] = useState<DetectedLocation | null>(null)

  const handleAllowLocation = () => {
    setError(null)
    setLoading(true)

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        try {
          const geo = await reverseGeocode(latitude, longitude, state.language) as DetectedLocation | null
          if (geo && (geo.village || geo.locality || geo.display_name)) {
            setDetected({
              latitude,
              longitude,
              village: geo.village,
              locality: geo.locality,
              district: geo.district,
              state: geo.state,
              display_name: geo.display_name,
            })
            setLoading(false)
            return
          }
          setLocation(latitude, longitude, geo?.village ?? undefined)
          router.push('/home')
        } catch {
          setLocation(latitude, longitude)
          router.push('/home')
        }
      },
      () => {
        setLoading(false)
        setError(t('location.denied'))
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleConfirm = () => {
    if (!detected) return
    const label = [detected.village, detected.district, detected.state]
      .filter(Boolean)
      .join(', ') || detected.display_name || undefined
    setLocation(detected.latitude, detected.longitude, label)
    router.push('/home')
  }

  const handleChange = () => {
    setDetected(null)
    setError(null)
  }

  const detectedLabel = detected
    ? [detected.village, detected.district, detected.state].filter(Boolean).join(', ') ||
      detected.display_name ||
      ''
    : ''

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <div className="bg-primary pt-14 pb-10 px-6 flex flex-col items-center">
        <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center mb-4">
          <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
            <path d="M26 4C17.163 4 10 11.163 10 20C10 32 26 48 26 48C26 48 42 32 42 20C42 11.163 34.837 4 26 4Z" fill="#CFD050"/>
            <circle cx="26" cy="20" r="6" fill="#18594B"/>
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-white text-center mb-2">{t('location.title')}</h1>
        <p className="text-white/70 text-sm text-center px-4">
          {t('location.description')}
        </p>
      </div>

      <div className="flex-1 px-6 py-8 space-y-5">
        {[
          { icon: '📍', title: t('location.nearbyMandis'), desc: t('location.nearbyDesc') },
          { icon: '🚛', title: t('location.transportCost'), desc: t('location.transportDesc') },
          { icon: '💹', title: t('location.bestPrice'), desc: t('location.bestPriceDesc') },
        ].map((item) => (
          <div key={item.title} className="flex gap-4 items-start">
            <div className="w-12 h-12 bg-muted rounded-xl flex items-center justify-center text-xl shrink-0">
              {item.icon}
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{item.title}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
            </div>
          </div>
        ))}

        {detected && (
          <div className="rounded-2xl border border-border bg-card p-4 space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {t('location.detected')}
            </p>
            <p className="text-base font-semibold text-foreground">{detectedLabel}</p>
            {detected.state && (
              <p className="text-xs text-muted-foreground">
                {t('location.state')}: {detected.state}
              </p>
            )}
            {detected.district && (
              <p className="text-xs text-muted-foreground">
                {t('location.district')}: {detected.district}
              </p>
            )}
            {(detected.village || detected.locality) && (
              <p className="text-xs text-muted-foreground">
                {t('location.village')}: {detected.village || detected.locality}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="px-6 pb-8 space-y-3">
        {error && (
          <p className="text-destructive text-sm text-center">{error}</p>
        )}
        {detected ? (
          <>
            <Button fullWidth size="lg" onClick={handleConfirm}>
              {t('village.confirm')}
            </Button>
            <Button fullWidth size="lg" variant="ghost" onClick={handleChange}>
              {t('location.change')}
            </Button>
          </>
        ) : (
          <>
            <Button fullWidth size="lg" onClick={handleAllowLocation} disabled={loading}>
              {loading ? t('location.searching') : t('location.detect')}
            </Button>
            <Button fullWidth size="lg" variant="ghost" onClick={() => router.push('/village')}>
              {t('location.selectManually')}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

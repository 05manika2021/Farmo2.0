'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import Button from '@/components/Button'
import { useApp } from '@/contexts/AppContext'
import { createProfile, addCrop, reverseGeocode } from '@/lib/api'
import { useT } from '@/hooks/useT'

const CROPS = ['Wheat', 'Rice', 'Cotton', 'Soybean', 'Maize', 'Sugarcane', 'Tomato', 'Onion', 'Potato', 'Pulses']

const CROP_KEYS: Record<string, string> = {
  Wheat: 'crop.wheat',
  Rice: 'crop.rice',
  Cotton: 'crop.cotton',
  Soybean: 'crop.soybean',
  Maize: 'crop.maize',
  Sugarcane: 'crop.sugarcane',
  Tomato: 'crop.tomato',
  Onion: 'crop.onion',
  Potato: 'crop.potato',
  Pulses: 'crop.pulses',
}

export default function ProfilePage() {
  const router = useRouter()
  const { state, setProfile, setCrops, setFarmerId, setLocation } = useApp()
  const t = useT()
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [village, setVillage] = useState('')
  const [selectedCrops, setSelectedCrops] = useState<string[]>(['Wheat'])
  const [step, setStep] = useState(1)
  const [detecting, setDetecting] = useState(false)
  const [detectError, setDetectError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null)

  const toggleCrop = (c: string) => {
    setSelectedCrops((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    )
  }

  const isStep1Valid = name.trim().length >= 2
  const isStep2Valid = selectedCrops.length > 0

  const handleDetectLocation = () => {
    setDetectError(null)
    setDetecting(true)
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        setCoords({ lat: latitude, lon: longitude })
        try {
          const geo = await reverseGeocode(latitude, longitude, state.language) as {
            village?: string | null
            locality?: string | null
            district?: string | null
            state?: string | null
            display_name?: string | null
          } | null
          const label =
            geo?.village ||
            geo?.locality ||
            geo?.display_name ||
            ''
          if (label) setVillage(label)
          setLocation(latitude, longitude, label || undefined)
        } catch {
          setDetectError(t('location.notFound'))
        } finally {
          setDetecting(false)
        }
      },
      () => {
        setDetecting(false)
        setDetectError(t('location.denied'))
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleFinish = async () => {
    if (saving) return
    setSaving(true)
    setSubmitError(null)
    try {
      const profileData = {
        name,
        age: parseInt(age) || undefined,
        language: state.language,
        village: village || undefined,
        latitude: coords?.lat,
        longitude: coords?.lon,
      }
      const result = await createProfile(profileData, state.token!) as {
        id?: number
        success?: boolean
        error_code?: string
        message?: string
      } | null

      if (!result || result.success === false || typeof result.id !== 'number') {
        setSubmitError(result?.message || t('phone.error'))
        setSaving(false)
        return
      }

      setFarmerId(result.id)

      await Promise.all(
        selectedCrops.map((crop) =>
          addCrop(result.id!, { crop_name: crop, quantity: 5 }, state.token!)
        )
      )

      setProfile(name, age, village)
      setCrops(selectedCrops)
      if (coords) setLocation(coords.lat, coords.lon, village || undefined)
      router.push('/location')
    } catch (err) {
      console.error('Failed to create profile:', err)
      setSubmitError(t('phone.error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar
        title={t('profile.setup')}
        onBack={step === 1 ? () => router.push('/otp') : () => setStep(1)}
      />

      <div className="px-6 mb-6">
        <div className="flex gap-1.5">
          {[1, 2].map((s) => (
            <div key={s} className={`h-1 rounded-full flex-1 transition-all ${s <= step ? 'bg-primary' : 'bg-border'}`} />
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-1.5">{t('profile.step')} {step} {t('profile.of')} 2</p>
      </div>

      {step === 1 ? (
        <div className="flex-1 px-6 space-y-5">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-1">{t('profile.tellUs')}</h1>
            <p className="text-sm text-muted-foreground">{t('profile.personalize')}</p>
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              {t('profile.fullName')}
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ramesh Kumar"
              className="w-full px-4 py-3.5 rounded-2xl border-2 border-border focus:border-primary outline-none text-base font-medium text-foreground bg-card transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              {t('profile.age')}
            </label>
            <input
              type="number"
              inputMode="numeric"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="42"
              min="18"
              max="99"
              className="w-full px-4 py-3.5 rounded-2xl border-2 border-border focus:border-primary outline-none text-base font-medium text-foreground bg-card transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">
              {t('profile.villageTown')}
            </label>
            <div className="space-y-2">
              <input
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                placeholder="Jaitpur, Haryana"
                className="w-full px-4 py-3.5 rounded-2xl border-2 border-border focus:border-primary outline-none text-base font-medium text-foreground bg-card transition-colors"
              />
              <Button
                fullWidth
                variant="outline"
                size="md"
                loading={detecting}
                onClick={handleDetectLocation}
              >
                {detecting ? t('location.searching') : t('location.detect')}
              </Button>
              {detectError && (
                <p className="text-xs text-destructive">{detectError}</p>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 px-6">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-foreground mb-1">{t('profile.yourCrops')}</h1>
            <p className="text-sm text-muted-foreground">{t('profile.selectCrops')}</p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            {CROPS.map((crop) => {
              const selected = selectedCrops.includes(crop)
              const label = t(CROP_KEYS[crop] || crop)
              return (
                <button
                  key={crop}
                  onClick={() => toggleCrop(crop)}
                  className={`px-4 py-2.5 rounded-2xl text-sm font-semibold border-2 transition-all active:scale-95 ${
                    selected
                      ? 'bg-primary text-white border-primary'
                      : 'bg-card text-foreground border-border hover:border-primary/40'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {selectedCrops.length > 0 && (
            <div className="mt-5 p-3.5 bg-secondary/15 rounded-2xl">
              <p className="text-xs font-semibold text-foreground">
                {t('profile.selected')}: {selectedCrops.map((c) => t(CROP_KEYS[c] || c)).join(', ')}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="px-6 pb-8 pt-4 space-y-3">
        {step === 2 && submitError && (
          <p className="text-xs text-destructive text-center">{submitError}</p>
        )}
        {step === 1 ? (
          <Button fullWidth size="lg" disabled={!isStep1Valid} onClick={() => setStep(2)}>
            {t('profile.next')}
          </Button>
        ) : (
          <Button fullWidth size="lg" disabled={!isStep2Valid} loading={saving} onClick={handleFinish}>
            {t('profile.createProfile')}
          </Button>
        )}
      </div>
    </div>
  )
}

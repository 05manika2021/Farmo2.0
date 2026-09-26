'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import Button from '@/components/Button'
import { useApp } from '@/contexts/AppContext'
import { sendOtp } from '@/lib/api'
import { useT } from '@/hooks/useT'

const ERROR_TRANSLATIONS: Record<string, string> = {
  OTP_SEND_FAILED: 'phone.sendFailed',
  OTP_RATE_LIMITED: 'phone.rateLimited',
  INVALID_PHONE_NUMBER: 'phone.invalid',
  OTP_PROVIDER_NOT_CONFIGURED: 'phone.providerNotConfigured',
  PROVIDER_NOT_CONFIGURED: 'phone.providerNotConfigured',
}

function normalizePhone(raw: string): string {
  const digits = raw.replace(/\D/g, '')
  if (digits.startsWith('91') && digits.length > 10) return digits.slice(-10)
  if (digits.startsWith('0') && digits.length > 10) return digits.slice(-10)
  return digits
}

const VALID_MOBILE_PREFIXES = /^[6-9]/

export default function PhonePage() {
  const router = useRouter()
  const { setPhone } = useApp()
  const t = useT()
  const [phone, setPhoneState] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const normalized = phone.length > 0 ? normalizePhone(phone) : ''
  const isValid = normalized.length === 10 && /^\d{10}$/.test(normalized) && VALID_MOBILE_PREFIXES.test(normalized)

  const handleChange = (raw: string) => {
    setPhoneState(raw)
    setError('')
  }

  const handleSubmit = async () => {
    if (!isValid) return
    setLoading(true)
    setError('')
    try {
      const res = await sendOtp(normalized) as { success: boolean; message?: string; error_code?: string } | null
      if (res?.success) {
        setPhone(normalized)
        router.push('/otp')
      } else if (res?.error_code && ERROR_TRANSLATIONS[res.error_code]) {
        setError(t(ERROR_TRANSLATIONS[res.error_code]))
      } else {
        setError(res?.message || t('phone.sendFailed'))
      }
    } catch {
      setError(t('phone.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar onBack={() => router.push('/language')} />

      <div className="flex-1 px-6 pt-6">
        <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-6">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect x="8" y="2" width="16" height="28" rx="4" stroke="#18594B" strokeWidth="2"/>
            <circle cx="16" cy="26" r="1.5" fill="#18594B"/>
            <line x1="12" y1="6" x2="20" y2="6" stroke="#18594B" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-2">{t('phone.title')}</h1>
        <p className="text-sm text-muted-foreground mb-8">
          {t('phone.subtitle')}
        </p>

        <div className={`flex items-center border-2 rounded-2xl overflow-hidden transition-colors ${
          phone.length > 0 && !isValid ? 'border-destructive' : phone.length > 0 && isValid ? 'border-primary' : 'border-border'
        }`}>
          <div className="flex items-center gap-2 px-4 py-4 border-r border-border bg-muted">
            <span className="text-lg">🇮🇳</span>
            <span className="text-base font-semibold text-foreground">+91</span>
          </div>
          <input
            type="tel"
            inputMode="numeric"
            value={phone}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="9876543210"
            className="flex-1 px-4 py-4 text-xl font-semibold text-foreground bg-transparent outline-none placeholder:text-muted-foreground/50 tracking-widest"
          />
        </div>

        {phone.length > 0 && !isValid && (
          <p className="text-xs text-destructive mt-2 ml-1">{t('phone.invalid')}</p>
        )}

        {error && (
          <p className="text-xs text-destructive mt-2 ml-1">{error}</p>
        )}

        <div className="mt-6 p-4 bg-muted rounded-2xl flex gap-3">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="shrink-0 mt-0.5">
            <circle cx="9" cy="9" r="8" stroke="#18594B" strokeWidth="1.5"/>
            <line x1="9" y1="8" x2="9" y2="13" stroke="#18594B" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="9" cy="5.5" r="1" fill="#18594B"/>
          </svg>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {t('phone.privacy')}
          </p>
        </div>
      </div>

      <div className="px-6 pb-8">
        <Button fullWidth size="lg" disabled={!isValid} loading={loading} onClick={handleSubmit}>
          {t('phone.getOtp')}
        </Button>
        <p className="text-center text-xs text-muted-foreground mt-4">
          {t('phone.terms')}
        </p>
      </div>
    </div>
  )
}

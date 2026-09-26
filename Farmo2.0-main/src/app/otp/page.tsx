'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import Button from '@/components/Button'
import { verifyOtp, resendOtp } from '@/lib/api'
import { useApp } from '@/contexts/AppContext'
import { useT } from '@/hooks/useT'

const ERROR_TRANSLATIONS: Record<string, string> = {
  INVALID_OTP: 'otp.incorrect',
  OTP_EXPIRED: 'otp.expired',
  OTP_MAX_ATTEMPTS: 'otp.maxAttempts',
  OTP_NOT_FOUND: 'otp.notFound',
  OTP_VERIFICATION_FAILED: 'otp.incorrect',
}

export default function OTPPage() {
  const router = useRouter()
  const { state, setToken, setFarmerId } = useApp()
  const t = useT()
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [timer, setTimer] = useState(30)
  const [error, setError] = useState(false)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [resent, setResent] = useState(false)
  const refs = [
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
  ]

  useEffect(() => {
    if (timer <= 0) return
    const t2 = setInterval(() => setTimer((p) => p - 1), 1000)
    return () => clearInterval(t2)
  }, [timer])

  const handleChange = (idx: number, val: string) => {
    const digit = val.replace(/\D/g, '').slice(-1)
    const next = [...otp]
    next[idx] = digit
    setOtp(next)
    setError(false)
    if (digit && idx < 5) refs[idx + 1].current?.focus()
  }

  const handleKeyDown = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
      refs[idx - 1].current?.focus()
    }
  }

  const handleVerify = async () => {
    const code = otp.join('')
    if (code.length < 6) return
    setLoading(true)
    try {
      const result = await verifyOtp(state.phone, code) as { success: boolean; access_token?: string; farmer_id?: number; error_code?: string } | null
      if (result?.success) {
        setToken(result.access_token ?? null)
        setFarmerId(result.farmer_id ?? null)
        router.push('/profile')
      } else {
        setError(true)
        setErrorKey(result?.error_code || null)
        setOtp(['', '', '', '', '', ''])
        refs[0].current?.focus()
      }
    } catch {
      setError(true)
      setErrorKey(null)
      setOtp(['', '', '', '', '', ''])
      refs[0].current?.focus()
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setTimer(30)
    setResent(true)
    setError(false)
    setOtp(['', '', '', '', '', ''])
    try {
      await resendOtp(state.phone)
    } catch {
      // ignore resend errors
    }
    setTimeout(() => setResent(false), 3000)
  }

  const filled = otp.every((d) => d !== '')

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar onBack={() => router.push('/phone')} />

      <div className="flex-1 px-6 pt-6">
        <div className="w-16 h-16 bg-secondary/20 rounded-2xl flex items-center justify-center mb-6">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <path d="M4 8C4 6.9 4.9 6 6 6H26C27.1 6 28 6.9 28 8V24C28 25.1 27.1 26 26 26H6C4.9 26 4 25.1 4 24V8Z" stroke="#18594B" strokeWidth="2"/>
            <path d="M4 10L16 18L28 10" stroke="#18594B" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-1">{t('otp.title')}</h1>
        <p className="text-sm text-muted-foreground mb-8">
          {t('otp.sentTo')} <span className="font-semibold text-foreground">{state.phone}</span>
        </p>

        <div className="flex gap-2 mb-4 justify-between">
          {otp.map((digit, i) => (
            <input
              key={i}
              ref={refs[i]}
              className={`otp-input ${digit ? 'filled' : ''} ${error ? 'error' : ''}`}
              type="tel"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              autoFocus={i === 0}
            />
          ))}
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 rounded-xl mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="#DC2626" strokeWidth="1.5"/>
              <line x1="8" y1="5" x2="8" y2="9" stroke="#DC2626" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="8" cy="11" r="0.8" fill="#DC2626"/>
            </svg>
            <p className="text-xs text-destructive font-medium">{errorKey && ERROR_TRANSLATIONS[errorKey] ? t(ERROR_TRANSLATIONS[errorKey]) : t('otp.incorrect')}</p>
          </div>
        )}

        {resent && (
          <div className="flex items-center gap-2 p-3 bg-green-50 rounded-xl mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" fill="#16A34A"/>
              <path d="M5 8L7 10L11 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p className="text-xs text-success font-medium">{t('otp.resent')}</p>
          </div>
        )}

        <div className="mt-2">
          {timer > 0 ? (
            <p className="text-sm text-muted-foreground">
              {t('otp.resendIn')} <span className="font-semibold text-foreground tabular-nums">{timer}s</span>
            </p>
          ) : (
            <button onClick={handleResend} className="text-sm font-semibold text-primary">
              {t('otp.resend')}
            </button>
          )}
        </div>
      </div>

      <div className="px-6 pb-8">
        <Button fullWidth size="lg" disabled={!filled} loading={loading} onClick={handleVerify}>
          {t('otp.verify')}
        </Button>
      </div>
    </div>
  )
}

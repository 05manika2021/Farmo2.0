'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useT } from '@/hooks/useT'

export default function RootPage() {
  const router = useRouter()
  const t = useT()

  useEffect(() => {
    const t2 = setTimeout(() => router.push('/language'), 2200)
    return () => clearTimeout(t2)
  }, [router])

  return (
    <div className="flex flex-col items-center justify-center min-h-full bg-primary screen-enter">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
            <circle cx="40" cy="40" r="40" fill="rgba(255,255,255,0.08)"/>
            <line x1="40" y1="64" x2="40" y2="18" stroke="#CFD050" strokeWidth="3" strokeLinecap="round"/>
            <ellipse cx="30" cy="30" rx="8" ry="5" fill="#CFD050" opacity="0.9" transform="rotate(-30 30 30)"/>
            <ellipse cx="26" cy="42" rx="8" ry="5" fill="#CFD050" opacity="0.75" transform="rotate(-20 26 42)"/>
            <ellipse cx="28" cy="54" rx="7" ry="4.5" fill="#CFD050" opacity="0.6" transform="rotate(-15 28 54)"/>
            <ellipse cx="50" cy="30" rx="8" ry="5" fill="white" opacity="0.9" transform="rotate(30 50 30)"/>
            <ellipse cx="54" cy="42" rx="8" ry="5" fill="white" opacity="0.75" transform="rotate(20 54 42)"/>
            <ellipse cx="52" cy="54" rx="7" ry="4.5" fill="white" opacity="0.6" transform="rotate(15 52 54)"/>
            <ellipse cx="40" cy="20" rx="5" ry="8" fill="#CFD050"/>
          </svg>
        </div>
        <div className="text-center">
          <h1 className="text-5xl font-black text-white tracking-tight">{t('app.name')}</h1>
          <p className="text-secondary font-medium text-base mt-1 tracking-wide">{t('app.taglineHi')}</p>
        </div>
        <p className="text-white/60 text-sm font-medium text-center px-8 mt-2">
          {t('app.tagline')}
        </p>
      </div>
      <div className="absolute bottom-20 flex gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-white/40"
            style={{
              animation: `pulse-ring 1.2s ${i * 0.2}s ease-in-out infinite`,
              background: i === 0 ? '#CFD050' : 'rgba(255,255,255,0.3)',
            }}
          />
        ))}
      </div>
      <p className="absolute bottom-10 text-white/30 text-xs">{t('app.taglineHi')}</p>
    </div>
  )
}

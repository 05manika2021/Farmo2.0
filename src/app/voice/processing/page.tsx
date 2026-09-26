'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useApp } from '@/contexts/AppContext'
import { voicePipeline } from '@/lib/api'
import { useT } from '@/hooks/useT'

export default function VoiceProcessingPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [error, setError] = useState(false)

  useEffect(() => {
    const audioBase64 = sessionStorage.getItem('farmo_voice_audio')
    const audioMime = sessionStorage.getItem('farmo_voice_audio_mime') || 'audio/webm'

    if (!audioBase64) {
      router.replace('/voice/listening')
      return
    }

    let cancelled = false

    async function run() {
      try {
        const byteString = atob(audioBase64!)
        const ab = new ArrayBuffer(byteString.length)
        const ia = new Uint8Array(ab)
        for (let i = 0; i < byteString.length; i++) {
          ia[i] = byteString.charCodeAt(i)
        }
        const audioBlob = new Blob([ab], { type: audioMime })
        const audioFile = new File([audioBlob], 'recording.webm', { type: audioMime })

        const formData = new FormData()
        formData.append('audio', audioFile)
        if (state.language) formData.append('language', state.language)
        if (state.farmerId) formData.append('farmer_id', String(state.farmerId))
        if (state.latitude) formData.append('latitude', String(state.latitude))
        if (state.longitude) formData.append('longitude', String(state.longitude))
        if (state.crops[0]) formData.append('crop', state.crops[0])

        const result = await voicePipeline(formData)

        if (cancelled) return

        if (!result) {
          setError(true)
          setTimeout(() => router.replace('/voice/listening'), 1500)
          return
        }

        sessionStorage.setItem('farmo_voice_result', JSON.stringify(result))
        router.push('/voice/transcript')
      } catch {
        if (!cancelled) {
          setError(true)
          setTimeout(() => router.replace('/voice/listening'), 1500)
        }
      }
    }

    run()

    return () => { cancelled = true }
  }, [router, state, t])

  return (
    <div className="flex flex-col items-center justify-center min-h-full bg-primary screen-enter px-6">
      <div className="relative w-32 h-32 mb-8">
        <svg className="absolute inset-0 spinner" width="128" height="128" viewBox="0 0 128 128">
          <circle cx="64" cy="64" r="56" stroke="#CFD050" strokeWidth="4" strokeLinecap="round"
            strokeDasharray="88 264" fill="none"/>
        </svg>
        <div className="absolute inset-4 bg-white/10 rounded-full flex items-center justify-center">
          <svg width="44" height="44" viewBox="0 0 36 36" fill="none">
            <rect x="12" y="2" width="12" height="20" rx="6" fill="white"/>
            <path d="M6 17C6 23.627 11.373 29 18 29C24.627 29 30 23.627 30 17"
              stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
            <line x1="18" y1="29" x2="18" y2="34" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
        </div>
      </div>

      <h2 className="text-xl font-bold text-white mb-2">{error ? t('voice.somethingWrong') : t('voice.processing')}</h2>
      <p className="text-white/60 text-sm text-center mb-8">
        {error ? t('voice.redirecting') : t('voice.understanding')}
      </p>

      {!error && (
        <div className="w-full space-y-3">
          {[
            { label: t('voice.stepVoiceRecognized'), done: true },
            { label: t('voice.stepFetchingPrices'), done: true },
            { label: t('voice.stepCalculating'), done: false },
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5 bg-white/5 rounded-2xl">
              {step.done ? (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="10" fill="#CFD050"/>
                  <path d="M6 10L8.5 12.5L14 7" stroke="#001913" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ) : (
                <svg className="spinner" width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="8" stroke="white" strokeWidth="2" strokeLinecap="round"
                    strokeDasharray="15 35" fill="none"/>
                </svg>
              )}
              <span className={`text-sm font-medium ${step.done ? 'text-white' : 'text-white/60'}`}>{step.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

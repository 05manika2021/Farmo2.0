'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useT } from '@/hooks/useT'

interface PipelineResult {
  transcribed_text: string
  answer_text: string
  answer_audio_base64?: string
  answer_audio_format?: string
  language?: string
  intent?: string
  context_used?: string
  data_status?: string
  stt_provider?: string
  tts_provider?: string
  gemini_source?: string
  stt_error?: string
  tts_error?: string
  success?: boolean
  error_code?: string
  error_message?: string
}

export default function VoiceResponsePage() {
  const router = useRouter()
  const t = useT()
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<PipelineResult | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const raw = sessionStorage.getItem('farmo_voice_result')
    if (!raw) {
      router.replace('/voice/listening')
      return
    }
    try {
      const parsed: PipelineResult = JSON.parse(raw)
      setResult(parsed)
    } catch {
      router.replace('/voice/listening')
    }
  }, [router])

  const togglePlay = useCallback(() => {
    if (!result?.answer_audio_base64) return

    if (playing) {
      audioRef.current?.pause()
      if (intervalRef.current) clearInterval(intervalRef.current)
      setPlaying(false)
      return
    }

    if (!audioRef.current) {
      const byteString = atob(result.answer_audio_base64)
      const ab = new ArrayBuffer(byteString.length)
      const ia = new Uint8Array(ab)
      for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i)
      }
      const rawFormat = result.answer_audio_format || 'mp3'
      const MIME_TYPES: Record<string, string> = {
        mp3: 'audio/mpeg',
        wav: 'audio/wav',
        m4a: 'audio/mp4',
        webm: 'audio/webm',
        ogg: 'audio/ogg',
      }
      const format = MIME_TYPES[rawFormat.toLowerCase()] ||
        (rawFormat.startsWith('audio/') ? rawFormat : 'audio/mpeg')
      const blob = new Blob([ab], { type: format })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio

      audio.onended = () => {
        setPlaying(false)
        setProgress(0)
        if (intervalRef.current) clearInterval(intervalRef.current)
      }
    }

    audioRef.current.currentTime = 0
    audioRef.current.play().then(() => {
      setPlaying(true)
      const duration = audioRef.current?.duration || 42
      setProgress(0)
      intervalRef.current = setInterval(() => {
        const current = audioRef.current?.currentTime || 0
        setProgress((current / duration) * 100)
      }, 200)
    }).catch(() => {})
  }, [playing, result])

  useEffect(() => {
    return () => {
      audioRef.current?.pause()
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  const formatTime = (pct: number, duration: number) => {
    const seconds = Math.floor((pct / 100) * duration)
    return `0:${String(Math.min(seconds, duration)).padStart(2, '0')}`
  }

  const hasAudio = !!result?.answer_audio_base64

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('voice.farmoAnswer')} onBack={() => router.push('/home')} />

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-4">
        <div className="bg-primary rounded-2xl p-4 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 2H5V12H2V2ZM9 2H12V12H9V2Z" fill="#001913"/>
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{t('voice.farmoVoiceReply')}</p>
              <p className="text-xs text-white/50">
                {hasAudio ? '0:42' : t('voice.noAudio')} · {result?.language || '—'}
              </p>
            </div>
            <button className="ml-auto p-2 rounded-full hover:bg-white/10 transition-colors">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 2C8 2 12 4 12 8C12 12 8 14 8 14" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M8 5C8 5 10 6.5 10 8C10 9.5 8 11 8 11" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={togglePlay}
              disabled={!hasAudio}
              className={`w-12 h-12 rounded-full bg-secondary flex items-center justify-center shrink-0 active:scale-95 transition-transform ${hasAudio ? '' : 'opacity-40'}`}
            >
              {playing ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <rect x="3" y="2" width="4" height="12" rx="1.5" fill="#001913"/>
                  <rect x="9" y="2" width="4" height="12" rx="1.5" fill="#001913"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M4 2L14 8L4 14V2Z" fill="#001913"/>
                </svg>
              )}
            </button>
            <div className="flex-1">
              <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                <div className="h-full bg-secondary rounded-full transition-all" style={{ width: `${progress}%` }} />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[10px] text-white/40 tabular-nums">{formatTime(progress, 42)}</span>
                <span className="text-[10px] text-white/40">0:42</span>
              </div>
            </div>
          </div>
        </div>

        {(result?.tts_error || !hasAudio) && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-3 mb-4">
            <p className="text-xs text-amber-700 font-semibold leading-relaxed">
              {t('voice.ttsUnavailable')}
            </p>
          </div>
        )}

        <div className="bg-card rounded-2xl border border-border p-4 mb-4">
          <div className="flex items-start gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">F</span>
            </div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-muted-foreground mb-1">{t('voice.farmoSays')}</p>
              <p className="text-sm text-foreground leading-relaxed">
                {result?.answer_text || t('voice.noAnswer')}
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-2 mb-4 flex-wrap">
          {result?.data_status && (
            <span className={`text-xs font-semibold px-3 py-1.5 rounded-full ${
              result.data_status === 'LIVE' ? 'bg-green-500/20 text-green-700' : 'bg-yellow-500/20 text-yellow-700'
            }`}>
              {result.data_status}
            </span>
          )}
          {result?.intent && (
            <span className="text-xs font-semibold bg-secondary/10 text-secondary-foreground px-3 py-1.5 rounded-full">
              {result.intent}
            </span>
          )}
          {result?.context_used && (
            <span className="text-xs font-semibold bg-muted text-muted-foreground px-3 py-1.5 rounded-full">
              {t('voice.context')}: {result.context_used}
            </span>
          )}
        </div>

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => router.push('/comparison')}
            className="flex-1 h-12 bg-muted rounded-2xl text-xs font-semibold text-foreground flex items-center justify-center gap-1.5 border border-border"
          >
            {t('voice.compareMarkets')}
          </button>
          <button
            onClick={() => router.push('/recommendation')}
            className="flex-1 h-12 bg-secondary rounded-2xl text-xs font-bold text-secondary-foreground flex items-center justify-center gap-1.5"
          >
            {t('voice.recommendation')}
          </button>
        </div>

        <div className="mt-4">
          <p className="text-xs text-muted-foreground mb-2 px-1">{t('voice.askFollowUp')}</p>
          <div className="flex flex-wrap gap-2">
            {[t('home.speakPrompt'), t('home.checkPrice'), t('home.compareMarkets')].map((q) => (
              <button
                key={q}
                onClick={() => router.push('/chat')}
                className="text-xs font-medium text-primary bg-primary/8 border border-primary/20 px-3 py-2 rounded-xl"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

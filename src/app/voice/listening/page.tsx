'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import MicButton from '@/components/MicButton'
import { useT } from '@/hooks/useT'

type RecordingState = 'IDLE' | 'RECORDING' | 'ERROR'

// Never let the screen sit in "listening" forever: if the mic does not open
// in time, or the farmer never taps stop, fall back instead of hanging.
const MIC_START_TIMEOUT_MS = 15000
const MAX_RECORDING_SECONDS = 30

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const result = reader.result as string
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

export default function VoiceListeningPage() {
  const router = useRouter()
  const t = useT()
  const [hintIdx, setHintIdx] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [recordingState, setRecordingState] = useState<RecordingState>('IDLE')
  const [micError, setMicError] = useState<string | null>(null)
  const [micTimedOut, setMicTimedOut] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  const HINTS = [
    t('voice.trySellWhere'),
    t('voice.trySellWait'),
    t('voice.tryNetValue'),
  ]

  useEffect(() => {
    const t2 = setInterval(() => {
      setHintIdx((i) => (i + 1) % HINTS.length)
    }, 2500)
    return () => clearInterval(t2)
  }, [HINTS.length])

  useEffect(() => {
    if (recordingState !== 'RECORDING') return
    const t2 = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t2)
  }, [recordingState])

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === 'inactive') return

    recorder.onstop = async () => {
      try {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        const base64 = await blobToBase64(blob)
        sessionStorage.setItem('farmo_voice_audio', base64)
        sessionStorage.setItem('farmo_voice_audio_mime', blob.type)
      } catch {
        // Nothing usable was captured - send the farmer back to retry rather
        // than leaving them on a screen that will never move.
        router.replace('/voice/listening')
        return
      }

      streamRef.current?.getTracks().forEach((tr) => tr.stop())
      mediaRecorderRef.current = null
      streamRef.current = null

      router.push('/voice/processing')
    }

    recorder.stop()
  }, [router])

  // Auto-stop so the screen cannot stay on "listening" indefinitely.
  useEffect(() => {
    if (recordingState !== 'RECORDING') return
    if (elapsed < MAX_RECORDING_SECONDS) return
    const t2 = setTimeout(() => stopRecording(), 0)
    return () => clearTimeout(t2)
  }, [elapsed, recordingState, stopRecording])

  const startRecording = useCallback(async () => {
    setMicError(null)
    setMicTimedOut(false)

    let timedOut = false
    const mediaPromise = navigator.mediaDevices.getUserMedia({ audio: true })
    // If we give up waiting, release the stream if it arrives later, and make
    // sure a late rejection never becomes an unhandled promise.
    mediaPromise.then(
      (stream) => {
        if (timedOut) stream.getTracks().forEach((tr) => tr.stop())
      },
      () => {}
    )

    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => {
        timedOut = true
        reject(new Error('mic-start-timeout'))
      }, MIC_START_TIMEOUT_MS)
    )

    let stream: MediaStream
    try {
      stream = await Promise.race([mediaPromise, timeoutPromise])
    } catch {
      setMicTimedOut(timedOut)
      setMicError(timedOut ? t('voice.micTimeoutDesc') : t('voice.micDeniedDesc'))
      setRecordingState('ERROR')
      return
    }

    try {
      streamRef.current = stream
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mediaRecorder.onerror = () => {
        setMicTimedOut(true)
        setMicError(t('voice.micTimeoutDesc'))
        setRecordingState('ERROR')
      }

      mediaRecorder.start()
      setRecordingState('RECORDING')
    } catch {
      stream.getTracks().forEach((tr) => tr.stop())
      setMicTimedOut(true)
      setMicError(t('voice.micTimeoutDesc'))
      setRecordingState('ERROR')
    }
  }, [t])

  useEffect(() => {
    startRecording()
    return () => {
      streamRef.current?.getTracks().forEach((tr) => tr.stop())
      mediaRecorderRef.current = null
      streamRef.current = null
    }
  }, [startRecording])

  const handleStop = () => {
    if (recordingState === 'RECORDING') stopRecording()
  }

  return (
    <div className="flex flex-col min-h-full bg-primary screen-enter">
      <div className="flex items-center justify-between px-5 pt-14 pb-4">
        <button
          onClick={() => router.push('/home')}
          className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M15 10H5M5 10L10 5M5 10L10 15" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse"/>
          <span className="text-white/80 text-sm font-semibold tabular-nums">
            {String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')}
          </span>
        </div>
        <button
          onClick={handleStop}
          className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="3" y="3" width="10" height="10" rx="2" fill="white"/>
          </svg>
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6">
        {micError ? (
          <>
            <div className="w-20 h-20 rounded-full bg-red-500/20 flex items-center justify-center mb-6">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="text-white text-base font-semibold text-center mb-2">
              {micTimedOut ? t('voice.micTimeout') : t('voice.micDenied')}
            </p>
            <p className="text-white/60 text-sm text-center mb-8">{micError}</p>
            <div className="w-full max-w-xs space-y-3">
              <button
                onClick={() => {
                  setRecordingState('IDLE')
                  setElapsed(0)
                  startRecording()
                }}
                className="w-full px-8 py-3 bg-secondary rounded-2xl text-primary font-bold text-sm active:scale-95 transition-transform"
              >
                {t('voice.tryAgain')}
              </button>
              <button
                onClick={() => router.push('/home')}
                className="w-full px-8 py-3 bg-white/10 rounded-2xl text-white font-semibold text-sm"
              >
                {t('voice.goBack')}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-10 h-16">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className={`wave-bar wave-bar-${i + 1}`} style={{ minHeight: 6 }} />
              ))}
            </div>

            <MicButton size="xl" listening onClick={handleStop} />

            <p className="text-white/60 text-sm mt-6 font-medium">
              {recordingState === 'RECORDING' ? t('voice.listening') : t('voice.starting')}
            </p>
            <p className="text-secondary text-base font-semibold mt-2 text-center px-8 min-h-[48px] transition-all">
              &ldquo;{HINTS[hintIdx]}&rdquo;
            </p>
          </>
        )}
      </div>

      <div className="px-6 pb-10">
        <p className="text-white/40 text-xs text-center">
          {t('voice.tapToStop')}
        </p>
        <div className="mt-4 p-4 bg-white/5 rounded-2xl">
          <p className="text-xs text-white/50 text-center mb-2 font-semibold">{t('voice.trySaying')}</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {['गेहूं का भाव', 'Best mandi today', 'Sell or wait?'].map((s) => (
              <span key={s} className="text-xs text-white/70 bg-white/10 px-3 py-1.5 rounded-full font-medium">
                {s}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

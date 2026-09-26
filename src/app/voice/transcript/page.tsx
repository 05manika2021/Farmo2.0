'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import Button from '@/components/Button'
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
}

export default function VoiceTranscriptPage() {
  const router = useRouter()
  const t = useT()
  const [transcript, setTranscript] = useState('')
  const [editing, setEditing] = useState(false)
  const [intent, setIntent] = useState('')

  useEffect(() => {
    const raw = sessionStorage.getItem('farmo_voice_result')
    if (!raw) {
      router.replace('/voice/listening')
      return
    }
    try {
      const result: PipelineResult = JSON.parse(raw)
      setTranscript(result.transcribed_text || '')
      setIntent(result.intent || '')
    } catch {
      router.replace('/voice/listening')
    }
  }, [router])

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('voice.confirmQuestion')} onBack={() => router.push('/voice/listening')} />

      <div className="flex-1 px-5 pt-4">
        <div className="bg-primary rounded-2xl p-5 mb-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-secondary"/>
            <span className="text-white/60 text-xs font-medium">{t('voice.yourVoiceMessage')}</span>
            <span className="ml-auto text-white/50 text-xs">0:03</span>
          </div>
          <div className="flex items-center gap-1.5 h-8">
            {[4, 8, 14, 20, 12, 18, 24, 10, 16, 22, 8, 12, 18, 6, 14].map((h, i) => (
              <div
                key={i}
                className="bg-secondary/60 rounded-full"
                style={{ width: 3, height: h, minHeight: 4 }}
              />
            ))}
          </div>
          <div className="flex items-center gap-3 mt-3">
            <button className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M5 3L13 8L5 13V3Z" fill="#001913"/>
              </svg>
            </button>
            <div className="flex-1 h-1 bg-white/20 rounded-full">
              <div className="w-1/3 h-full bg-secondary rounded-full"/>
            </div>
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{t('voice.whatWeHeard')}</p>
            <button
              onClick={() => setEditing(!editing)}
              className="text-xs font-semibold text-primary"
            >
              {editing ? t('voice.done') : t('voice.edit')}
            </button>
          </div>
          {editing ? (
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              className="w-full p-4 rounded-2xl border-2 border-primary bg-card text-base text-foreground font-medium outline-none resize-none leading-relaxed"
              rows={3}
            />
          ) : (
            <div className="p-4 bg-muted rounded-2xl border border-border">
              <p className="text-base text-foreground font-medium leading-relaxed">&ldquo;{transcript}&rdquo;</p>
            </div>
          )}
        </div>

        {intent && (
          <div className="p-4 bg-secondary/10 rounded-2xl border border-secondary/30">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{t('voice.detectedIntent')}</p>
            <div className="flex flex-wrap gap-2">
              {intent.split(',').map((tag) => (
                <span key={tag.trim()} className="text-xs font-semibold bg-secondary text-secondary-foreground px-3 py-1.5 rounded-full">
                  {tag.trim()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="px-5 pb-8 pt-4 space-y-3">
        <Button fullWidth size="lg" onClick={() => router.push('/voice/response')}>
          {t('voice.yesGetAnswer')}
        </Button>
        <Button fullWidth size="lg" variant="ghost" onClick={() => router.push('/voice/listening')}>
          {t('voice.rerecord')}
        </Button>
      </div>
    </div>
  )
}

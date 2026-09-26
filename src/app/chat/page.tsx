'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import PriceCard from '@/components/PriceCard'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { chat } from '@/lib/api'
import { useT } from '@/hooks/useT'

type Message = {
  id: number
  from: 'user' | 'farmo'
  text?: string
  card?: boolean
  timestamp: string
  data_status?: 'DEMO' | 'LIVE'
}

const INITIAL: Message[] = [
  {
    id: 1,
    from: 'farmo',
    text: 'Hello! I can help you with mandi prices, profit calculations, and sell timing.',
    timestamp: '9:14 AM',
  },
]

const SUGGESTION_KEYS = [
  'chat.suggestPrice',
  'chat.suggestMarket',
  'chat.suggestSellWait',
  'chat.suggestTrend',
  'chat.suggestTransport',
]

let msgId = 10

export default function ChatPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [messages, setMessages] = useState<Message[]>(() => [
    { ...INITIAL[0], text: t('chat.initialMessage') },
  ])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  const sendMessage = async (text: string) => {
    if (!text.trim()) return
    const userMsg: Message = { id: msgId++, from: 'user', text, timestamp: 'Now' }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setTyping(true)

    try {
      const res = await chat({
        message: text,
        language: state.language,
        farmer_id: state.farmerId ?? undefined,
        crop: state.crops[0],
        quantity: state.quantity,
        latitude: state.latitude ?? undefined,
        longitude: state.longitude ?? undefined,
      }) as { answer: string; data_status?: string } | null
      setTyping(false)
      if (res && res.answer) {
        setMessages((m) => [
          ...m,
          {
            id: msgId++,
            from: 'farmo',
            text: res.answer,
            timestamp: 'Now',
            data_status: res.data_status === 'LIVE' || res.data_status === 'DEMO'
              ? res.data_status
              : undefined,
          },
        ])
      } else {
        setMessages((m) => [
          ...m,
          {
            id: msgId++,
            from: 'farmo',
            text: t('chat.error'),
            timestamp: 'Now',
          },
        ])
      }
    } catch {
      setTyping(false)
      setMessages((m) => [
        ...m,
        {
          id: msgId++,
          from: 'farmo',
          text: t('chat.error'),
          timestamp: 'Now',
        },
      ])
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar
        title={t('chat.title')}
        onBack={() => router.push('/home')}
        right={<div className="w-2 h-2 rounded-full bg-success"/>}
      />

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 py-2 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'} gap-2`}>
            {msg.from === 'farmo' && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 mt-1">
                <span className="text-white text-xs font-bold">F</span>
              </div>
            )}
            <div className={`max-w-[80%] space-y-2 ${msg.from === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              {msg.text && (
                <div className="relative">
                  <div
                    className={`relative px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                      msg.from === 'user'
                        ? 'bubble-sent bg-primary text-white rounded-br-sm'
                        : 'bubble-recv bg-muted text-foreground rounded-bl-sm'
                    }`}
                  >
                    {msg.text}
                  </div>
                  {msg.data_status && (
                    <span className={`absolute -top-2 text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                      msg.data_status === 'LIVE'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}>
                      {msg.data_status}
                    </span>
                  )}
                </div>
              )}
              {msg.card && (
                <PriceCard
                  crop="Wheat · गेहूं"
                  cropIcon="🌾"
                  market="Hisar Mandi"
                  distance="42 km"
                  pricePerQtl={2180}
                  transportCost={1380}
                  netProfit={24800}
                  badge="best"
                  trend="up"
                  compact
                  onClick={() => router.push('/mandi')}
                />
              )}
              <span className="text-[10px] text-muted-foreground px-1">{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {typing && (
          <div className="flex gap-2 items-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">F</span>
            </div>
            <div className="bg-muted px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1 items-center">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-muted-foreground"
                  style={{ animation: `wave-a 0.8s ${i * 0.2}s ease-in-out infinite` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-2">
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {SUGGESTION_KEYS.map((key) => {
            const s = t(key)
            return (
              <button
                key={key}
                onClick={() => sendMessage(s)}
                className="shrink-0 text-xs font-semibold text-primary bg-primary/8 border border-primary/20 px-3 py-2 rounded-xl whitespace-nowrap"
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-border">
        <div className="flex items-center gap-2 bg-muted rounded-2xl border border-border px-3 py-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(input) }}
            placeholder={t('chat.placeholder')}
            className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
          />
          <button
            onClick={() => router.push('/voice/listening')}
            className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shrink-0"
          >
            <svg width="18" height="18" viewBox="0 0 36 36" fill="none">
              <rect x="12" y="2" width="12" height="20" rx="6" fill="white"/>
              <path d="M6 17C6 23.627 11.373 29 18 29C24.627 29 30 23.627 30 17"
                stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
          </button>
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim()}
            className="w-9 h-9 rounded-xl bg-secondary flex items-center justify-center shrink-0 disabled:opacity-40"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8L14 2L8 14L7 9L2 8Z" fill="#001913"/>
            </svg>
          </button>
        </div>
      </div>

      <BottomNav active="chat" />
    </div>
  )
}

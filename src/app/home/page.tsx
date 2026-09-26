'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import MicButton from '@/components/MicButton'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { getCurrentPrices, calculateProfit } from '@/lib/api'
import { useT } from '@/hooks/useT'

interface PriceItem {
  market_id: number
  market_name: string
  crop_name: string
  price_per_quintal: number
  data_status: string
  distance_km?: number
}

interface ProfitMarket {
  market_id: number
  market_name: string
  price_per_quintal: number
  distance_km: number
  transport_cost: number
  gross_revenue: number
  net_profit: number
  data_status: string
}

export default function HomePage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()

  const [prices, setPrices] = useState<PriceItem[]>([])
  const [profitMarkets, setProfitMarkets] = useState<ProfitMarket[]>([])
  const [loadingPrices, setLoadingPrices] = useState(true)
  const [loadingProfit, setLoadingProfit] = useState(true)

  const lat = state.latitude ?? 22.7196
  const lon = state.longitude ?? 75.8577
  const crop = state.crops?.[0] ?? 'Wheat'

  useEffect(() => {
    let cancelled = false
    setLoadingPrices(true)
    getCurrentPrices(crop, undefined, lat, lon)
      .then((res: any) => {
        if (cancelled) return
        if (res?.prices && Array.isArray(res.prices)) {
          setPrices(res.prices as PriceItem[])
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingPrices(false) })
    return () => { cancelled = true }
  }, [crop, lat, lon])

  useEffect(() => {
    let cancelled = false
    setLoadingProfit(true)
    calculateProfit({ crop, quantity: state.quantity, farmer_latitude: lat, farmer_longitude: lon })
      .then((res: any) => {
        if (cancelled) return
        if (res?.markets && Array.isArray(res.markets)) {
          setProfitMarkets(res.markets as ProfitMarket[])
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingProfit(false) })
    return () => { cancelled = true }
  }, [crop, lat, lon, state.quantity])

  const bestMarket = profitMarkets.length > 0
    ? profitMarkets.reduce((best, m) => m.net_profit > best.net_profit ? m : best, profitMarkets[0])
    : null

  const CORE_ACTIONS = [
    {
      id: 'mandi',
      icon: '₹',
      title: t('home.checkPrice'),
      desc: bestMarket
        ? `${crop} · ${bestMarket.market_name} · Today`
        : `${crop} · ${t('home.fetchingData')}`,
      highlight: loadingProfit ? '...' : bestMarket ? `₹${bestMarket.net_profit.toLocaleString('en-IN')}` : '—',
      highlightLabel: t('home.netProfitAcre'),
      href: '/mandi',
      bg: '#18594B',
      fg: 'white',
    },
    {
      id: 'comparison',
      icon: '⚖',
      title: t('home.compareMarkets'),
      desc: loadingProfit
        ? t('home.loading')
        : profitMarkets.length > 0
          ? `${profitMarkets.length} ${t('home.mandisCompared')}`
          : t('home.noData'),
      highlight: bestMarket ? bestMarket.market_name : '—',
      highlightLabel: t('comparison.bestOption'),
      href: '/comparison',
      bg: '#CFD050',
      fg: '#001913',
    },
    {
      id: 'chat',
      icon: '🤖',
      title: t('home.askFarmo'),
      desc: t('home.voiceText'),
      highlight: t('home.ai'),
      highlightLabel: t('home.powered'),
      href: '/chat',
      bg: '#F0F5F2',
      fg: '#001913',
    },
  ]

  const COMING_SOON = [
    { icon: '🔔', label: t('home.alerts') },
    { icon: '📋', label: t('home.schemes') },
    { icon: '🚛', label: t('home.logistics') },
    { icon: '🤝', label: t('home.buyers') },
  ]

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <div className="bg-primary px-5 pt-12 pb-5">
        <div className="flex items-center justify-between mb-1">
          <div>
            <p className="text-white/60 text-xs font-medium">{t('home.greeting')}</p>
            <h1 className="text-xl font-bold text-white">{state.name || t('home.farmer')} 👋</h1>
          </div>
          <button onClick={() => router.push('/settings')} className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="5.5" r="3" stroke="white" strokeWidth="1.6"/>
              <path d="M2 16C2 12.686 5.134 10 9 10C12.866 10 16 12.686 16 16" stroke="white" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1C3.8 1 2 2.8 2 5C2 8 6 11 6 11C6 11 10 8 10 5C10 2.8 8.2 1 6 1Z" fill="#CFD050"/>
            <circle cx="6" cy="5" r="1.5" fill="#18594B"/>
          </svg>
          <span className="text-white/70 text-xs font-medium">{state.villageName || t('home.yourLocation')}</span>
          <span className="text-secondary text-xs font-semibold">· {loadingPrices ? t('home.loading') : t('home.live')}</span>
        </div>
      </div>

      <div className="flex flex-col items-center py-6 bg-primary">
        <p className="text-white/60 text-xs font-medium mb-3 tracking-wide uppercase">{t('home.tapToSpeak')}</p>
        <MicButton size="xl" onClick={() => router.push('/voice/listening')} />
        <p className="text-white/50 text-xs mt-3">{t('home.speakPrompt')}</p>
      </div>

      <div className="h-3 bg-primary relative">
        <div className="absolute bottom-0 left-0 right-0 h-3 bg-background rounded-t-[24px]" />
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pt-1 pb-4">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3 px-1">{t('home.coreTools')}</p>
        <div className="space-y-3">
          {CORE_ACTIONS.map((action) => (
            <button
              key={action.id}
              onClick={() => router.push(action.href)}
              className="w-full rounded-2xl p-4 flex items-center gap-4 active:scale-[0.98] transition-transform shadow-sm border border-border"
              style={{ background: action.bg }}
            >
              <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl bg-black/5 shrink-0">
                {action.icon}
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-bold leading-tight" style={{ color: action.fg }}>{action.title}</p>
                <p className="text-xs mt-0.5" style={{ color: action.fg, opacity: 0.65 }}>{action.desc}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-lg font-black" style={{ color: action.fg }}>{action.highlight}</p>
                <p className="text-[10px]" style={{ color: action.fg, opacity: 0.65 }}>{action.highlightLabel}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="mt-5">
          <div className="flex items-center justify-between mb-3 px-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{t('home.moreFeatures')}</p>
            <span className="text-[10px] font-bold bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{t('home.comingSoon')}</span>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {COMING_SOON.map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center gap-1.5 p-3 bg-muted rounded-2xl border border-border opacity-60"
              >
                <span className="text-xl">{item.icon}</span>
                <span className="text-[10px] font-semibold text-muted-foreground">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 p-4 bg-primary/5 rounded-2xl border border-primary/15">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold text-primary uppercase tracking-wide">{t('home.todaysPrices')}</p>
            <button onClick={() => router.push('/graph')} className="text-xs font-semibold text-primary">{t('home.viewAll')}</button>
          </div>
          <div className="space-y-2">
            {loadingPrices ? (
              <p className="text-xs text-muted-foreground">{t('home.loadingPrices')}</p>
            ) : prices.length > 0 ? (
              prices.slice(0, 5).map((item) => (
                <div key={item.market_id} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">
                    {item.crop_name} {item.data_status === 'DEMO' && <span className="text-[9px] font-bold bg-muted text-muted-foreground px-1 py-0.5 rounded ml-1">DEMO</span>}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground">₹{item.price_per_quintal.toLocaleString('en-IN')}</span>
                    {item.distance_km != null && (
                      <span className="text-xs text-muted-foreground">{item.distance_km} km</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">{t('home.noPrices')} {crop}</p>
            )}
          </div>
        </div>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

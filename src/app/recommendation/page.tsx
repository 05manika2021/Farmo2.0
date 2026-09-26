'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { sellWait, calculateProfit, getWeather, getPriceTrend, chat } from '@/lib/api'
import { useT } from '@/hooks/useT'

type Verdict = 'sell' | 'wait' | 'sell-elsewhere'

const VERDICT_META: Record<Verdict, {
  emoji: string
  color: string
  bg: string
  border: string
}> = {
  sell: {
    emoji: '✅',
    color: 'text-success',
    bg: 'bg-green-50',
    border: 'border-green-200',
  },
  wait: {
    emoji: '⏳',
    color: 'text-warning',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
  },
  'sell-elsewhere': {
    emoji: '🗺',
    color: 'text-primary',
    bg: 'bg-primary/5',
    border: 'border-primary/20',
  },
}

interface ApiFactor {
  factor: string
  impact: string
  detail: string
}

interface ApiResponse {
  recommendation: string
  reason: string
  factors: ApiFactor[]
  uncertainty: string
  data_status: string
  best_market_name: string
  best_market_net_profit: number
  weather_risk: string
}

interface ProfitMarket {
  market_id: number
  market_name: string
  price_per_quintal: number
  distance_km: number
  transport_cost: number
  gross_revenue: number
  other_costs: number
  net_profit: number
  data_status: string
}

interface WeatherInfo {
  temperature?: number
  condition?: string
  weather_risk?: string
  data_status?: string
  note?: string
}

interface TrendInfo {
  trend?: string
  current_price?: number
  data_status?: string
}

interface AiInfo {
  answer: string
  data_status?: string
}

interface WhyRow {
  icon: string
  tone: string
  label: string
  value: string
  sub?: string
}

export default function RecommendationPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [verdict, setVerdict] = useState<Verdict>('sell')
  const [loading, setLoading] = useState(true)
  const [apiData, setApiData] = useState<ApiResponse | null>(null)
  const [markets, setMarkets] = useState<ProfitMarket[]>([])
  const [weather, setWeather] = useState<WeatherInfo | null>(null)
  const [trend, setTrend] = useState<TrendInfo | null>(null)
  const [ai, setAi] = useState<AiInfo | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState(false)

  const crop = state.crops[0] || 'Wheat'
  const quantity = state.quantity
  const lat = state.latitude ?? 28.4595
  const lon = state.longitude ?? 76.9915
  const village = state.villageName || 'Jaitpur'

  useEffect(() => {
    let cancelled = false

    async function fetchAll() {
      setLoading(true)
      setAi(null)
      setAiError(false)
      setWeather(null)
      setTrend(null)
      setMarkets([])
      setApiData(null)

      const [wRes, pRes] = await Promise.all([
        getWeather(lat, lon).catch(() => null),
        calculateProfit({ crop, quantity, farmer_latitude: lat, farmer_longitude: lon }).catch(() => null),
      ])
      if (cancelled) return

      const w = (wRes ?? null) as WeatherInfo | null
      const p = (pRes ?? null) as { markets?: ProfitMarket[] } | null
      const mkts = Array.isArray(p?.markets) ? p!.markets! : []
      setWeather(w)
      setMarkets(mkts)

      const best = mkts[0]
      const [swRes, trRes] = await Promise.all([
        sellWait({
          crop,
          quantity,
          latitude: lat,
          longitude: lon,
          weather_risk: w?.weather_risk,
        }).catch(() => null),
        best ? getPriceTrend(crop, best.market_id, 30).catch(() => null) : Promise.resolve(null),
      ])
      if (cancelled) return

      if (swRes) {
        const res = swRes as ApiResponse
        setApiData(res)
        if (res.recommendation === 'WAIT') setVerdict('wait')
        else if (res.recommendation === 'SELL_IN_ANOTHER_MARKET') setVerdict('sell-elsewhere')
        else setVerdict('sell')
      }
      setTrend((trRes ?? null) as TrendInfo | null)
      setLoading(false)

      const message = t('recommendation.askMessage')
        .replace('{qty}', String(quantity))
        .replace('{crop}', crop)
      setAiLoading(true)
      const aiRes = (await chat({
        message,
        language: state.language,
        crop,
        quantity,
        latitude: lat,
        longitude: lon,
      }).catch(() => null)) as AiInfo | null
      if (cancelled) return
      setAiLoading(false)
      if (aiRes?.answer) setAi(aiRes)
      else setAiError(true)
    }

    fetchAll()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.crops, state.latitude, state.longitude, state.quantity, state.language])

  const VERDICT_LABELS: Record<Verdict, string> = {
    sell: t('recommendation.sellNow'),
    wait: t('recommendation.waitDays'),
    'sell-elsewhere': t('recommendation.sellOther'),
  }

  const meta = VERDICT_META[verdict]
  const label = verdict === 'sell-elsewhere' && apiData?.best_market_name
    ? `${t('recommendation.sellOther')} ${apiData.best_market_name}`
    : VERDICT_LABELS[verdict]

  const best = markets[0] ?? null

  const trendLabel = !trend?.trend
    ? t('recommendation.unavailable')
    : trend.trend === 'increasing'
      ? t('graph.rising')
      : trend.trend === 'decreasing'
        ? t('graph.falling')
        : t('graph.stable')
  const trendIcon = trend?.trend === 'increasing' ? '📈' : trend?.trend === 'decreasing' ? '📉' : '➡️'

  const risk = weather?.weather_risk
  const weatherUnavailable = !weather || weather.data_status === 'UNAVAILABLE' || !risk || risk === 'unknown'
  const weatherLabel = weatherUnavailable
    ? t('recommendation.unavailable')
    : risk === 'high'
      ? t('recommendation.riskHigh')
      : risk === 'moderate'
        ? t('recommendation.riskModerate')
        : t('recommendation.riskLow')
  const weatherIcon = weatherUnavailable ? '✕' : risk === 'low' ? '✓' : '⚠'

  const topPriceMarket = markets.length > 0
    ? markets.reduce((a, b) => (b.price_per_quintal > a.price_per_quintal ? b : a), markets[0])
    : null
  const alternative = topPriceMarket && best && topPriceMarket.market_id !== best.market_id
    ? topPriceMarket
    : null

  const whyRows: WhyRow[] = []
  if (!loading && best) {
    whyRows.push(
      {
        icon: '✓',
        tone: 'text-success',
        label: t('recommendation.mandiPrice'),
        value: `₹${best.price_per_quintal.toLocaleString('en-IN')}/${t('recommendation.qtl')}`,
        sub: best.market_name,
      },
      {
        icon: '⚠',
        tone: 'text-warning',
        label: t('recommendation.transportCost'),
        value: `− ₹${best.transport_cost.toLocaleString('en-IN')}`,
        sub: t('recommendation.estimateNote'),
      },
      {
        icon: '✓',
        tone: 'text-success',
        label: t('recommendation.expectedNetValue'),
        value: `₹${best.net_profit.toLocaleString('en-IN')}`,
        sub: `${quantity} ${t('recommendation.qtl')}`,
      },
      {
        icon: '✓',
        tone: 'text-success',
        label: t('recommendation.bestMarket'),
        value: best.market_name,
        sub: best.data_status,
      },
      {
        icon: trendIcon,
        tone: trend?.trend === 'increasing' ? 'text-success' : trend?.trend === 'decreasing' ? 'text-destructive' : 'text-muted-foreground',
        label: t('recommendation.priceTrend'),
        value: trendLabel,
        sub: trend?.data_status,
      },
      {
        icon: weatherIcon,
        tone: weatherUnavailable ? 'text-muted-foreground' : risk === 'low' ? 'text-success' : 'text-warning',
        label: t('recommendation.weatherRisk'),
        value: weatherLabel,
        sub: weather?.condition,
      },
    )
    whyRows.push(alternative
      ? {
          icon: '⚠',
          tone: 'text-warning',
          label: t('recommendation.alternativeMarket'),
          value: `${alternative.market_name} · ₹${alternative.price_per_quintal.toLocaleString('en-IN')}`,
          sub: t('recommendation.altHigherPrice'),
        }
      : {
          icon: '✓',
          tone: 'text-success',
          label: t('recommendation.alternativeMarket'),
          value: t('recommendation.noAlternative'),
        })
  }

  const statusBadge = (status?: string) => status ? (
    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold ${
      status === 'LIVE' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
    }`}>
      {status}
    </span>
  ) : null

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('recommendation.title')} onBack={() => router.push('/mandi')} />

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-4">
        <div className="flex items-center gap-3 mb-4 p-3.5 bg-muted rounded-2xl border border-border">
          <span className="text-2xl">🌾</span>
          <div>
            <p className="text-sm font-bold text-foreground">
              {crop} · {quantity} {t('recommendation.qtl')} · {village}
            </p>
            <p className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
              {t('recommendation.basedOn')}
              {statusBadge(apiData?.data_status)}
            </p>
          </div>
        </div>

        <div className="rounded-3xl p-5 mb-5 bg-card border-2 border-primary/20">
          <div className="flex items-center justify-between gap-2 mb-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {t('recommendation.expectedNetValue')}
            </p>
            {!loading && best && statusBadge(best.data_status)}
          </div>

          {loading || !best ? (
            <div className="h-16 bg-muted rounded-xl animate-pulse" />
          ) : (
            <>
              <div className="flex items-end justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-foreground truncate">{best.market_name}</p>
                  <p className="text-xs text-muted-foreground">
                    ₹{best.price_per_quintal.toLocaleString('en-IN')} / {t('recommendation.qtl')}
                  </p>
                </div>
                <p className="text-3xl font-black text-success shrink-0">
                  ₹{best.net_profit.toLocaleString('en-IN')}
                </p>
              </div>

              <div className="mt-3 pt-3 border-t border-border space-y-1.5 text-xs">
                <div className="flex justify-between gap-3">
                  <span className="text-muted-foreground">{t('comparison.mandiPrice')}</span>
                  <span className="font-semibold text-foreground text-right">
                    ₹{best.gross_revenue.toLocaleString('en-IN')}
                    <span className="text-muted-foreground font-normal"> ({quantity} {t('recommendation.qtl')})</span>
                  </span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-muted-foreground">{t('recommendation.transportCost')}</span>
                  <span className="font-semibold text-destructive">− ₹{best.transport_cost.toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-muted-foreground">{t('recommendation.priceTrend')}</span>
                  <span className="font-semibold text-foreground">{trendIcon} {trendLabel}</span>
                </div>
              </div>
              <p className="text-[10px] text-muted-foreground mt-2 leading-snug">
                {t('recommendation.estimateNote')}
              </p>
            </>
          )}
        </div>

        <div className={`rounded-3xl p-6 mb-5 border-2 ${meta.bg} ${meta.border}`}>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{t('recommendation.aiRec')}</p>
          <div className="flex items-center gap-3">
            <span className="text-4xl">{loading ? '🔄' : meta.emoji}</span>
            <div>
              <p className={`text-3xl font-black ${meta.color}`}>{loading ? t('recommendation.analyzing') : label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {loading
                  ? t('recommendation.fetching')
                  : `${t('recommendation.updatedNow')} · ${apiData?.data_status ?? ''}`}
              </p>
            </div>
          </div>
        </div>

        <div className="mb-5 p-4 rounded-2xl bg-primary/5 border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">✨</span>
            <p className="text-xs font-semibold text-foreground uppercase tracking-wide">{t('recommendation.aiExplain')}</p>
          </div>
          {aiLoading ? (
            <div>
              <div className="space-y-2">
                <div className="h-3 bg-muted rounded w-full animate-pulse" />
                <div className="h-3 bg-muted rounded w-4/5 animate-pulse" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">{t('recommendation.aiLoading')}</p>
            </div>
          ) : aiError ? (
            <p className="text-xs text-muted-foreground">{t('recommendation.aiError')}</p>
          ) : ai ? (
            <>
              <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{ai.answer}</p>
              <div className="mt-2">{statusBadge(ai.data_status)}</div>
            </>
          ) : null}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => router.push('/chat')}
              className="flex-1 h-10 rounded-xl text-xs font-semibold bg-primary text-white"
            >
              {t('home.askFarmo')}
            </button>
            <button
              onClick={() => router.push('/voice/listening')}
              className="flex-1 h-10 rounded-xl text-xs font-semibold bg-card border border-border text-foreground"
            >
              🎤 {t('recommendation.hearVoice')}
            </button>
          </div>
        </div>

        <div className="mb-5">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3 px-1">{t('recommendation.why')}</p>
          <div className="space-y-2.5">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-3 items-start p-3.5 bg-card rounded-2xl border border-border animate-pulse">
                  <div className="w-5 h-5 rounded bg-muted shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 bg-muted rounded w-3/4" />
                    <div className="h-3 bg-muted rounded w-1/2" />
                  </div>
                </div>
              ))
            ) : (
              whyRows.map((r, i) => (
                <div key={i} className="flex gap-3 items-start p-3.5 bg-card rounded-2xl border border-border">
                  <span className={`text-sm font-bold shrink-0 ${r.tone}`}>{r.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="text-xs text-muted-foreground">{r.label}</p>
                      <p className="text-sm font-bold text-foreground text-right">{r.value}</p>
                    </div>
                    {r.sub && (
                      <p className="text-[10px] text-muted-foreground leading-snug mt-0.5">{r.sub}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mb-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 px-1">{t('recommendation.exploreOptions')}</p>
          <div className="flex gap-2">
            {(Object.keys(VERDICT_META) as Verdict[]).map((v2) => (
              <button
                key={v2}
                onClick={() => setVerdict(v2)}
                className={`flex-1 py-3 rounded-xl text-xs font-semibold border-2 transition-all text-center ${
                  verdict === v2
                    ? 'bg-foreground text-white border-foreground'
                    : 'bg-card border-border text-foreground'
                }`}
              >
                {VERDICT_META[v2].emoji}<br/>{VERDICT_LABELS[v2].split(' ').slice(0, 2).join(' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 bg-card rounded-2xl border border-border">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">{t('recommendation.marketContext')}</p>
          <div className="grid grid-cols-3 gap-3">
            {[
              {
                label: t('recommendation.bestMarket'),
                value: best?.market_name || '—',
                sub: best?.data_status || '',
              },
              {
                label: t('recommendation.priceTrend'),
                value: loading ? '—' : `${trendIcon} ${trendLabel}`,
                sub: trend?.data_status || '',
              },
              {
                label: t('recommendation.weatherRisk'),
                value: loading ? '—' : weatherLabel,
                sub: weather?.condition || '',
              },
            ].map((stat) => (
              <div key={stat.label} className="text-center p-2.5 bg-muted rounded-xl">
                <p className="text-xs text-muted-foreground mb-1">{stat.label}</p>
                <p className="text-sm font-bold text-foreground break-words">{stat.value}</p>
                <p className="text-[10px] text-muted-foreground">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-border flex gap-3">
        <button
          onClick={() => router.push('/graph')}
          className="flex-1 h-12 bg-muted rounded-2xl text-sm font-semibold text-foreground border border-border"
        >
          📈 {t('recommendation.priceGraph')}
        </button>
        <button
          onClick={() => router.push('/comparison')}
          className="flex-1 h-12 bg-primary rounded-2xl text-sm font-semibold text-white"
        >
          {t('home.compareMarkets')}
        </button>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

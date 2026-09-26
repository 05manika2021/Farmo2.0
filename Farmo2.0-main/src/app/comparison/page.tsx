'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import PriceCard from '@/components/PriceCard'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { compareMarkets } from '@/lib/api'
import { useT } from '@/hooks/useT'

type Sort = 'profit' | 'price' | 'distance'

interface MarketItem {
  market: string
  distance: string
  pricePerQtl: number
  transportCost: number
  netProfit: number
  badge: 'best' | 'good' | null
  trend: 'up' | 'down' | 'stable'
  dataStatus?: string
  marketId?: number
}

export default function ComparisonPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [sort, setSort] = useState<Sort>('profit')
  const [loading, setLoading] = useState(false)
  const [markets, setMarkets] = useState<MarketItem[]>([])
  const [cropName, setCropName] = useState('')
  const quantity = state.quantity
  const [quantityUnit] = useState('quintal')

  const fetchData = useCallback(async () => {
    setLoading(true)
    const crop = state.crops[0] || 'Wheat'
    const lat = state.latitude ?? 22.7196
    const lon = state.longitude ?? 75.8577

    setCropName(crop)

    try {
      const result = await compareMarkets({
        crop,
        quantity,
        quantity_unit: quantityUnit,
        latitude: lat,
        longitude: lon,
      }) as { markets: any[]; recommended_market_id?: number; recommendation_reason?: string } | null

      if (result?.markets) {
        const mapped: MarketItem[] = result.markets.map((m: any) => ({
          market: m.market_name,
          distance: `${m.distance_km} km`,
          pricePerQtl: m.price_per_quintal,
          transportCost: m.transport_cost,
          netProfit: m.net_profit,
          badge: m.market_id === result.recommended_market_id ? 'best' as const : null,
          trend: 'stable' as const,
          dataStatus: m.data_status,
          marketId: m.market_id,
        }))
        setMarkets(mapped)
      }
    } catch (err) {
      console.error('Failed to fetch comparison data:', err)
    } finally {
      setLoading(false)
    }
  }, [state.crops, state.latitude, state.longitude, quantity])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const sorted = [...markets].sort((a, b) => {
    if (sort === 'profit') return b.netProfit - a.netProfit
    if (sort === 'price') return b.pricePerQtl - a.pricePerQtl
    return parseInt(a.distance) - parseInt(b.distance)
  })

  const handleRefresh = () => {
    fetchData()
  }

  const displayCrop = cropName || 'Wheat'
  const money = (n: number) => `₹${n.toLocaleString('en-IN')}`
  const maxNet = markets.length > 0 ? Math.max(...markets.map((m) => m.netProfit)) : null
  const maxPrice = markets.length > 0 ? Math.max(...markets.map((m) => m.pricePerQtl)) : null
  const COLS = 'grid grid-cols-[1.3fr_1fr_1fr_1.2fr] gap-x-2 items-center'

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar
        title={t('comparison.title')}
        onBack={() => router.push('/home')}
        right={
          <button onClick={handleRefresh} className="text-muted-foreground">
            <svg className={loading ? 'spinner' : ''} width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M15 9A6 6 0 1 1 3 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <path d="M15 5V9H11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        }
      />

      <div className="mx-4 mb-3 p-3 bg-primary/5 rounded-2xl border border-primary/15 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🌾</span>
          <div>
            <p className="text-sm font-bold text-foreground">{displayCrop} · {quantity} {quantityUnit}</p>
            <p className="text-xs text-muted-foreground">{sorted.length} {t('comparison.mandisInRange')}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">{t('comparison.bestNetProfit')}</p>
          {sorted.length > 0 ? (
            <p className="text-base font-black text-success">₹{sorted[0].netProfit.toLocaleString('en-IN')}</p>
          ) : (
            <p className="text-base font-black text-success">—</p>
          )}
        </div>
      </div>

      {markets.length > 0 && !loading && (
        <div className="mx-4 mb-3 p-3 bg-card rounded-2xl border border-border">
          <p className="text-[11px] text-muted-foreground mb-2 leading-snug">{t('comparison.priceNote')}</p>
          <div className={`${COLS} text-[10px] font-semibold uppercase tracking-wide text-muted-foreground pb-1.5 border-b border-border`}>
            <span>{t('comparison.market')}</span>
            <span className="text-right">{t('comparison.mandiPrice')}</span>
            <span className="text-right">{t('recommendation.transportCost')}</span>
            <span className="text-right">{t('comparison.afterCosts')}</span>
          </div>
          {sorted.map((m) => {
            const isBestNet = maxNet !== null && m.netProfit === maxNet
            const isTopPrice = maxPrice !== null && m.pricePerQtl === maxPrice
            return (
              <div
                key={`row-${m.market}`}
                className={`${COLS} py-2 border-b border-border/50 last:border-0 ${isBestNet ? 'bg-green-50 -mx-1 px-1 rounded-lg' : ''}`}
              >
                <span className="text-xs font-semibold text-foreground truncate">{m.market}</span>
                <span className={`text-xs text-right ${isTopPrice ? 'font-bold text-foreground' : 'text-muted-foreground'}`}>
                  {money(m.pricePerQtl)}
                  {isTopPrice && !isBestNet && (
                    <span className="block text-[9px] font-semibold text-warning">{t('comparison.highestPrice')}</span>
                  )}
                </span>
                <span className="text-xs text-right text-destructive">−{money(m.transportCost)}</span>
                <span className={`text-xs text-right font-black ${isBestNet ? 'text-success' : 'text-foreground'}`}>
                  {money(m.netProfit)}
                  {isBestNet && (
                    <span className="block text-[9px] font-semibold">✓ {t('price.best')}</span>
                  )}
                </span>
              </div>
            )
          })}
        </div>
      )}

      <div className="px-4 mb-3">
        <div className="flex bg-muted rounded-xl p-1 gap-1">
          {([
            { key: 'profit', label: t('comparison.netProfit') },
            { key: 'price', label: t('comparison.mandiPrice') },
            { key: 'distance', label: t('comparison.nearest') },
          ] as { key: Sort; label: string }[]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSort(tab.key)}
              className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all ${
                sort === tab.key ? 'bg-primary text-white shadow-sm' : 'text-muted-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-4 space-y-3">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-muted rounded-2xl animate-pulse border border-border"/>
          ))
        ) : (
          sorted.map((m, idx) => (
            <div key={m.market}>
              {idx === 0 && sort === 'profit' && (
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-xs font-bold text-success uppercase tracking-wide">🏆 {t('comparison.bestOption')}</span>
                </div>
              )}
              <PriceCard
                crop={displayCrop}
                cropIcon="🌾"
                market={m.market}
                distance={m.distance}
                pricePerQtl={m.pricePerQtl}
                transportCost={m.transportCost}
                netProfit={m.netProfit}
                badge={m.badge}
                trend={m.trend}
                onClick={() => router.push('/mandi')}
              />
            </div>
          ))
        )}

        <p className="text-xs text-muted-foreground text-center pt-2">
          {sorted.length > 0 && sorted[0].dataStatus
            ? `${sorted[0].dataStatus} · ${t('comparison.netProfitFor')} ${quantity} ${quantityUnit}`
            : `${t('comparison.netProfitFor')} ${quantity} ${quantityUnit}`}
        </p>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

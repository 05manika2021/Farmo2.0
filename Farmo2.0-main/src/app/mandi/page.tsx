'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { calculateProfit, getNearbyMarkets } from '@/lib/api'
import { useT } from '@/hooks/useT'

const CROPS = ['Wheat 🌾', 'Cotton 🪡', 'Soybean 🌱', 'Maize 🌽']
const CROP_NAMES = ['wheat', 'cotton', 'soybean', 'maize'] as const
const QTLS = [5, 10, 15, 20, 25]

interface MarketResult {
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

interface NearbyMarket {
  id: number
  name: string
  state: string
  district: string
  latitude: number
  longitude: number
  distance_km: number
}

export default function MandiPage() {
  const router = useRouter()
  const { state, setQuantity } = useApp()
  const t = useT()
  const [crop, setCrop] = useState(0)
  const qty = state.quantity
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)

  const [basePrice, setBasePrice] = useState(0)
  const [transportCost, setTransportCost] = useState(0)
  const [grossRevenue, setGrossRevenue] = useState(0)
  const [netProfit, setNetProfit] = useState(0)
  const [profitPerQtl, setProfitPerQtl] = useState(0)
  const [dataStatus, setDataStatus] = useState('')
  const [nearestMarketName, setNearestMarketName] = useState('Hisar Mandi')
  const [nearestMarketDist, setNearestMarketDist] = useState(42)
  const [arrivalCount, setArrivalCount] = useState('4,200')

  const fetchProfitData = useCallback(async (cropIndex: number, quantity: number) => {
    const lat = state.latitude
    const lon = state.longitude
    if (!lat || !lon) return

    setFetching(true)
    try {
      const result = await calculateProfit({
        crop: CROP_NAMES[cropIndex],
        quantity,
        farmer_latitude: lat,
        farmer_longitude: lon,
      }) as { markets: MarketResult[] } | null

      if (result && result.markets && result.markets.length > 0) {
        const best = result.markets[0]
        setBasePrice(best.price_per_quintal)
        setTransportCost(best.transport_cost)
        setGrossRevenue(best.gross_revenue)
        setNetProfit(best.net_profit)
        setProfitPerQtl(Math.round(best.net_profit / quantity))
        setDataStatus(best.data_status)
      }
    } catch {
      // keep defaults on error
    }
    setFetching(false)
  }, [state.latitude, state.longitude])

  const fetchMarketInfo = useCallback(async (cropIndex: number) => {
    const lat = state.latitude
    const lon = state.longitude
    if (!lat || !lon) return

    try {
      const result = await getNearbyMarkets(lat, lon, undefined, CROP_NAMES[cropIndex]) as { markets: NearbyMarket[] } | null
      if (result && result.markets && result.markets.length > 0) {
        const nearest = result.markets[0]
        setNearestMarketName(nearest.name + ' Mandi')
        setNearestMarketDist(Math.round(nearest.distance_km))
      }
    } catch {
      // keep defaults
    }
  }, [state.latitude, state.longitude])

  useEffect(() => {
    fetchProfitData(crop, qty)
    fetchMarketInfo(crop)
  }, [crop, qty, fetchProfitData, fetchMarketInfo])

  const handleCropChange = (index: number) => {
    setCrop(index)
  }

  const handleQtyChange = (q: number) => {
    setQuantity(q)
  }

  const handleRefresh = () => {
    setLoading(true)
    setFetching(true)
    Promise.all([fetchProfitData(crop, qty), fetchMarketInfo(crop)]).then(() => {
      setLoading(false)
      setFetching(false)
    })
  }

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar
        title={t('mandi.title')}
        onBack={() => router.push('/home')}
        right={
          <button onClick={handleRefresh} className="w-8 h-8 flex items-center justify-center text-muted-foreground">
            <svg className={loading ? 'spinner' : ''} width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M15 9A6 6 0 1 1 3 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              <path d="M15 5V9H11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto no-scrollbar">
        <div className="px-4 mb-4">
          <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
            {CROPS.map((c, i) => (
              <button
                key={c}
                onClick={() => handleCropChange(i)}
                className={`shrink-0 px-4 py-2 rounded-xl text-sm font-semibold border-2 transition-all ${
                  crop === i ? 'bg-primary text-white border-primary' : 'bg-card border-border text-foreground'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        <div className="mx-4 bg-primary rounded-3xl p-6 mb-4">
          <p className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-1">{t('mandi.expectedNetProfit')}</p>
          <div className="flex items-end gap-1 mb-1">
            <span className="text-5xl font-black text-white">
              {fetching ? (
                <span className="text-3xl">...</span>
              ) : (
                `₹${netProfit.toLocaleString('en-IN')}`
              )}
            </span>
          </div>
          <p className="text-secondary text-sm font-semibold">{qty} {t('mandi.quintal')} {CROPS[crop].split(' ')[0]}</p>
          {dataStatus && (
            <span className={`inline-block mt-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
              dataStatus === 'LIVE' ? 'bg-green-500/20 text-green-200' : 'bg-yellow-500/20 text-yellow-200'
            }`}>
              {dataStatus}
            </span>
          )}
          <div className="mt-4 h-px bg-white/10"/>
          <div className="flex justify-between mt-4">
            <div>
              <p className="text-white/50 text-xs">{t('mandi.mandiPrice')}</p>
              <p className="text-white font-bold text-lg">
                {fetching ? '...' : `₹${basePrice.toLocaleString('en-IN')}/qtl`}
              </p>
            </div>
            <div className="text-right">
              <p className="text-white/50 text-xs">{t('mandi.netPerQtl')}</p>
              <p className="text-secondary font-bold text-lg">
                {fetching ? '...' : `₹${profitPerQtl.toLocaleString('en-IN')}`}
              </p>
            </div>
          </div>
        </div>

        <div className="mx-4 mb-4 p-4 bg-card rounded-2xl border border-border">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-foreground">{t('mandi.quantity')}</p>
            <span className="text-sm font-bold text-primary">{qty} {t('mandi.quintal')}</span>
          </div>
          <div className="flex gap-2">
            {QTLS.map((q) => (
              <button
                key={q}
                onClick={() => handleQtyChange(q)}
                className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all ${
                  qty === q ? 'bg-secondary text-secondary-foreground border-secondary' : 'bg-muted border-transparent text-foreground'
                }`}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div className="mx-4 mb-4 p-4 bg-card rounded-2xl border border-border">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">{t('mandi.costBreakdown')}</p>
          <div className="space-y-3">
            {[
              { label: `Mandi Price (₹${basePrice} × ${qty} qtl)`, value: `₹${grossRevenue.toLocaleString('en-IN')}`, positive: true },
              { label: `Transport (₹${qty > 0 ? Math.round(transportCost / qty) : 0} × ${qty} qtl)`, value: `−₹${transportCost.toLocaleString('en-IN')}`, positive: false },
              { label: t('mandi.mandiCommission'), value: `−₹${Math.round(grossRevenue * 0.02).toLocaleString('en-IN')}`, positive: false },
            ].map((row) => (
              <div key={row.label} className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">{row.label}</p>
                <p className={`text-sm font-semibold ${row.positive ? 'text-foreground' : 'text-destructive'}`}>
                  {row.value}
                </p>
              </div>
            ))}
            <div className="h-px bg-border"/>
            <div className="flex justify-between items-center">
              <p className="text-sm font-bold text-foreground">{t('mandi.netProfit')}</p>
              <p className="text-base font-black text-success">₹{netProfit.toLocaleString('en-IN')}</p>
            </div>
          </div>
        </div>

        <div className="mx-4 mb-4 p-4 bg-muted rounded-2xl flex items-center gap-3">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="#18594B" strokeWidth="1.5"/>
            <line x1="10" y1="9" x2="10" y2="14" stroke="#18594B" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="10" cy="6.5" r="0.8" fill="#18594B"/>
          </svg>
          <div>
            <p className="text-xs font-semibold text-foreground">{nearestMarketName} · {nearestMarketDist} km away</p>
            <p className="text-xs text-muted-foreground">Last updated: 9:30 AM · Arrivals: {arrivalCount} bags</p>
          </div>
        </div>

        <div className="mx-4 flex gap-3 mb-4">
          <button
            onClick={() => router.push('/comparison')}
            className="flex-1 h-12 bg-muted rounded-2xl text-xs font-semibold text-foreground border border-border flex items-center justify-center gap-1.5"
          >
            ⚖ {t('mandi.compareMarkets')}
          </button>
          <button
            onClick={() => router.push('/recommendation')}
            className="flex-1 h-12 bg-secondary rounded-2xl text-xs font-bold text-secondary-foreground flex items-center justify-center gap-1.5"
          >
            📋 {t('mandi.sellWait')}
          </button>
        </div>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

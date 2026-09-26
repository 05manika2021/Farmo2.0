'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { getPriceTrend, getNearbyMarkets } from '@/lib/api'
import { useT } from '@/hooks/useT'

const RANGES = [
  { key: '7D', days: 7 },
  { key: '30D', days: 30 },
  { key: '90D', days: 90 },
]

const CROPS = ['Wheat 🌾', 'Cotton 🪡', 'Soybean 🌱']
const CROP_API = ['Wheat', 'Cotton', 'Soybean']

interface TooltipPayload {
  value: number
}

interface HistoryPoint {
  date: string
  price: number
}

interface TrendData {
  crop: string
  market_id: number
  market_name: string
  current_price: number
  trend: string
  history: { date: string; price: number }[]
  data_status: string
}

interface Market {
  id: number
  name: string
  distance_km: number
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayload[]; label?: string }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-foreground text-white px-3 py-2 rounded-xl shadow-lg text-xs">
        <p className="font-semibold">₹{payload[0].value.toLocaleString('en-IN')}/qtl</p>
        <p className="text-white/60">{label}</p>
      </div>
    )
  }
  return null
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${months[d.getMonth()]} ${d.getDate()}`
}

export default function GraphPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [range, setRange] = useState(0)
  const [crop, setCrop] = useState(0)
  const [trendData, setTrendData] = useState<TrendData | null>(null)
  const [markets, setMarkets] = useState<Market[]>([])
  const [loading, setLoading] = useState(true)

  const lat = state.latitude ?? 22.7196
  const lon = state.longitude ?? 75.8577

  const fetchData = useCallback(async (cropIndex: number, days: number) => {
    setLoading(true)
    try {
      const marketsRes = await getNearbyMarkets(lat, lon, 100, CROP_API[cropIndex])
      if (marketsRes && Array.isArray((marketsRes as { markets: Market[] }).markets)) {
        setMarkets((marketsRes as { markets: Market[] }).markets)
        const topMarket = (marketsRes as { markets: Market[] }).markets[0]
        if (topMarket) {
          const trendRes = await getPriceTrend(CROP_API[cropIndex], topMarket.id, days)
          if (trendRes) {
            setTrendData(trendRes as TrendData)
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch trend data:', err)
    } finally {
      setLoading(false)
    }
  }, [lat, lon])

  useEffect(() => {
    fetchData(crop, RANGES[range].days)
  }, [crop, range, fetchData])

  const handleCropChange = (i: number) => setCrop(i)
  const handleRangeChange = (i: number) => setRange(i)

  const chartData: HistoryPoint[] = trendData
    ? trendData.history.map((h) => ({ date: formatDate(h.date), price: h.price }))
    : []

  const prices = chartData.map((d) => d.price)
  const min = prices.length ? Math.min(...prices) : 0
  const max = prices.length ? Math.max(...prices) : 0
  const latest = trendData?.current_price ?? (prices.length ? prices[prices.length - 1] : 0)
  const prev = prices.length >= 2 ? prices[prices.length - 2] : latest
  const change = latest - prev
  const changePct = prev !== 0 ? ((change / prev) * 100).toFixed(1) : '0.0'
  const trending = trendData?.trend === 'increasing'
  const stableTrend = trendData?.trend === 'stable'

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('graph.title')} onBack={() => router.push('/home')} />

      <div className="flex-1 overflow-y-auto no-scrollbar">
        <div className="px-4 mb-3">
          <div className="flex gap-2">
            {CROPS.map((c, i) => (
              <button
                key={c}
                onClick={() => handleCropChange(i)}
                className={`flex-1 py-2 rounded-xl text-xs font-semibold border-2 transition-all ${
                  crop === i ? 'bg-primary text-white border-primary' : 'bg-card border-border text-foreground'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-sm text-muted-foreground animate-pulse">{t('graph.loadingData')}</div>
          </div>
        ) : (
          <>
            <div className="mx-4 mb-4 flex gap-3">
              <div className="flex-1 p-4 bg-card rounded-2xl border border-border">
                <p className="text-xs text-muted-foreground mb-1">{t('graph.current')}</p>
                <p className="text-2xl font-black text-foreground">₹{latest.toLocaleString('en-IN')}</p>
                <p className="text-xs text-muted-foreground">/quintal</p>
              </div>
              <div className="flex-1 p-4 bg-card rounded-2xl border border-border">
                <p className="text-xs text-muted-foreground mb-1">{t('graph.change')}</p>
                <p className={`text-2xl font-black ${change >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {change >= 0 ? '+' : ''}₹{change}
                </p>
                <p className={`text-xs font-semibold ${change >= 0 ? 'text-success' : 'text-destructive'}`}>
                  {change >= 0 ? '▲' : '▼'} {changePct}%
                </p>
              </div>
              <div className="flex-1 p-4 bg-card rounded-2xl border border-border">
                <p className="text-xs text-muted-foreground mb-1">{t('graph.trend')}</p>
                <p className="text-xl font-black text-foreground">{trending ? '📈' : stableTrend ? '➡️' : '📉'}</p>
                <p className={`text-xs font-semibold ${trending ? 'text-success' : stableTrend ? 'text-muted-foreground' : 'text-destructive'}`}>
                  {trending ? t('graph.rising') : stableTrend ? t('graph.stable') : t('graph.falling')}
                </p>
              </div>
            </div>

            <div className="px-4 mb-3">
              <div className="flex bg-muted rounded-xl p-1 gap-1">
                {RANGES.map((r, i) => (
                  <button
                    key={r.key}
                    onClick={() => handleRangeChange(i)}
                    className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
                      range === i ? 'bg-secondary text-secondary-foreground shadow-sm' : 'text-muted-foreground'
                    }`}
                  >
                    {r.key}
                  </button>
                ))}
              </div>
            </div>

            <div className="mx-4 mb-4 bg-card rounded-2xl border border-border p-4 pt-5">
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2EDE9" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: '#5A7A70', fontFamily: 'Poppins' }}
                      tickLine={false}
                      axisLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: '#5A7A70', fontFamily: 'Poppins' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₹${v}`}
                      domain={[min - 50, max + 50]}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={latest} stroke="#CFD050" strokeDasharray="4 4" strokeWidth={1.5}/>
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#18594B"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5, fill: '#18594B', stroke: 'white', strokeWidth: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-between mt-2 px-1">
                <span className="text-[10px] text-muted-foreground">{t('graph.low')}: ₹{min.toLocaleString('en-IN')}</span>
                <span className="text-[10px] text-muted-foreground">{t('graph.high')}: ₹{max.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <div className="mx-4 mb-4">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 px-1">{t('graph.todaysPrices')}</p>
              <div className="space-y-2">
                {markets.slice(0, 5).map((m, i) => (
                  <div key={m.id} className="flex items-center justify-between p-3.5 bg-card rounded-2xl border border-border">
                    <div className="flex items-center gap-2">
                      {i === 0 && <span className="text-xs font-bold text-secondary bg-secondary/15 px-2 py-0.5 rounded-full">{t('graph.best')}</span>}
                      <span className="text-sm font-medium text-foreground">{m.name}</span>
                      <span className="text-xs text-muted-foreground">{m.distance_km} km</span>
                    </div>
                  </div>
                ))}
                {markets.length === 0 && (
                  <div className="text-center text-xs text-muted-foreground py-4">{t('graph.noMarkets')}</div>
                )}
              </div>
            </div>

            <button
              onClick={() => router.push('/comparison')}
              className="mx-4 mb-4 w-[calc(100%-2rem)] h-12 bg-primary rounded-2xl text-sm font-semibold text-white flex items-center justify-center"
            >
              {t('graph.compareAll')}
            </button>
          </>
        )}
      </div>

      <BottomNav active="graph" />
    </div>
  )
}

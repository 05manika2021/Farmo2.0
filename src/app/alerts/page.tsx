'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import { useApp } from '@/contexts/AppContext'
import { getAlerts, type AlertItem } from '@/lib/api'
import { useT } from '@/hooks/useT'

const TYPE_META: Record<string, { icon: string; tone: string }> = {
  weather: { icon: '🌦', tone: 'text-primary' },
  market: { icon: '₹', tone: 'text-success' },
  sell: { icon: '⚖', tone: 'text-warning' },
}

export default function AlertsPage() {
  const router = useRouter()
  const { state } = useApp()
  const t = useT()
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [loading, setLoading] = useState(true)

  const crop = state.crops[0] || 'Wheat'
  const lat = state.latitude ?? 22.7196
  const lon = state.longitude ?? 75.8577

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    getAlerts({
      language: state.language,
      crop,
      quantity: state.quantity,
      latitude: lat,
      longitude: lon,
    })
      .then((res) => {
        if (cancelled) return
        setAlerts(Array.isArray(res?.alerts) ? res!.alerts : [])
      })
      .catch(() => {
        if (!cancelled) setAlerts([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [state.language, state.quantity, crop, lat, lon])

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('alerts.title')} onBack={() => router.push('/home')} />

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-4">
        <div className="flex items-center gap-2 mb-4 px-1">
          <span className="text-[10px] font-bold bg-muted text-muted-foreground px-2 py-0.5 rounded-full">DEMO</span>
          <p className="text-xs text-muted-foreground">{t('alerts.demoNote')}</p>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-4 bg-card rounded-2xl border border-border animate-pulse">
                <div className="h-3 bg-muted rounded w-1/3 mb-2" />
                <div className="h-3 bg-muted rounded w-3/4" />
              </div>
            ))}
            <p className="text-xs text-muted-foreground text-center">{t('alerts.loading')}</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-6 bg-card rounded-2xl border border-border text-center">
            <p className="text-2xl mb-2">🔔</p>
            <p className="text-sm text-foreground font-semibold">{t('alerts.empty')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => {
              const meta = TYPE_META[alert.type] ?? TYPE_META.market
              return (
                <div
                  key={alert.id}
                  className={`p-4 rounded-2xl border ${
                    alert.severity === 'warning'
                      ? 'bg-amber-50 border-amber-200'
                      : 'bg-card border-border'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-base font-bold ${meta.tone}`}>{meta.icon}</span>
                    <p className="text-sm font-bold text-foreground flex-1 min-w-0">{alert.title}</p>
                    <span className="text-[9px] font-bold bg-muted text-muted-foreground px-1.5 py-0.5 rounded shrink-0">
                      {alert.data_status}
                    </span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">{alert.body}</p>
                </div>
              )
            })}
          </div>
        )}

        <button
          onClick={() => router.push('/chat')}
          className="w-full h-12 mt-4 rounded-2xl text-sm font-semibold bg-primary text-white active:scale-95 transition-transform"
        >
          {t('home.askFarmo')}
        </button>
      </div>

      <BottomNav active="home" />
    </div>
  )
}

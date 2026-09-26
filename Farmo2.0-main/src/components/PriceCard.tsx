'use client'

import { useT } from '@/hooks/useT'

interface PriceCardProps {
  crop: string
  cropIcon?: string
  market: string
  distance: string
  pricePerQtl: number
  transportCost?: number
  netProfit?: number
  badge?: 'best' | 'good' | null
  trend?: 'up' | 'down' | 'stable'
  onClick?: () => void
  compact?: boolean
}

const TREND_ICONS = {
  up: (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 11V3M7 3L3 7M7 3L11 7" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  down: (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 3V11M7 11L3 7M7 11L11 7" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  stable: (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 7H11" stroke="#D97706" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
}

export default function PriceCard({
  crop,
  cropIcon = '🌾',
  market,
  distance,
  pricePerQtl,
  transportCost,
  netProfit,
  badge,
  trend,
  onClick,
  compact,
}: PriceCardProps) {
  const t = useT()

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-card rounded-2xl border border-border p-4 flex flex-col gap-3 active:scale-[0.98] transition-transform shadow-sm"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl leading-none">{cropIcon}</span>
          <div>
            <p className="text-sm font-semibold text-foreground leading-tight">{crop}</p>
            <p className="text-xs text-muted-foreground">{market} · {distance}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {badge === 'best' && (
            <span className="text-xs font-bold bg-secondary text-secondary-foreground px-2.5 py-1 rounded-full">{t('price.best')}</span>
          )}
          {badge === 'good' && (
            <span className="text-xs font-semibold bg-primary/10 text-primary px-2.5 py-1 rounded-full">{t('price.good')}</span>
          )}
          {trend && <span className="flex items-center gap-0.5">{TREND_ICONS[trend]}</span>}
        </div>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs text-muted-foreground mb-0.5">{t('price.mandiPrice')}</p>
          <p className="text-xl font-bold text-foreground">
            ₹{pricePerQtl.toLocaleString('en-IN')}
            <span className="text-xs font-normal text-muted-foreground ml-1">{t('price.perQtl')}</span>
          </p>
        </div>
        {!compact && transportCost !== undefined && (
          <div className="text-right">
            <p className="text-xs text-muted-foreground mb-0.5">{t('price.transport')}</p>
            <p className="text-sm font-medium text-foreground">−₹{transportCost.toLocaleString('en-IN')}</p>
          </div>
        )}
        {netProfit !== undefined && (
          <div className="text-right">
            <p className="text-xs text-muted-foreground mb-0.5">{t('price.netProfit')}</p>
            <p className={`text-xl font-bold ${netProfit >= 0 ? 'text-success' : 'text-destructive'}`}>
              ₹{Math.abs(netProfit).toLocaleString('en-IN')}
            </p>
          </div>
        )}
      </div>
    </button>
  )
}

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import TopBar from '@/components/TopBar'
import Button from '@/components/Button'
import { useApp } from '@/contexts/AppContext'
import { useT } from '@/hooks/useT'

const STATES = ['Haryana', 'Punjab', 'Uttar Pradesh', 'Madhya Pradesh', 'Maharashtra', 'Rajasthan', 'Gujarat']
const DISTRICTS: Record<string, string[]> = {
  'Haryana': ['Hisar', 'Rohtak', 'Karnal', 'Panipat', 'Ambala', 'Sirsa', 'Fatehabad'],
  'Punjab': ['Ludhiana', 'Amritsar', 'Patiala', 'Bathinda', 'Jalandhar', 'Moga'],
  'Uttar Pradesh': ['Agra', 'Meerut', 'Varanasi', 'Lucknow', 'Bareilly', 'Mathura'],
}
const VILLAGES = ['Jaitpur', 'Rampur', 'Badli', 'Khanpur', 'Bhiwani', 'Tosham']

export default function VillagePage() {
  const router = useRouter()
  const { setLocation } = useApp()
  const t = useT()
  const [query, setQuery] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [village, setVillage] = useState('')

  const filteredVillages = VILLAGES.filter((v) =>
    v.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="flex flex-col min-h-full bg-background screen-enter">
      <TopBar title={t('village.title')} onBack={() => router.push('/location')} />

      <div className="flex-1 px-4 overflow-y-auto no-scrollbar">
        <div className="px-2 mb-4">
          <div className="flex items-center gap-2 px-4 py-3 bg-muted rounded-2xl border border-border">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="8" cy="8" r="6" stroke="#5A7A70" strokeWidth="1.8"/>
              <path d="M13 13L16 16" stroke="#5A7A70" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('village.search')}
              className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>
        </div>

        <div className="px-2 mb-3">
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">{t('village.state')}</label>
          <div className="flex flex-wrap gap-2">
            {STATES.map((s) => (
              <button
                key={s}
                onClick={() => { setState(s); setDistrict(''); setVillage('') }}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  state === s ? 'bg-primary text-white border-primary' : 'bg-card border-border text-foreground'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {state && DISTRICTS[state] && (
          <div className="px-2 mb-3">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 block">{t('village.district')}</label>
            <div className="flex flex-wrap gap-2">
              {DISTRICTS[state].map((d) => (
                <button
                  key={d}
                  onClick={() => { setDistrict(d); setVillage('') }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                    district === d ? 'bg-primary text-white border-primary' : 'bg-card border-border text-foreground'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="px-2 space-y-2 mb-4">
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 block">{t('village.village')}</label>
          {filteredVillages.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">{t('village.noResults')}</div>
          ) : (
            filteredVillages.map((v) => (
              <button
                key={v}
                onClick={() => setVillage(v)}
                className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl border-2 transition-all ${
                  village === v ? 'border-primary bg-primary/5' : 'border-border bg-card'
                }`}
              >
                <div className="flex items-center gap-3">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M8 2C5.239 2 3 4.239 3 7C3 11 8 14 8 14C8 14 13 11 13 7C13 4.239 10.761 2 8 2Z"
                      fill={village === v ? '#18594B' : '#DDE9E5'} stroke={village === v ? '#18594B' : '#5A7A70'} strokeWidth="1.2"/>
                    <circle cx="8" cy="7" r="1.5" fill={village === v ? 'white' : '#5A7A70'}/>
                  </svg>
                  <span className={`text-sm font-medium ${village === v ? 'text-primary' : 'text-foreground'}`}>{v}</span>
                </div>
                {village === v && (
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <circle cx="9" cy="9" r="9" fill="#18594B"/>
                    <path d="M5 9L7.5 11.5L13 6" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="px-6 pb-8">
        <Button fullWidth size="lg" disabled={!village} onClick={() => { setLocation(28.4595, 76.9915, village + (district ? ', ' + district : '') + (state ? ', ' + state : '')); router.push('/home') }}>
          {t('village.confirm')}
        </Button>
      </div>
    </div>
  )
}

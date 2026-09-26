'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useT } from '@/hooks/useT'

export default function BottomNav({ active }: { active: string }) {
  const router = useRouter()
  const t = useT()

  const NAV_ITEMS = [
    {
      key: 'home',
      href: '/home',
      label: t('nav.home'),
      icon: (active: boolean) => (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <path d="M3 9.5L11 3L19 9.5V19C19 19.55 18.55 20 18 20H14V15H8V20H4C3.45 20 3 19.55 3 19V9.5Z"
            fill={active ? '#18594B' : 'none'}
            stroke={active ? '#18594B' : '#5A7A70'}
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      key: 'chat',
      href: '/chat',
      label: t('nav.askFarmo'),
      icon: (active: boolean) => (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <path d="M19 3H3C2.45 3 2 3.45 2 4V15C2 15.55 2.45 16 3 16H7V20L13 16H19C19.55 16 20 15.55 20 15V4C20 3.45 19.55 3 19 3Z"
            fill={active ? '#18594B' : 'none'}
            stroke={active ? '#18594B' : '#5A7A70'}
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
          />
          <circle cx="7.5" cy="9.5" r="1" fill={active ? 'white' : '#5A7A70'}/>
          <circle cx="11" cy="9.5" r="1" fill={active ? 'white' : '#5A7A70'}/>
          <circle cx="14.5" cy="9.5" r="1" fill={active ? 'white' : '#5A7A70'}/>
        </svg>
      ),
    },
    {
      key: 'graph',
      href: '/graph',
      label: t('nav.prices'),
      icon: (active: boolean) => (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <polyline points="3,17 8,11 12,14 17,7 21,9"
            stroke={active ? '#18594B' : '#5A7A70'}
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            fill="none"
          />
          <line x1="3" y1="19" x2="21" y2="19" stroke={active ? '#18594B' : '#5A7A70'} strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      key: 'settings',
      href: '/settings',
      label: t('nav.profile'),
      icon: (active: boolean) => (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <circle cx="11" cy="7" r="4"
            fill={active ? '#18594B' : 'none'}
            stroke={active ? '#18594B' : '#5A7A70'}
            strokeWidth="1.8"
          />
          <path d="M3 19C3 15.686 6.686 13 11 13C15.314 13 19 15.686 19 19"
            stroke={active ? '#18594B' : '#5A7A70'}
            strokeWidth="1.8" strokeLinecap="round"
          />
        </svg>
      ),
    },
  ]

  return (
    <div className="flex items-center justify-around bg-white border-t border-border px-2 pb-6 pt-3">
      {NAV_ITEMS.map((item) => {
        const isActive = active === item.key
        return (
          <button
            key={item.key}
            onClick={() => router.push(item.href)}
            className="flex flex-col items-center gap-1 min-w-[56px] active:scale-95 transition-transform"
          >
            {item.icon(isActive)}
            <span className={`text-[10px] font-semibold ${isActive ? 'text-primary' : 'text-muted-foreground'}`}>
              {item.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}

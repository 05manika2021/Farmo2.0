'use client'

interface TopBarProps {
  title?: string
  onBack?: () => void
  right?: React.ReactNode
  dark?: boolean
}

export default function TopBar({ title, onBack, right, dark }: TopBarProps) {
  const fg = dark ? 'text-white' : 'text-foreground'
  return (
    <div className={`flex items-center justify-between px-4 pt-12 pb-3`}>
      <button
        onClick={onBack}
        className={`w-10 h-10 flex items-center justify-center rounded-full transition-colors ${
          dark ? 'hover:bg-white/10 text-white' : 'hover:bg-muted text-foreground'
        } ${!onBack ? 'invisible' : ''}`}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M12 4L6 10L12 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {title && (
        <span className={`text-base font-semibold ${fg}`}>{title}</span>
      )}
      <div className="w-10 flex justify-end">{right}</div>
    </div>
  )
}

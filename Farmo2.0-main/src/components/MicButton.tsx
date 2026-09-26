'use client'

interface MicButtonProps {
  size?: 'lg' | 'xl'
  listening?: boolean
  onClick?: () => void
  disabled?: boolean
}

export default function MicButton({ size = 'xl', listening = false, onClick, disabled }: MicButtonProps) {
  const dim = size === 'xl' ? 88 : 64
  const iconSize = size === 'xl' ? 36 : 28

  return (
    <div className="relative flex items-center justify-center" style={{ width: dim * 2.4, height: dim * 2.4 }}>
      {listening && (
        <>
          <div
            className="absolute rounded-full bg-secondary/20"
            style={{ width: dim * 2.2, height: dim * 2.2, animation: 'pulse-ring 1.5s ease-out infinite' }}
          />
          <div
            className="absolute rounded-full bg-secondary/10"
            style={{ width: dim * 1.7, height: dim * 1.7, animation: 'pulse-ring-slow 1.8s ease-out 0.3s infinite' }}
          />
        </>
      )}
      <button
        onClick={onClick}
        disabled={disabled}
        className={`relative z-10 flex items-center justify-center rounded-full transition-all active:scale-95 shadow-lg ${
          listening
            ? 'bg-secondary'
            : 'bg-primary hover:bg-primary-light'
        } ${disabled ? 'opacity-50' : ''}`}
        style={{ width: dim, height: dim }}
      >
        <svg width={iconSize} height={iconSize} viewBox="0 0 36 36" fill="none">
          <rect x="12" y="2" width="12" height="20" rx="6"
            fill={listening ? '#001913' : 'white'}
          />
          <path
            d="M6 17C6 23.627 11.373 29 18 29C24.627 29 30 23.627 30 17"
            stroke={listening ? '#001913' : 'white'}
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <line x1="18" y1="29" x2="18" y2="34" stroke={listening ? '#001913' : 'white'} strokeWidth="2.5" strokeLinecap="round"/>
          <line x1="13" y1="34" x2="23" y2="34" stroke={listening ? '#001913' : 'white'} strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
      </button>
    </div>
  )
}

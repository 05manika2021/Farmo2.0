'use client'

import { ReactNode } from 'react'

interface ButtonProps {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
  className?: string
  icon?: ReactNode
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  onClick,
  className = '',
  icon,
}: ButtonProps) {
  const base = 'inline-flex items-center justify-center gap-2 font-semibold rounded-2xl transition-all active:scale-95 select-none'

  const variants: Record<string, string> = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary-light disabled:opacity-50',
    secondary: 'bg-secondary text-secondary-foreground hover:brightness-95 disabled:opacity-50',
    ghost: 'bg-transparent text-primary hover:bg-muted disabled:opacity-50',
    outline: 'bg-transparent text-primary border-2 border-primary hover:bg-muted disabled:opacity-50',
  }

  const sizes: Record<string, string> = {
    sm: 'h-10 px-4 text-sm',
    md: 'h-12 px-6 text-base',
    lg: 'h-14 px-8 text-base',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
    >
      {loading ? (
        <svg className="spinner w-5 h-5" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
        </svg>
      ) : icon}
      {children}
    </button>
  )
}

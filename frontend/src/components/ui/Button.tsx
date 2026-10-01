import type { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  variant?: 'primary' | 'ghost'
}

export function Button({ loading = false, variant = 'primary', children, disabled, ...props }: ButtonProps) {
  return (
    <button
      className={`btn btn--${variant}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className="btn__spinner" aria-label="Carregando..." /> : children}
    </button>
  )
}

import type { InputHTMLAttributes } from 'react'

interface InputFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function InputField({ label, error, id, ...props }: InputFieldProps) {
  return (
    <div className="form-group">
      <label htmlFor={id} className="form-label">
        {label}
      </label>
      <input
        id={id}
        className={`form-input${error ? ' form-input--error' : ''}`}
        {...props}
      />
      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

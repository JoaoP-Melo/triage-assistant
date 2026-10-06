import type { ChangeEvent } from 'react'

interface DescriptionTextareaProps {
  value: string
  onChange: (value: string) => void
  error?: string
  disabled?: boolean
  maxLength?: number
}

export function DescriptionTextarea({
  value,
  onChange,
  error,
  disabled = false,
  maxLength = 2000,
}: DescriptionTextareaProps) {
  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onChange(e.target.value)
  }

  return (
    <div className="form-group triage-description">
      <div className="triage-description__header">
        <label htmlFor="triage-description" className="form-label">
          Descrição Detalhada do Quadro <span className="form-label__required">*</span>
        </label>
        <span
          className={`triage-description__counter ${
            value.length > maxLength ? 'triage-description__counter--overflow' : ''
          }`}
        >
          {value.length}/{maxLength}
        </span>
      </div>

      <textarea
        id="triage-description"
        rows={4}
        maxLength={maxLength}
        placeholder="Descreva o que está sentindo, quando piora ou melhora, se tomou alguma medicação prévia e outras observações relevantes..."
        value={value}
        onChange={handleChange}
        disabled={disabled}
        className={`form-input form-textarea ${error ? 'form-input--error' : ''}`}
      />

      <span className="form-helper">
        Mínimo de 10 caracteres. Quanto mais claro o relato, mais precisa será a recomendação médica.
      </span>

      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

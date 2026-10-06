import type { ChangeEvent } from 'react'

interface SymptomDurationInputProps {
  value: number | ''
  onChange: (value: number | '') => void
  error?: string
  disabled?: boolean
}

export function SymptomDurationInput({
  value,
  onChange,
  error,
  disabled = false,
}: SymptomDurationInputProps) {
  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    if (raw === '') {
      onChange('')
      return
    }
    const parsed = parseFloat(raw)
    onChange(isNaN(parsed) ? '' : parsed)
  }

  return (
    <div className="form-group triage-duration">
      <label htmlFor="triage-duration" className="form-label">
        Duração dos Sintomas (em horas) <span className="form-label__required">*</span>
      </label>

      <div className="triage-duration__input-wrapper">
        <input
          id="triage-duration"
          type="number"
          min="0.1"
          step="0.5"
          placeholder="Ex: 24 (para 1 dia), 48 (para 2 dias)"
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={`form-input ${error ? 'form-input--error' : ''}`}
        />
        <span className="triage-duration__suffix">horas</span>
      </div>

      <span className="form-helper">
        Informe há quanto tempo os primeiros sintomas começaram a se manifestar.
      </span>

      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

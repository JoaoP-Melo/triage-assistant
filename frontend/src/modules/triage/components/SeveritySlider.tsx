interface SeveritySliderProps {
  value: number
  onChange: (value: number) => void
  error?: string
  disabled?: boolean
}

export function SeveritySlider({ value, onChange, error, disabled = false }: SeveritySliderProps) {
  function getSeverityColor(val: number) {
    if (val <= 3) return 'var(--color-success-text, #86efac)'
    if (val <= 6) return '#facc15'
    if (val <= 8) return '#fb923c'
    return 'var(--color-error-text, #fca5a5)'
  }

  function getSeverityLabel(val: number) {
    if (val <= 3) return 'Leve'
    if (val <= 6) return 'Moderada'
    if (val <= 8) return 'Intensa'
    return 'Muito Intensa / Extrema'
  }

  return (
    <div className="form-group triage-severity">
      <div className="triage-severity__header">
        <label htmlFor="triage-severity" className="form-label">
          Severidade Percebida (1 a 10) <span className="form-label__required">*</span>
        </label>
        <span
          className="triage-severity__badge"
          style={{
            color: getSeverityColor(value),
            borderColor: getSeverityColor(value),
          }}
        >
          {value}/10 — {getSeverityLabel(value)}
        </span>
      </div>

      <div className="triage-severity__slider-wrap">
        <input
          id="triage-severity"
          type="range"
          min={1}
          max={10}
          step={1}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          className="triage-severity__range"
        />
        <div className="triage-severity__ticks">
          {Array.from({ length: 10 }, (_, i) => i + 1).map((num) => (
            <span
              key={num}
              className={`triage-severity__tick ${num === value ? 'triage-severity__tick--active' : ''}`}
            >
              {num}
            </span>
          ))}
        </div>
      </div>

      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

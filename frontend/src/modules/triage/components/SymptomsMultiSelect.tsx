import { SYMPTOM_OPTIONS } from '../constants/symptoms'

interface SymptomsMultiSelectProps {
  selectedSymptoms: string[]
  onToggleSymptom: (symptom: string) => void
  error?: string
  disabled?: boolean
}

export function SymptomsMultiSelect({
  selectedSymptoms,
  onToggleSymptom,
  error,
  disabled = false,
}: SymptomsMultiSelectProps) {
  const isMaxReached = selectedSymptoms.length >= 3

  return (
    <div className="form-group triage-symptoms">
      <div className="triage-symptoms__header">
        <label className="form-label">
          Sintomas Primários <span className="form-label__required">*</span>
        </label>
        <span
          className={`triage-symptoms__counter ${
            selectedSymptoms.length === 3 ? 'triage-symptoms__counter--complete' : ''
          }`}
          aria-live="polite"
        >
          {selectedSymptoms.length}/3 selecionados
        </span>
      </div>

      <p className="form-helper">
        Selecione exatamente 3 sintomas principais que melhor descrevem seu estado atual.
      </p>

      <div className="triage-symptoms__grid" role="group" aria-label="Lista de sintomas disponíveis">
        {SYMPTOM_OPTIONS.map((option) => {
          const isSelected = selectedSymptoms.includes(option.value)
          const isDisabled = disabled || (!isSelected && isMaxReached)

          return (
            <button
              key={option.value}
              type="button"
              disabled={isDisabled}
              onClick={() => onToggleSymptom(option.value)}
              className={`triage-chip ${isSelected ? 'triage-chip--selected' : ''} ${
                isDisabled ? 'triage-chip--disabled' : ''
              }`}
              aria-pressed={isSelected}
            >
              <span className="triage-chip__check">{isSelected ? '✓' : '+'}</span>
              <span className="triage-chip__label">{option.label}</span>
            </button>
          )
        })}
      </div>

      {error && <span className="form-error">{error}</span>}
    </div>
  )
}

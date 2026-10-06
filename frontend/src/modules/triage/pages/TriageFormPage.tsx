import { useNavigate } from 'react-router-dom'
import { AlertMessage } from '../../../components/ui/AlertMessage'
import { Button } from '../../../components/ui/Button'
import { DescriptionTextarea } from '../components/DescriptionTextarea'
import { SeveritySlider } from '../components/SeveritySlider'
import { SymptomDurationInput } from '../components/SymptomDurationInput'
import { SymptomsMultiSelect } from '../components/SymptomsMultiSelect'
import { useTriageForm } from '../hooks/useTriageForm'
import { TriageResultPage } from './TriageResultPage'

export function TriageFormPage() {
  const navigate = useNavigate()
  const {
    values,
    errors,
    loading,
    error,
    result,
    handleChangeSeverity,
    handleChangeDuration,
    handleToggleSymptom,
    handleChangeDescription,
    handleSubmit,
    resetForm,
  } = useTriageForm()

  return (
    <div className="triage-page">
      <header className="triage-header">
        <div className="triage-header__brand">
          <span className="triage-header__logo" aria-hidden="true">⚕</span>
          <span className="triage-header__app-name">Triage Assistant</span>
        </div>
        <button
          type="button"
          onClick={() => navigate('/home')}
          className="btn btn--ghost"
        >
          Voltar ao Início
        </button>
      </header>

      <main className="triage-main">
        <div className="triage-container">
          {result ? (
            <TriageResultPage result={result} onNewTriage={resetForm} />
          ) : (
            <div className="triage-card">
              <div className="triage-card__header">
                <h1 className="triage-card__title">Triagem Clínica de Sintomas</h1>
                <p className="triage-card__subtitle">
                  Preencha as informações abaixo para receber direcionamento médico prioritário com auxílio de inteligência clínica.
                </p>
              </div>

              {error && <AlertMessage message={error} type="error" />}

              {loading && (
                <div className="triage-loading-banner" role="status">
                  <div className="triage-loading-spinner" />
                  <div>
                    <strong>Analisando quadro clínico...</strong>
                    <p className="triage-loading-text">
                      Nosso sistema de classificação híbrido (ML + IA) está processando seus dados para recomendar a especialidade ideal. Isso pode levar alguns segundos.
                    </p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate className="triage-form">
                <SeveritySlider
                  value={values.perceived_severity}
                  onChange={handleChangeSeverity}
                  error={errors.perceived_severity}
                  disabled={loading}
                />

                <SymptomsMultiSelect
                  selectedSymptoms={values.primary_symptoms}
                  onToggleSymptom={handleToggleSymptom}
                  error={errors.primary_symptoms}
                  disabled={loading}
                />

                <SymptomDurationInput
                  value={values.symptom_duration_hours}
                  onChange={handleChangeDuration}
                  error={errors.symptom_duration_hours}
                  disabled={loading}
                />

                <DescriptionTextarea
                  value={values.description}
                  onChange={handleChangeDescription}
                  error={errors.description}
                  disabled={loading}
                />

                <div className="triage-form__actions">
                  <Button
                    type="submit"
                    loading={loading}
                    className="btn--full-width"
                  >
                    Enviar Triagem
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

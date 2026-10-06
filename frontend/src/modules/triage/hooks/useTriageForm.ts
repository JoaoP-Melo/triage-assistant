import { useState } from 'react'
import { ApiError } from '../../../services/api'
import { PRIMARY_SYMPTOMS } from '../constants/symptoms'
import { submitTriage } from '../services/triageService'
import type {
  TriageFormErrors,
  TriageFormState,
  TriageSubmitResponse,
} from '../types/triage.types'

const INITIAL_FORM_STATE: TriageFormState = {
  perceived_severity: 5,
  symptom_duration_hours: '',
  primary_symptoms: [],
  description: '',
}

export function useTriageForm() {
  const [values, setValues] = useState<TriageFormState>(INITIAL_FORM_STATE)
  const [errors, setErrors] = useState<TriageFormErrors>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TriageSubmitResponse | null>(null)

  function handleChangeSeverity(val: number) {
    setValues((prev) => ({ ...prev, perceived_severity: val }))
    if (errors.perceived_severity) {
      setErrors((prev) => ({ ...prev, perceived_severity: undefined }))
    }
  }

  function handleChangeDuration(val: number | '') {
    setValues((prev) => ({ ...prev, symptom_duration_hours: val }))
    if (errors.symptom_duration_hours) {
      setErrors((prev) => ({ ...prev, symptom_duration_hours: undefined }))
    }
  }

  function handleToggleSymptom(symptom: string) {
    setValues((prev) => {
      const exists = prev.primary_symptoms.includes(symptom)
      if (exists) {
        return {
          ...prev,
          primary_symptoms: prev.primary_symptoms.filter((s) => s !== symptom),
        }
      }
      if (prev.primary_symptoms.length >= 3) {
        return prev
      }
      return {
        ...prev,
        primary_symptoms: [...prev.primary_symptoms, symptom],
      }
    })

    if (errors.primary_symptoms) {
      setErrors((prev) => ({ ...prev, primary_symptoms: undefined }))
    }
  }

  function handleChangeDescription(val: string) {
    setValues((prev) => ({ ...prev, description: val }))
    if (errors.description) {
      setErrors((prev) => ({ ...prev, description: undefined }))
    }
  }

  function validate(state: TriageFormState): TriageFormErrors {
    const errs: TriageFormErrors = {}

    if (
      !Number.isInteger(state.perceived_severity) ||
      state.perceived_severity < 1 ||
      state.perceived_severity > 10
    ) {
      errs.perceived_severity = 'A severidade deve ser um número inteiro entre 1 e 10.'
    }

    if (
      state.symptom_duration_hours === '' ||
      typeof state.symptom_duration_hours !== 'number' ||
      state.symptom_duration_hours <= 0
    ) {
      errs.symptom_duration_hours = 'Informe a duração dos sintomas em horas (número maior que zero).'
    }

    if (state.primary_symptoms.length !== 3) {
      errs.primary_symptoms = 'Você deve selecionar exatamente 3 sintomas principais.'
    } else {
      const invalid = state.primary_symptoms.filter(
        (s) => !PRIMARY_SYMPTOMS.includes(s)
      )
      if (invalid.length > 0) {
        errs.primary_symptoms = 'Selecione apenas sintomas presentes na lista permitida.'
      }
    }

    const trimmedDesc = state.description.trim()
    if (!trimmedDesc) {
      errs.description = 'A descrição detalhada é obrigatória.'
    } else if (trimmedDesc.length < 10) {
      errs.description = 'A descrição deve conter no mínimo 10 caracteres para contextualizar a IA.'
    } else if (trimmedDesc.length > 2000) {
      errs.description = 'A descrição deve ter no máximo 2000 caracteres.'
    }

    return errs
  }

  async function handleSubmit(e?: React.FormEvent) {
    if (e) {
      e.preventDefault()
    }

    const validationErrors = validate(values)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await submitTriage({
        perceived_severity: values.perceived_severity,
        symptom_duration_hours: Number(values.symptom_duration_hours),
        primary_symptoms: values.primary_symptoms,
        description: values.description.trim(),
      })

      setResult(response)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError(
            'Limite de requisições atingido. Por favor, aguarde alguns instantes antes de enviar uma nova triagem.'
          )
        } else if (err.status === 403) {
          setError('Acesso negado. Apenas pacientes podem submeter triagens.')
        } else {
          setError(err.message || 'Erro ao processar a triagem clínica.')
        }
      } else {
        setError('Ocorreu uma falha de conexão. Por favor, tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }

  function resetForm() {
    setValues(INITIAL_FORM_STATE)
    setErrors({})
    setError(null)
    setResult(null)
  }

  return {
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
  }
}

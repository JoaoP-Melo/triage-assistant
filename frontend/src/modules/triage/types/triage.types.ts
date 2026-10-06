/**
 * Tipos compartilhados do módulo de triagem de paciente.
 */

export interface TriageSubmitPayload {
  perceived_severity: number
  symptom_duration_hours: number
  primary_symptoms: string[]
  description: string
}

export type UrgencyLevel = 'BAIXA' | 'MEDIA' | 'ALTA' | 'EMERGENCIA'

export interface TriageSubmitResponse {
  ticket_id: string
  assigned_specialty: string
  urgency_level: UrgencyLevel
  status: string
  created_at: string
}

export interface TriageFormState {
  perceived_severity: number
  symptom_duration_hours: number | ''
  primary_symptoms: string[]
  description: string
}

export interface TriageFormErrors {
  perceived_severity?: string
  symptom_duration_hours?: string
  primary_symptoms?: string
  description?: string
}

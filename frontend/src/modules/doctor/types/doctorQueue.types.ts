export type UrgencyLevel = 'EMERGENCIA' | 'ALTA' | 'MEDIA' | 'BAIXA'

export interface PatientInput {
  perceived_severity: number
  symptom_duration_hours: number
  primary_symptoms: string[]
  description: string
}

export interface DoctorQueueTicket {
  ticket_id: string
  assigned_specialty: string
  urgency_level: UrgencyLevel
  status: string
  created_at: string
  patient_input: PatientInput
}

export interface DoctorQueueResponse {
  items: DoctorQueueTicket[]
  total: number
}

export interface DoctorFinishResponse {
  ticket_id: string
  status: string
}


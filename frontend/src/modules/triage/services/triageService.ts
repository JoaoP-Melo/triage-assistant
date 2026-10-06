import { apiClient } from '../../../services/api'
import type { TriageSubmitPayload, TriageSubmitResponse } from '../types/triage.types'

export async function submitTriage(payload: TriageSubmitPayload): Promise<TriageSubmitResponse> {
  return apiClient.post<TriageSubmitResponse>('/triage/submit', payload)
}

import { apiClient } from '../../../services/api'
import type { DoctorFinishResponse, DoctorQueueResponse } from '../types/doctorQueue.types'

export async function fetchDoctorQueue(limit = 20, offset = 0): Promise<DoctorQueueResponse> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  return apiClient.get<DoctorQueueResponse>(`/triage/queue?${query.toString()}`)
}

export async function finishTicket(ticketId: string): Promise<DoctorFinishResponse> {
  return apiClient.patch<DoctorFinishResponse>(`/triage/${ticketId}/finish`)
}


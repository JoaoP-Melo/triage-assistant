import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../../../services/api'
import { fetchDoctorQueue, finishTicket as finishTicketApi } from '../services/doctorQueueService'
import type { DoctorQueueTicket } from '../types/doctorQueue.types'

const PAGE_SIZE = 20

export function useDoctorQueue() {
  const [items, setItems] = useState<DoctorQueueTicket[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [finishingId, setFinishingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorStatus, setErrorStatus] = useState<number | null>(null)
  const [actionMessage, setActionMessage] = useState<{
    text: string
    type: 'success' | 'error'
  } | null>(null)
  const [offset, setOffset] = useState(0)

  const loadQueue = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setLoading(true)
      setOffset(0)
    }

    setError(null)
    setErrorStatus(null)

    try {
      const response = await fetchDoctorQueue(PAGE_SIZE, 0)
      setItems(response.items)
      setTotal(response.total)
      setOffset(response.items.length)
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorStatus(err.status)
        if (err.status === 403) {
          setError('Acesso não permitido. Esta fila é restrita a médicos autorizados com especialidade cadastrada.')
        } else if (err.status === 429) {
          setError('Muitas requisições em pouco tempo. Por favor, aguarde alguns instantes e tente novamente.')
        } else {
          setError(err.message || 'Erro ao carregar a fila de atendimentos.')
        }
      } else {
        setError('Erro de conexão ao carregar atendimentos. Verifique sua rede e tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const loadMore = useCallback(async () => {
    if (loadingMore || items.length >= total) return

    setLoadingMore(true)
    setError(null)

    try {
      const response = await fetchDoctorQueue(PAGE_SIZE, offset)
      setItems((prev) => [...prev, ...response.items])
      setTotal(response.total)
      setOffset((prev) => prev + response.items.length)
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorStatus(err.status)
        if (err.status === 429) {
          setError('Limite de requisições atingido. Aguarde alguns instantes antes de carregar mais.')
        } else {
          setError(err.message || 'Erro ao carregar mais atendimentos.')
        }
      } else {
        setError('Erro de conexão ao carregar mais atendimentos.')
      }
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, items.length, total, offset])

  const finishTicket = useCallback(async (ticketId: string) => {
    setFinishingId(ticketId)
    setActionMessage(null)

    try {
      await finishTicketApi(ticketId)
      // Sucesso: remove o card localmente e decrementa o total sem refazer busca
      setItems((prev) => prev.filter((item) => item.ticket_id !== ticketId))
      setTotal((prev) => Math.max(0, prev - 1))
      setActionMessage({
        text: 'Atendimento finalizado com sucesso.',
        type: 'success',
      })
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          // 404: já finalizado ou indisponível -> remove o card da lista
          setItems((prev) => prev.filter((item) => item.ticket_id !== ticketId))
          setTotal((prev) => Math.max(0, prev - 1))
          setActionMessage({
            text: 'Este atendimento já foi finalizado ou não está mais disponível.',
            type: 'error',
          })
        } else if (err.status === 403) {
          setActionMessage({
            text: 'Acesso não permitido para finalizar este atendimento.',
            type: 'error',
          })
        } else if (err.status === 429) {
          setActionMessage({
            text: 'Muitas requisições. Aguarde alguns instantes antes de tentar novamente.',
            type: 'error',
          })
        } else {
          setActionMessage({
            text: err.message || 'Erro ao finalizar atendimento. Tente novamente.',
            type: 'error',
          })
        }
      } else {
        setActionMessage({
          text: 'Erro de comunicação ao finalizar atendimento. Tente novamente.',
          type: 'error',
        })
      }
    } finally {
      setFinishingId(null)
    }
  }, [])

  useEffect(() => {
    loadQueue()
  }, [loadQueue])

  const hasMore = items.length < total

  return {
    items,
    total,
    loading,
    loadingMore,
    finishingId,
    error,
    errorStatus,
    actionMessage,
    clearActionMessage: () => setActionMessage(null),
    hasMore,
    refresh: () => loadQueue(true),
    loadMore,
    finishTicket,
  }
}


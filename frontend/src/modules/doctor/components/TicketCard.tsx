import { useEffect, useState } from 'react'
import type { DoctorQueueTicket, UrgencyLevel } from '../types/doctorQueue.types'

interface TicketCardProps {
  ticket: DoctorQueueTicket
  onFinish?: (ticketId: string) => void | Promise<void>
  isFinishing?: boolean
}

const URGENCY_CONFIG: Record<UrgencyLevel, { label: string; bg: string; text: string; border: string }> = {
  EMERGENCIA: {
    label: 'Emergência',
    bg: '#fee2e2',
    text: '#991b1b',
    border: '#ef4444',
  },
  ALTA: {
    label: 'Alta Urgência',
    bg: '#ffedd5',
    text: '#9a3412',
    border: '#f97316',
  },
  MEDIA: {
    label: 'Média Urgência',
    bg: '#fef9c3',
    text: '#854d0e',
    border: '#eab308',
  },
  BAIXA: {
    label: 'Baixa Urgência',
    bg: '#dcfce7',
    text: '#166534',
    border: '#22c55e',
  },
}

function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString)
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return isoString
  }
}

export function TicketCard({ ticket, onFinish, isFinishing = false }: TicketCardProps) {
  const urgencyStyle = URGENCY_CONFIG[ticket.urgency_level] || URGENCY_CONFIG.MEDIA
  const { patient_input } = ticket
  const [confirming, setConfirming] = useState(false)

  // Cancela o modo de confirmação automaticamente após 5 segundos
  useEffect(() => {
    if (!confirming) return
    const timer = setTimeout(() => {
      setConfirming(false)
    }, 5000)
    return () => clearTimeout(timer)
  }, [confirming])

  function handleFinishClick() {
    if (!confirming) {
      setConfirming(true)
      return
    }
    setConfirming(false)
    onFinish?.(ticket.ticket_id)
  }

  return (
    <article
      className="ticket-card"
      style={{
        borderLeft: `5px solid ${urgencyStyle.border}`,
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        padding: '1.25rem',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      }}
    >
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            style={{
              backgroundColor: urgencyStyle.bg,
              color: urgencyStyle.text,
              border: `1px solid ${urgencyStyle.border}`,
              padding: '0.25rem 0.65rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {urgencyStyle.label}
          </span>
          <span
            style={{
              backgroundColor: '#f1f5f9',
              color: '#334155',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}
          >
            {ticket.assigned_specialty.replace('_', ' ')}
          </span>
        </div>

        <time
          dateTime={ticket.created_at}
          style={{
            fontSize: '0.8rem',
            color: '#64748b',
          }}
        >
          {formatDate(ticket.created_at)}
        </time>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '0.5rem',
          backgroundColor: '#f8fafc',
          padding: '0.65rem 0.85rem',
          borderRadius: '6px',
          fontSize: '0.85rem',
        }}
      >
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '0.75rem' }}>Severidade Relatada</span>
          <strong style={{ color: patient_input.perceived_severity >= 8 ? '#dc2626' : '#1e293b' }}>
            {patient_input.perceived_severity} / 10
          </strong>
        </div>
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '0.75rem' }}>Duração dos Sintomas</span>
          <strong style={{ color: '#1e293b' }}>
            {patient_input.symptom_duration_hours}h ({Math.round(patient_input.symptom_duration_hours / 24 * 10) / 10} dias)
          </strong>
        </div>
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '0.75rem' }}>Status do Ticket</span>
          <strong style={{ color: '#2563eb' }}>{ticket.status}</strong>
        </div>
      </div>

      <div>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase' }}>
          Sintomas Principais
        </span>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.35rem' }}>
          {patient_input.primary_symptoms.map((symptom) => (
            <span
              key={symptom}
              style={{
                backgroundColor: '#eff6ff',
                color: '#1d4ed8',
                border: '1px solid #bfdbfe',
                borderRadius: '4px',
                padding: '0.15rem 0.5rem',
                fontSize: '0.75rem',
                fontWeight: 500,
              }}
            >
              {symptom.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      <div>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase' }}>
          Relato do Paciente
        </span>
        <p
          style={{
            margin: '0.35rem 0 0',
            fontSize: '0.9rem',
            color: '#334155',
            lineHeight: 1.45,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
          title={patient_input.description}
        >
          {patient_input.description}
        </p>
      </div>

      {onFinish && (
        <footer
          style={{
            marginTop: '0.5rem',
            paddingTop: '0.85rem',
            borderTop: '1px solid #f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '0.5rem',
          }}
        >
          {confirming && (
            <button
              type="button"
              onClick={() => setConfirming(false)}
              disabled={isFinishing}
              style={{
                backgroundColor: 'transparent',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                padding: '0.45rem 0.85rem',
                fontSize: '0.85rem',
                color: '#64748b',
                cursor: 'pointer',
              }}
            >
              Cancelar
            </button>
          )}

          <button
            type="button"
            onClick={handleFinishClick}
            disabled={isFinishing}
            aria-label={`Finalizar atendimento do paciente ${ticket.ticket_id}`}
            style={{
              backgroundColor: confirming ? '#15803d' : '#16a34a',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '0.45rem 1rem',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: isFinishing ? 'not-allowed' : 'pointer',
              opacity: isFinishing ? 0.7 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
              transition: 'background-color 0.15s ease',
            }}
          >
            {isFinishing
              ? 'Finalizando...'
              : confirming
              ? 'Confirmar finalização?'
              : 'Finalizar'}
          </button>
        </footer>
      )}
    </article>
  )
}

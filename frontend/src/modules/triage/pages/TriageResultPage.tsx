import type { TriageSubmitResponse, UrgencyLevel } from '../types/triage.types'

interface TriageResultPageProps {
  result: TriageSubmitResponse
  onNewTriage: () => void
}

const URGENCY_CONFIG: Record<
  UrgencyLevel,
  { label: string; color: string; bg: string; border: string; icon: string }
> = {
  EMERGENCIA: {
    label: 'Emergência (Atendimento Imediato)',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.15)',
    border: 'rgba(239, 68, 68, 0.45)',
    icon: '🚨',
  },
  ALTA: {
    label: 'Urgência Alta (Prioritário)',
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.15)',
    border: 'rgba(249, 115, 22, 0.45)',
    icon: '⚠️',
  },
  MEDIA: {
    label: 'Urgência Média (Moderado)',
    color: '#eab308',
    bg: 'rgba(234, 179, 8, 0.15)',
    border: 'rgba(234, 179, 8, 0.45)',
    icon: '⏳',
  },
  BAIXA: {
    label: 'Urgência Baixa (Pouco Urgente)',
    color: '#22c55e',
    bg: 'rgba(34, 197, 94, 0.15)',
    border: 'rgba(34, 197, 94, 0.45)',
    icon: '🟢',
  },
}

export function TriageResultPage({ result, onNewTriage }: TriageResultPageProps) {
  const urgency = URGENCY_CONFIG[result.urgency_level] || {
    label: result.urgency_level,
    color: 'var(--color-primary)',
    bg: 'var(--color-accent-glow)',
    border: 'var(--color-primary)',
    icon: 'ℹ️',
  }

  function formatSpecialty(spec: string) {
    return spec
      .toLowerCase()
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  function formatStatus(status: string) {
    if (status === 'WAITING') return 'Aguardando atendimento médico'
    return status
  }

  const formattedDate = result.created_at
    ? new Date(result.created_at).toLocaleString('pt-BR')
    : new Date().toLocaleString('pt-BR')

  return (
    <div className="triage-result-card">
      <div className="triage-result-card__header">
        <span className="triage-result-card__icon" aria-hidden="true">
          {urgency.icon}
        </span>
        <h2 className="triage-result-card__title">Triagem Concluída com Sucesso</h2>
        <p className="triage-result-card__subtitle">
          Seus dados foram processados com sucesso. Confira abaixo o direcionamento e nível de prioridade.
        </p>
      </div>

      <div
        className="triage-urgency-banner"
        style={{
          backgroundColor: urgency.bg,
          borderColor: urgency.border,
        }}
      >
        <span className="triage-urgency-banner__tag">Classificação de Risco</span>
        <div
          className="triage-urgency-banner__level"
          style={{ color: urgency.color }}
        >
          {urgency.label}
        </div>
      </div>

      <div className="triage-info-grid">
        <div className="triage-info-item">
          <span className="triage-info-item__label">Protocolo (Ticket ID)</span>
          <span className="triage-info-item__value triage-info-item__value--mono">
            {result.ticket_id}
          </span>
        </div>

        <div className="triage-info-item">
          <span className="triage-info-item__label">Especialidade Recomendada</span>
          <span className="triage-info-item__value triage-info-item__value--highlight">
            {formatSpecialty(result.assigned_specialty)}
          </span>
        </div>

        <div className="triage-info-item">
          <span className="triage-info-item__label">Status da Fila</span>
          <span className="triage-info-item__value">
            <span className="triage-status-badge">
              <span className="triage-status-badge__dot" />
              {formatStatus(result.status)}
            </span>
          </span>
        </div>

        <div className="triage-info-item">
          <span className="triage-info-item__label">Registrado em</span>
          <span className="triage-info-item__value">{formattedDate}</span>
        </div>
      </div>

      <div className="triage-result-card__footer">
        <button
          type="button"
          onClick={onNewTriage}
          className="btn btn--primary btn--full-width"
        >
          Iniciar Nova Triagem
        </button>
      </div>
    </div>
  )
}

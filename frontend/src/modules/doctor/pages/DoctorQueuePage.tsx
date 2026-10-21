import { AlertMessage } from '../../../components/ui/AlertMessage'
import { Button } from '../../../components/ui/Button'
import { TicketCard } from '../components/TicketCard'
import { useDoctorQueue } from '../hooks/useDoctorQueue'

export function DoctorQueuePage() {
  const {
    items,
    total,
    loading,
    loadingMore,
    finishingId,
    error,
    errorStatus,
    actionMessage,
    hasMore,
    refresh,
    loadMore,
    finishTicket,
  } = useDoctorQueue()

  return (
    <div
      style={{
        maxWidth: '1080px',
        margin: '0 auto',
        padding: '2rem 1.5rem',
      }}
    >
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2rem',
          borderBottom: '1px solid #e2e8f0',
          paddingBottom: '1.25rem',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: '#0f172a',
              margin: 0,
            }}
          >
            Fila de Atendimento Médico
          </h1>
          <p
            style={{
              fontSize: '0.95rem',
              color: '#64748b',
              margin: '0.25rem 0 0',
            }}
          >
            Atendimentos aguardando avaliação para sua especialidade
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span
            style={{
              fontSize: '0.875rem',
              color: '#475569',
              fontWeight: 500,
            }}
          >
            Total na fila: <strong style={{ color: '#0f172a' }}>{total}</strong>
          </span>
          <Button
            type="button"
            onClick={refresh}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.875rem',
              backgroundColor: '#0284c7',
              color: '#ffffff',
            }}
          >
            {loading ? 'Atualizando...' : 'Atualizar Fila'}
          </Button>
        </div>
      </header>

      {/* Feedback de Ação de Finalização */}
      {actionMessage && (
        <div style={{ marginBottom: '1.5rem' }}>
          <AlertMessage
            type={actionMessage.type}
            message={actionMessage.text}
          />
        </div>
      )}

      {/* Estado de Erro 403 */}
      {error && errorStatus === 403 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <AlertMessage
            type="error"
            message="Acesso restrito: Você não possui autorização ou especialidade clínica válida para acessar esta fila."
          />
        </div>
      )}

      {/* Estado de Erro 429 */}
      {error && errorStatus === 429 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <AlertMessage
            type="error"
            message="Limite de requisições excedido. Por favor, aguarde alguns instantes antes de atualizar novamente."
          />
        </div>
      )}

      {/* Outros Erros */}
      {error && errorStatus !== 403 && errorStatus !== 429 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <AlertMessage type="error" message={error} />
        </div>
      )}

      {/* Loading inicial */}
      {loading && items.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '4rem 1rem',
            color: '#64748b',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              margin: '0 auto 1rem',
              border: '3px solid #e2e8f0',
              borderTopColor: '#0284c7',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <p style={{ fontSize: '1rem', fontWeight: 500 }}>Carregando atendimentos da sua especialidade...</p>
        </div>
      )}

      {/* Lista Vazia */}
      {!loading && items.length === 0 && !error && (
        <div
          style={{
            textAlign: 'center',
            padding: '4rem 1.5rem',
            backgroundColor: '#f8fafc',
            border: '2px dashed #cbd5e1',
            borderRadius: '12px',
          }}
        >
          <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: '0.75rem' }} role="img" aria-label="Sem atendimentos">
            📋
          </span>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#334155', margin: '0 0 0.5rem' }}>
            Nenhum atendimento na fila
          </h2>
          <p style={{ color: '#64748b', maxWidth: '400px', margin: '0 auto 1.5rem', fontSize: '0.9rem' }}>
            Não há novos pacientes aguardando triagem para sua especialidade no momento.
          </p>
          <Button type="button" onClick={refresh} style={{ padding: '0.5rem 1.25rem' }}>
            Verificar Novamente
          </Button>
        </div>
      )}

      {/* Grid de Cards */}
      {items.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {items.map((ticket) => (
            <TicketCard
              key={ticket.ticket_id}
              ticket={ticket}
              onFinish={finishTicket}
              isFinishing={finishingId === ticket.ticket_id}
            />
          ))}
        </div>
      )}

      {/* Botão de Paginação (Carregar mais) */}
      {hasMore && (
        <div
          style={{
            textAlign: 'center',
            marginTop: '2.5rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid #e2e8f0',
          }}
        >
          <Button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            style={{
              padding: '0.75rem 2rem',
              fontSize: '0.95rem',
              backgroundColor: '#f8fafc',
              color: '#0f172a',
              border: '1px solid #cbd5e1',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
          >
            {loadingMore ? 'Carregando mais atendimentos...' : `Carregar mais atendimentos (${items.length} de ${total})`}
          </Button>
        </div>
      )}
    </div>
  )
}

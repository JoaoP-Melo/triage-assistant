import { logout } from '../../auth/services/auth.service'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../../services/api'

export function HomePage() {
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout()
    } catch (err) {
      if (err instanceof ApiError && err.status !== 401) {
        console.error('Logout error:', err)
      }
    } finally {
      navigate('/login')
    }
  }

  return (
    <div className="home-page">
      <header className="home-header">
        <div className="home-header__brand">
          <span className="home-header__logo" aria-hidden="true">⚕</span>
          <span className="home-header__app-name">Triage Assistant</span>
        </div>
        <button className="btn btn--ghost" onClick={handleLogout}>
          Sair
        </button>
      </header>

      <main className="home-main">
        <div className="home-welcome">
          <div className="home-welcome__icon" aria-hidden="true">🩺</div>
          <h1 className="home-welcome__title">Portal do Paciente</h1>
          <p className="home-welcome__subtitle">
            Relate seus sintomas para passar pelo sistema inteligente de classificação e direcionamento médico prioritário.
          </p>
          <div style={{ marginTop: 'var(--space-6)' }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => navigate('/triage')}
              style={{ padding: '0.875rem 2rem', fontSize: 'var(--font-size-base)' }}
            >
              Iniciar Triagem
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

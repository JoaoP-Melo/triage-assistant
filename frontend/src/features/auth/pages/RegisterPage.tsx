import { RegisterForm } from '../components/RegisterForm'

export function RegisterPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span className="auth-card__logo" aria-hidden="true">⚕</span>
          <span className="auth-card__app-name">Triage Assistant</span>
        </div>
        <RegisterForm />
      </div>
    </div>
  )
}

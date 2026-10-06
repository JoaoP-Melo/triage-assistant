import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { RegisterPage } from '../features/auth/pages/RegisterPage'
import { HomePage } from '../features/home/pages/HomePage'
import { ProtectedRoute } from '../features/auth/components/ProtectedRoute'
import { TriageFormPage } from '../modules/triage/pages/TriageFormPage'

export function AppRoutes() {
  return (
    <Routes>
      {/* Redireciona a raiz para /login */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Autenticação */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Área autenticada */}
      <Route path="/home" element={<HomePage />} />

      {/* Triagem de Paciente (protegido por role="patient") */}
      <Route
        path="/triage"
        element={
          <ProtectedRoute role="patient">
            <TriageFormPage />
          </ProtectedRoute>
        }
      />

      {/* Fallback para rotas não encontradas */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

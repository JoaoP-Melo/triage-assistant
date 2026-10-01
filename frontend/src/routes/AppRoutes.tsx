import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { RegisterPage } from '../features/auth/pages/RegisterPage'
import { HomePage } from '../features/home/pages/HomePage'

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

      {/* Fallback para rotas não encontradas */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertMessage } from '../../../components/ui/AlertMessage'
import { Button } from '../../../components/ui/Button'
import { InputField } from '../../../components/ui/InputField'
import { login } from '../services/auth.service'
import { ApiError } from '../../../services/api'

interface FormState {
  email: string
  password: string
}

interface FormErrors {
  email?: string
  password?: string
}

function validate(values: FormState): FormErrors {
  const errors: FormErrors = {}
  if (!values.email.trim()) {
    errors.email = 'E-mail é obrigatório.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.email = 'Informe um e-mail válido.'
  }
  if (!values.password) {
    errors.password = 'Senha é obrigatória.'
  }
  return errors
}

export function LoginForm() {
  const navigate = useNavigate()

  const [values, setValues] = useState<FormState>({ email: '', password: '' })
  const [errors, setErrors] = useState<FormErrors>({})
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    setValues((prev) => ({ ...prev, [name]: value }))
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
    setApiError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const validationErrors = validate(values)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    setApiError(null)

    try {
      await login({ email: values.email, password: values.password })
      navigate('/home')
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message)
      } else {
        setApiError('Erro inesperado. Tente novamente.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h1 className="auth-form__title">Entrar</h1>
      <p className="auth-form__subtitle">Acesse sua conta para continuar</p>

      {apiError && <AlertMessage message={apiError} type="error" />}

      <InputField
        id="login-email"
        label="E-mail"
        type="email"
        name="email"
        value={values.email}
        onChange={handleChange}
        error={errors.email}
        autoComplete="email"
        placeholder="seu@email.com"
      />

      <InputField
        id="login-password"
        label="Senha"
        type="password"
        name="password"
        value={values.password}
        onChange={handleChange}
        error={errors.password}
        autoComplete="current-password"
        placeholder="••••••••"
      />

      <Button type="submit" loading={loading} className="btn--full-width">
        Entrar
      </Button>

      <p className="auth-form__footer">
        Não tem uma conta?{' '}
        <Link to="/register" className="auth-link">
          Criar conta
        </Link>
      </p>
    </form>
  )
}

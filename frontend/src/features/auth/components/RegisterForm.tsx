import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertMessage } from '../../../components/ui/AlertMessage'
import { Button } from '../../../components/ui/Button'
import { InputField } from '../../../components/ui/InputField'
import * as authService from '../services/auth.service'
import { ApiError } from '../../../services/api'

type RoleType = 'patient' | 'doctor'

interface FormState {
  name: string
  email: string
  password1: string
  password2: string
  specialization: string
}

interface FormErrors {
  name?: string
  email?: string
  password1?: string
  password2?: string
  specialization?: string
}

function validate(values: FormState, role: RoleType): FormErrors {
  const errors: FormErrors = {}
  if (!values.name.trim() || values.name.trim().length < 2) {
    errors.name = 'Nome deve ter pelo menos 2 caracteres.'
  }
  if (!values.email.trim()) {
    errors.email = 'E-mail é obrigatório.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.email = 'Informe um e-mail válido.'
  }
  if (!values.password1) {
    errors.password1 = 'Senha é obrigatória.'
  } else if (values.password1.length < 8) {
    errors.password1 = 'A senha deve ter no mínimo 8 caracteres.'
  }
  if (!values.password2) {
    errors.password2 = 'Confirmação de senha é obrigatória.'
  } else if (values.password1 !== values.password2) {
    errors.password2 = 'As senhas não coincidem.'
  }
  if (role === 'doctor') {
    if (!values.specialization.trim()) {
      errors.specialization = 'Especialização é obrigatória.'
    } else if (values.specialization.trim().length < 3) {
      errors.specialization = 'A especialização deve ter no mínimo 3 caracteres.'
    }
  }
  return errors
}

export function RegisterForm() {
  const navigate = useNavigate()

  const [role, setRole] = useState<RoleType>('patient')
  const [values, setValues] = useState<FormState>({
    name: '',
    email: '',
    password1: '',
    password2: '',
    specialization: '',
  })
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

  function handleRoleChange(newRole: RoleType) {
    if (newRole === role) return
    setRole(newRole)
    setApiError(null)
    setErrors((prev) => ({ ...prev, specialization: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const validationErrors = validate(values, role)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    setApiError(null)

    try {
      if (role === 'patient') {
        await authService.registerPatient({
          name: values.name.trim(),
          email: values.email.trim(),
          password1: values.password1,
          password2: values.password2,
        })
      } else {
        await authService.registerDoctor({
          name: values.name.trim(),
          email: values.email.trim(),
          password1: values.password1,
          password2: values.password2,
          specialization: values.specialization.trim(),
        })
      }
      navigate('/login')
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
      <h1 className="auth-form__title">Criar conta</h1>
      <p className="auth-form__subtitle">Preencha os dados para se cadastrar</p>

      <div className="role-selector" role="group" aria-label="Perfil de cadastro">
        <button
          type="button"
          className={`role-selector__btn${role === 'patient' ? ' role-selector__btn--active' : ''}`}
          onClick={() => handleRoleChange('patient')}
        >
          Paciente
        </button>
        <button
          type="button"
          className={`role-selector__btn${role === 'doctor' ? ' role-selector__btn--active' : ''}`}
          onClick={() => handleRoleChange('doctor')}
        >
          Médico
        </button>
      </div>

      {apiError && <AlertMessage message={apiError} type="error" />}

      <InputField
        id="register-name"
        label={role === 'doctor' ? 'Nome completo do médico' : 'Nome completo'}
        type="text"
        name="name"
        value={values.name}
        onChange={handleChange}
        error={errors.name}
        autoComplete="name"
        placeholder={role === 'doctor' ? 'Dr(a). Seu Nome' : 'Seu nome'}
      />

      {role === 'doctor' && (
        <InputField
          id="register-specialization"
          label="Especialização médica"
          type="text"
          name="specialization"
          value={values.specialization}
          onChange={handleChange}
          error={errors.specialization}
          placeholder="Ex.: Cardiologia, Clínica Geral"
        />
      )}

      <InputField
        id="register-email"
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
        id="register-password1"
        label="Senha"
        type="password"
        name="password1"
        value={values.password1}
        onChange={handleChange}
        error={errors.password1}
        autoComplete="new-password"
        placeholder="Mínimo 8 caracteres"
      />

      <InputField
        id="register-password2"
        label="Confirmar senha"
        type="password"
        name="password2"
        value={values.password2}
        onChange={handleChange}
        error={errors.password2}
        autoComplete="new-password"
        placeholder="Repita a senha"
      />

      <Button type="submit" loading={loading} className="btn--full-width">
        Criar conta
      </Button>

      <p className="auth-form__footer">
        Já tem uma conta?{' '}
        <Link to="/login" className="auth-link">
          Entrar
        </Link>
      </p>
    </form>
  )
}

import { ApiError, apiClient, setAccessToken } from '../../../services/api'
import type {
  LoginPayload,
  LoginResponse,
  LogoutResponse,
  RefreshResponse,
  RegisterDoctorRequest,
  RegisterPayload,
  RegisterResponse,
} from '../types/auth.types'

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  return apiClient.post<RegisterResponse>('/auth/register', payload)
}

export const registerPatient = register

export async function registerDoctor(
  payload: RegisterDoctorRequest
): Promise<RegisterResponse> {
  return apiClient.post<RegisterResponse>('/auth/register/doctor', payload)
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const data = await apiClient.post<LoginResponse>('/auth/login', payload)
  setAccessToken(data.access_token)
  return data
}

export async function refreshToken(): Promise<RefreshResponse> {
  try {
    const data = await apiClient.post<RefreshResponse>('/auth/refresh')
    setAccessToken(data.access_token)
    return data
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      setAccessToken(null)
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('triage_user')
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login'
        }
      }
    }
    throw error
  }
}

export async function logout(): Promise<LogoutResponse> {
  const data = await apiClient.post<LogoutResponse>('/auth/logout')
  setAccessToken(null)
  return data
}

import { apiClient, setAccessToken } from '../../../services/api'
import type {
  LoginPayload,
  LoginResponse,
  LogoutResponse,
  RefreshResponse,
  RegisterPayload,
  RegisterResponse,
} from '../types/auth.types'

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  return apiClient.post<RegisterResponse>('/auth/register', payload)
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const data = await apiClient.post<LoginResponse>('/auth/login', payload)
  setAccessToken(data.access_token)
  return data
}

export async function refreshToken(): Promise<RefreshResponse> {
  const data = await apiClient.post<RefreshResponse>('/auth/refresh')
  setAccessToken(data.access_token)
  return data
}

export async function logout(): Promise<LogoutResponse> {
  const data = await apiClient.post<LogoutResponse>('/auth/logout')
  setAccessToken(null)
  return data
}

export interface RegisterPayload {
  name: string
  email: string
  password1: string
  password2: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface UserInfo {
  name: string
  role: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

export interface RegisterResponse {
  message: string
}

export interface RefreshResponse {
  access_token: string
  token_type: string
}

export interface LogoutResponse {
  message: string
}

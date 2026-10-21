/**
 * Cliente HTTP centralizado para comunicacao com o backend FastAPI.
 * O Access Token é mantido apenas em memória — nunca em localStorage/sessionStorage.
 */

const API_URL = import.meta.env.VITE_API_URL as string

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

export class ApiError extends Error {
  public readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers: customHeaders, ...rest } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  }

  if (accessToken) {
    ; (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...rest,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const json = (await response.json()) as { detail?: string }
      detail = json.detail ?? detail
    } catch {
      // mantém a mensagem padrão
    }
    throw new ApiError(detail, response.status)
  }

  const text = await response.text()
  return (text ? JSON.parse(text) : undefined) as T
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', body }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PATCH', body }),
}

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { UserInfo, LoginResponse } from '../types/auth.types'
import { getAccessToken, setAccessToken } from '../../../services/api'

interface AuthContextType {
  user: UserInfo | null
  token: string | null
  isAuthenticated: boolean
  loginUser: (data: LoginResponse) => void
  logoutUser: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const USER_STORAGE_KEY = 'triage_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(() => {
    try {
      const stored = sessionStorage.getItem(USER_STORAGE_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const [token, setTokenState] = useState<string | null>(getAccessToken())

  useEffect(() => {
    if (user) {
      sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    } else {
      sessionStorage.removeItem(USER_STORAGE_KEY)
    }
  }, [user])

  function loginUser(data: LoginResponse) {
    setAccessToken(data.access_token)
    setTokenState(data.access_token)
    setUser(data.user)
  }

  function logoutUser() {
    setAccessToken(null)
    setTokenState(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token || !!user,
        loginUser,
        logoutUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider.')
  }
  return context
}

/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { onUnauthorized } from '../lib/api'
import {
  getMe,
  getToken,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from '../services/authService'

const AuthContext = createContext(null)

function normalizeError(error) {
  if (error?.status === 401) {
    return 'Email ou senha inválidos.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => getToken())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const clearSession = useCallback(() => {
    logoutRequest()
    setUser(null)
    setToken(null)
    setError('')
    setLoading(false)
  }, [])

  const refreshMe = useCallback(async () => {
    const storedToken = getToken()

    if (!storedToken) {
      clearSession()
      return null
    }

    const currentUser = await getMe()
    setUser(currentUser)
    setToken(storedToken)

    return currentUser
  }, [clearSession])

  useEffect(() => {
    return onUnauthorized(clearSession)
  }, [clearSession])

  useEffect(() => {
    let isMounted = true

    async function restoreSession() {
      const storedToken = getToken()

      if (!storedToken) {
        if (isMounted) {
          setLoading(false)
        }
        return
      }

      try {
        const currentUser = await getMe()

        if (!isMounted) {
          return
        }

        setUser(currentUser)
        setToken(storedToken)
      } catch {
        if (isMounted) {
          clearSession()
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      isMounted = false
    }
  }, [clearSession])

  const login = useCallback(async (email, password) => {
    setError('')

    try {
      const tokenData = await loginRequest(email, password)
      setToken(tokenData.access_token)

      const currentUser = await getMe()
      setUser(currentUser)

      return currentUser
    } catch (loginError) {
      logoutRequest()
      setUser(null)
      setToken(null)
      setError(normalizeError(loginError))
      throw loginError
    }
  }, [])

  const register = useCallback(async (data) => {
    setError('')

    try {
      return await registerRequest(data)
    } catch (registerError) {
      setError(normalizeError(registerError))
      throw registerError
    }
  }, [])

  const logout = useCallback(() => {
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({
      error,
      isAuthenticated: Boolean(user && token),
      loading,
      login,
      logout,
      refreshMe,
      register,
      token,
      user,
    }),
    [error, loading, login, logout, refreshMe, register, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider.')
  }

  return context
}

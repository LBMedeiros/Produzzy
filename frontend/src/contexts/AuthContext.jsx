/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { flushSync } from 'react-dom'
import { onUnauthorized } from '../lib/api'
import {
  getMe,
  getToken,
  login as loginRequest,
  loginWithGoogle as loginWithGoogleRequest,
  logout as logoutRequest,
  changeEmail as changeEmailRequest,
  removeAvatar as removeAvatarRequest,
  register as registerRequest,
  updateProfile as updateProfileRequest,
  uploadAvatar as uploadAvatarRequest,
} from '../services/authService'

const AuthContext = createContext(null)

function normalizeError(error) {
  if (error?.status === 401) {
    return 'Email ou senha inválidos.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

function shouldUseAuthViewTransition() {
  return Boolean(
    document.startViewTransition &&
      !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  )
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

  const login = useCallback(async (email, password, options = {}) => {
    setError('')

    try {
      const authData = await loginRequest(email, password, options)
      const currentUser = authData.user
      const commitSession = () => {
        setToken(authData.access_token)
        setUser(currentUser)
      }

      if (shouldUseAuthViewTransition()) {
        document.startViewTransition(() => {
          flushSync(commitSession)
        })
      } else {
        commitSession()
      }

      return currentUser
    } catch (loginError) {
      logoutRequest()
      setUser(null)
      setToken(null)
      setError(normalizeError(loginError))
      throw loginError
    }
  }, [])

  const loginWithGoogle = useCallback(async (code, redirectUri, options = {}) => {
    setError('')

    try {
      const authData = await loginWithGoogleRequest(code, redirectUri, options)
      const currentUser = authData.user
      const commitSession = () => {
        setToken(authData.access_token)
        setUser(currentUser)
      }

      if (shouldUseAuthViewTransition()) {
        document.startViewTransition(() => {
          flushSync(commitSession)
        })
      } else {
        commitSession()
      }

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

  const updateProfile = useCallback(async (data) => {
    const updatedUser = await updateProfileRequest(data)

    setUser(updatedUser)

    return updatedUser
  }, [])

  const changeEmail = useCallback(async (data) => {
    const result = await changeEmailRequest(data)

    setUser(result.user)
    setToken(result.access_token)

    return result
  }, [])

  const uploadAvatar = useCallback(async (file) => {
    const updatedUser = await uploadAvatarRequest(file)

    setUser(updatedUser)

    return updatedUser
  }, [])

  const removeAvatar = useCallback(async () => {
    const updatedUser = await removeAvatarRequest()

    setUser(updatedUser)

    return updatedUser
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
      loginWithGoogle,
      logout,
      changeEmail,
      removeAvatar,
      refreshMe,
      register,
      token,
      updateProfile,
      uploadAvatar,
      user,
    }),
    [
      changeEmail,
      error,
      loading,
      login,
      loginWithGoogle,
      logout,
      removeAvatar,
      refreshMe,
      register,
      token,
      updateProfile,
      uploadAvatar,
      user,
    ],
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

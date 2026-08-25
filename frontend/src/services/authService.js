import {
  clearStoredToken,
  getStoredToken,
  request,
  setStoredToken,
} from '../lib/api'

export async function login(email, password, options = {}) {
  const formData = new URLSearchParams()
  formData.set('username', email.trim())
  formData.set('password', password)
  formData.set('grant_type', 'password')
  formData.set('client_id', '')
  formData.set('client_secret', '')

  const tokenData = await request('/auth/token', {
    body: formData,
    method: 'POST',
    skipAuth: true,
  })

  setStoredToken(tokenData.access_token, {
    rememberMe: Boolean(options.rememberMe),
  })

  return tokenData
}

export async function loginWithGoogle(code, redirectUri, options = {}) {
  const tokenData = await request('/auth/google', {
    body: {
      code,
      redirect_uri: redirectUri,
    },
    headers: {
      'X-Requested-With': 'XmlHttpRequest',
    },
    method: 'POST',
    skipAuth: true,
  })

  setStoredToken(tokenData.access_token, {
    rememberMe: Boolean(options.rememberMe),
  })

  return tokenData
}

export function register(data) {
  return request('/auth/register', {
    body: data,
    method: 'POST',
    skipAuth: true,
  })
}

export function getMe() {
  return request('/auth/me')
}

export function getToken() {
  return getStoredToken()
}

export function logout() {
  clearStoredToken()
}

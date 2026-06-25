export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

const TOKEN_STORAGE_KEY = 'produzzy_access_token'
const unauthorizedHandlers = new Set()

export class ApiError extends Error {
  constructor(message, { status = 0, data = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return `${BASE_URL}${normalizedPath}`
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function onUnauthorized(handler) {
  unauthorizedHandlers.add(handler)

  return () => unauthorizedHandlers.delete(handler)
}

async function readResponse(response) {
  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  const text = await response.text()

  return text || null
}

function getErrorMessage(data, fallback) {
  if (typeof data === 'string' && data.trim()) {
    return data
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(' ')
  }

  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (typeof data?.message === 'string') {
    return data.message
  }

  return fallback
}

export async function request(path, options = {}) {
  const {
    body,
    headers = {},
    skipAuth = false,
    token = getStoredToken(),
    ...fetchOptions
  } = options

  const requestHeaders = new Headers(headers)
  let requestBody = body

  if (!requestHeaders.has('Accept')) {
    requestHeaders.set('Accept', 'application/json')
  }

  if (
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    typeof body !== 'string'
  ) {
    requestHeaders.set('Content-Type', 'application/json')
    requestBody = JSON.stringify(body)
  }

  if (body instanceof URLSearchParams && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/x-www-form-urlencoded')
  }

  if (!skipAuth && token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  let response
  let data

  try {
    response = await fetch(apiUrl(path), {
      ...fetchOptions,
      body: requestBody,
      headers: requestHeaders,
    })
    data = await readResponse(response)
  } catch (error) {
    throw new ApiError('Não foi possível conectar ao servidor.', {
      data: error,
      status: 0,
    })
  }

  if (!response.ok) {
    const message = getErrorMessage(data, 'Não foi possível concluir a solicitação.')

    if (response.status === 401) {
      unauthorizedHandlers.forEach((handler) => handler())
    }

    throw new ApiError(message, {
      data,
      status: response.status,
    })
  }

  return data
}

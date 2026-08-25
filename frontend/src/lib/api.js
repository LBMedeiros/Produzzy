export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

const TOKEN_STORAGE_KEY = 'produzzy_access_token'
const unauthorizedHandlers = new Set()
const USER_FACING_ERROR_MESSAGES = {
  'An active product with this name already exists in this workspace.':
    'Já existe um produto ativo com esse nome neste workspace.',
  'Another active category with this name already exists in this workspace.':
    'Já existe uma categoria ativa com esse nome neste workspace.',
  'Another active product with this name already exists in this workspace.':
    'Já existe outro produto ativo com esse nome neste workspace.',
  'Cannot move stock for an inactive product.':
    'Não é possível movimentar estoque de um produto inativo.',
  'Restore the category before restoring this product.':
    'Restaure a categoria antes de restaurar este produto.',
}

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
  const sessionToken = sessionStorage.getItem(TOKEN_STORAGE_KEY)
  const persistentToken = localStorage.getItem(TOKEN_STORAGE_KEY)

  if (sessionToken && persistentToken) {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }

  return sessionToken || persistentToken
}

export function setStoredToken(token, { rememberMe = false } = {}) {
  clearStoredToken()

  if (!token) {
    return
  }

  if (rememberMe) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    return
  }

  sessionStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  sessionStorage.removeItem(TOKEN_STORAGE_KEY)
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
  function normalizeMessage(message) {
    return USER_FACING_ERROR_MESSAGES[message] ?? message
  }

  if (typeof data === 'string' && data.trim()) {
    return normalizeMessage(data)
  }

  if (Array.isArray(data?.detail)) {
    const message = data.detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(' ')

    return normalizeMessage(message)
  }

  if (typeof data?.detail === 'string') {
    return normalizeMessage(data.detail)
  }

  if (typeof data?.message === 'string') {
    return normalizeMessage(data.message)
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
      clearStoredToken()
      unauthorizedHandlers.forEach((handler) => handler())
    }

    throw new ApiError(message, {
      data,
      status: response.status,
    })
  }

  return data
}

export async function requestBlob(path, options = {}) {
  const {
    headers = {},
    skipAuth = false,
    token = getStoredToken(),
    ...fetchOptions
  } = options

  const requestHeaders = new Headers(headers)

  if (!requestHeaders.has('Accept')) {
    requestHeaders.set('Accept', 'image/png,*/*')
  }

  if (!skipAuth && token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  let response

  try {
    response = await fetch(apiUrl(path), {
      ...fetchOptions,
      headers: requestHeaders,
    })
  } catch (error) {
    throw new ApiError('Não foi possível conectar ao servidor.', {
      data: error,
      status: 0,
    })
  }

  if (!response.ok) {
    const data = await readResponse(response)
    const message = getErrorMessage(data, 'Não foi possível baixar o arquivo.')

    if (response.status === 401) {
      clearStoredToken()
      unauthorizedHandlers.forEach((handler) => handler())
    }

    throw new ApiError(message, {
      data,
      status: response.status,
    })
  }

  return response.blob()
}

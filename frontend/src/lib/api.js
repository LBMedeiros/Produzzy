export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return `${BASE_URL}${normalizedPath}`
}

// Real authenticated requests will be added when the frontend starts consuming
// the FastAPI endpoints.

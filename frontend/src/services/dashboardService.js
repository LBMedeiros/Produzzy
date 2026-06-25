import { request } from '../lib/api'

function withQuery(path, params = {}) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value)
    }
  })

  const queryString = query.toString()

  return queryString ? `${path}?${queryString}` : path
}

export function getDashboardSummary(workspaceId) {
  return request(`/workspaces/${workspaceId}/dashboard/summary`)
}

export function listLowStockProducts(workspaceId, options = {}) {
  const { limit = 5, page = 1 } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/products/low-stock`, {
      limit,
      page,
    }),
  )
}

export function listRecentActivity(workspaceId, options = {}) {
  const { limit = 6, page = 1 } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/audit-logs`, {
      limit,
      page,
    }),
  )
}

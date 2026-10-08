import { request } from '../lib/api'
import { fetchAllPages } from '../lib/pagination'

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

export function listReplenishments(workspaceId, params = {}) {
  const { limit = 20, page = 1, status } = params

  return request(
    withQuery(`/workspaces/${workspaceId}/replenishments`, {
      limit,
      page,
      status,
    }),
  )
}

// Every matching request, across all API pages (the API caps a page at 100).
export function listAllReplenishments(workspaceId, params = {}) {
  return fetchAllPages((pageOptions) =>
    listReplenishments(workspaceId, { ...params, ...pageOptions }),
  )
}

export function createReplenishment(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/replenishments`, {
    body: data,
    method: 'POST',
  })
}

export function updateReplenishment(workspaceId, requestId, data) {
  return request(`/workspaces/${workspaceId}/replenishments/${requestId}`, {
    body: data,
    method: 'PATCH',
  })
}

export function getReplenishment(workspaceId, requestId) {
  return request(`/workspaces/${workspaceId}/replenishments/${requestId}`)
}

export function assignReplenishmentToMe(workspaceId, requestId) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/assignees/me`,
    { method: 'POST' },
  )
}

export function unassignReplenishmentFromMe(workspaceId, requestId) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/assignees/me`,
    { method: 'DELETE' },
  )
}

export function assignReplenishmentMember(workspaceId, requestId, userId) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/assignees/${userId}`,
    { method: 'POST' },
  )
}

export function removeReplenishmentMember(workspaceId, requestId, userId) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/assignees/${userId}`,
    { method: 'DELETE' },
  )
}

export function listReplenishmentMessages(workspaceId, requestId) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/messages`,
  )
}

export function createReplenishmentMessage(workspaceId, requestId, body) {
  return request(
    `/workspaces/${workspaceId}/replenishments/${requestId}/messages`,
    { body: { body }, method: 'POST' },
  )
}

import { request } from '../lib/api'

// Stock movement requests: a Solicitante asks for an entrada/saída and
// Operação and up approve (moving the stock) or reject it.

function basePath(workspaceId) {
  return `/workspaces/${workspaceId}/stock-requests`
}

// status: 'pending' (default), 'closed', 'all', 'approved', 'rejected', 'canceled'.
export function listStockRequests(workspaceId, { limit = 100, status = 'pending' } = {}) {
  const query = new URLSearchParams({ limit: String(limit), status })

  return request(`${basePath(workspaceId)}?${query.toString()}`)
}

export function createStockRequest(workspaceId, data) {
  return request(basePath(workspaceId), {
    body: data,
    method: 'POST',
  })
}

export function approveStockRequest(workspaceId, requestId, data = {}) {
  return request(`${basePath(workspaceId)}/${requestId}/approve`, {
    body: data,
    method: 'POST',
  })
}

export function rejectStockRequest(workspaceId, requestId, note) {
  return request(`${basePath(workspaceId)}/${requestId}/reject`, {
    body: { note },
    method: 'POST',
  })
}

export function cancelStockRequest(workspaceId, requestId) {
  return request(`${basePath(workspaceId)}/${requestId}/cancel`, {
    method: 'POST',
  })
}

export function listStockRequestMessages(workspaceId, requestId) {
  return request(`${basePath(workspaceId)}/${requestId}/messages`)
}

export function createStockRequestMessage(workspaceId, requestId, body) {
  return request(`${basePath(workspaceId)}/${requestId}/messages`, {
    body: { body },
    method: 'POST',
  })
}

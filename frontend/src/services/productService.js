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

export function listProducts(workspaceId, options = {}) {
  const { category, limit = 100, page = 1, search, status = 'active' } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/products`, {
      category,
      limit,
      page,
      search,
      status,
    }),
  )
}

export function listLowStockProducts(workspaceId, options = {}) {
  const { limit = 100, page = 1 } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/products/low-stock`, {
      limit,
      page,
    }),
  )
}

export function getProduct(workspaceId, productId, options = {}) {
  const { includeDeleted = false } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/products/${productId}`, {
      include_deleted: includeDeleted,
    }),
  )
}

export function createProduct(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/products`, {
    body: data,
    method: 'POST',
  })
}

export function updateProduct(workspaceId, productId, data) {
  return request(`/workspaces/${workspaceId}/products/${productId}`, {
    body: data,
    method: 'PATCH',
  })
}

export function deleteProduct(workspaceId, productId) {
  return request(`/workspaces/${workspaceId}/products/${productId}`, {
    method: 'DELETE',
  })
}

export function restoreProduct(workspaceId, productId) {
  return request(`/workspaces/${workspaceId}/products/${productId}/restore`, {
    method: 'POST',
  })
}

export function createStockMovement(workspaceId, productId, data) {
  return request(`/workspaces/${workspaceId}/products/${productId}/stock`, {
    body: data,
    method: 'POST',
  })
}

export function listProductStockMovements(workspaceId, productId, options = {}) {
  const { limit = 20, page = 1 } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/products/${productId}/stock-movements`, {
      limit,
      page,
    }),
  )
}

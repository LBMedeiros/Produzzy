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

export function listCategories(workspaceId, options = {}) {
  const {
    limit = 100,
    page = 1,
    search,
    status = 'active',
  } = options

  return request(
    withQuery(`/workspaces/${workspaceId}/categories`, {
      limit,
      page,
      search,
      status,
    }),
  )
}

export function createCategory(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/categories`, {
    body: data,
    method: 'POST',
  })
}

export function updateCategory(workspaceId, categoryId, data) {
  return request(`/workspaces/${workspaceId}/categories/${categoryId}`, {
    body: data,
    method: 'PATCH',
  })
}

export function deleteCategory(workspaceId, categoryId) {
  return request(`/workspaces/${workspaceId}/categories/${categoryId}`, {
    method: 'DELETE',
  })
}

export function restoreCategory(workspaceId, categoryId) {
  return request(
    `/workspaces/${workspaceId}/categories/${categoryId}/restore`,
    {
      method: 'POST',
    },
  )
}

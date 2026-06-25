import { request } from '../lib/api'

export function listWorkspaces() {
  return request('/workspaces')
}

export function createWorkspace(data) {
  return request('/workspaces', {
    body: data,
    method: 'POST',
  })
}

export function getWorkspace(id) {
  return request(`/workspaces/${id}`)
}

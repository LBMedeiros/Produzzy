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

export function updateWorkspace(workspaceId, data) {
  return request(`/workspaces/${workspaceId}`, {
    body: data,
    method: 'PATCH',
  })
}

export function listWorkspaceMembers(workspaceId) {
  return request(`/workspaces/${workspaceId}/members?limit=100`)
}

export function listWorkspaceInvites(workspaceId) {
  return request(`/workspaces/${workspaceId}/invites?limit=100`)
}

export function updateWorkspaceMember(workspaceId, memberId, data) {
  return request(`/workspaces/${workspaceId}/members/${memberId}`, {
    body: data,
    method: 'PATCH',
  })
}

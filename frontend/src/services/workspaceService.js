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

export function deleteWorkspace(workspaceId) {
  return request(`/workspaces/${workspaceId}`, {
    method: 'DELETE',
  })
}

export function listWorkspaceMembers(workspaceId) {
  return request(`/workspaces/${workspaceId}/members?limit=100`)
}

export function listWorkspaceInvites(workspaceId) {
  return request(`/workspaces/${workspaceId}/invites?limit=100`)
}

export function listWorkspaceInviteLinks(workspaceId) {
  return request(`/workspaces/${workspaceId}/invite-links?limit=100`)
}

export function createWorkspaceInvite(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/invites`, {
    body: data,
    method: 'POST',
  })
}

export function createWorkspaceInviteLink(workspaceId) {
  return request(`/workspaces/${workspaceId}/invite-links`, {
    method: 'POST',
  })
}

export function acceptWorkspaceInvite(token) {
  return request(`/invites/${encodeURIComponent(token)}/accept`, {
    method: 'POST',
  })
}

export function acceptWorkspaceInviteLink(token) {
  return request(`/invite-links/${encodeURIComponent(token)}/accept`, {
    method: 'POST',
  })
}

export function revokeWorkspaceInvite(workspaceId, inviteId) {
  return request(`/workspaces/${workspaceId}/invites/${inviteId}/revoke`, {
    method: 'POST',
  })
}

export function revokeWorkspaceInviteLink(workspaceId, linkId) {
  return request(`/workspaces/${workspaceId}/invite-links/${linkId}/revoke`, {
    method: 'POST',
  })
}

export function updateWorkspaceMember(workspaceId, memberId, data) {
  return request(`/workspaces/${workspaceId}/members/${memberId}`, {
    body: data,
    method: 'PATCH',
  })
}

export function deleteWorkspaceMember(workspaceId, memberId) {
  return request(`/workspaces/${workspaceId}/members/${memberId}`, {
    method: 'DELETE',
  })
}

import { request } from '../lib/api'

export function searchWorkspace(workspaceId, query) {
  const params = new URLSearchParams({ q: query })

  return request(`/workspaces/${workspaceId}/search?${params.toString()}`)
}

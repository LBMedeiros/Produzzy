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

// `tz` makes the per-day chart follow the user's calendar days.
export function getDashboard(workspaceId, options = {}) {
  const tz = options.tz ?? Intl.DateTimeFormat().resolvedOptions().timeZone

  return request(withQuery(`/workspaces/${workspaceId}/dashboard`, { tz }))
}


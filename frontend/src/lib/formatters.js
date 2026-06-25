export function getInitials(name, fallback = 'US') {
  if (!name) {
    return fallback
  }

  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

  return initials || fallback
}

export function getFirstName(name) {
  return name?.trim().split(/\s+/)[0] ?? 'Usuário'
}

export function getWorkspaceRole(user, workspace) {
  if (workspace?.owner_id === user?.id) {
    return 'Owner'
  }

  return 'Membro'
}

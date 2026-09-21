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

export const workspaceRoleLabels = {
  admin: 'Admin',
  employee: 'Funcionário',
  member: 'Membro',
  owner: 'Dono',
  viewer: 'Visualizador',
}

export function formatWorkspaceRole(role, fallback = 'Membro') {
  const normalizedRole = String(role ?? '').toLowerCase()

  return workspaceRoleLabels[normalizedRole] ?? fallback
}

export function getWorkspaceRoleValue(user, workspace) {
  if (workspace?.owner_id === user?.id) {
    return 'owner'
  }

  const role =
    workspace?.current_user_role ??
    workspace?.membership_role ??
    workspace?.role ??
    ''

  return String(role).toLowerCase()
}

export function getWorkspaceRole(user, workspace) {
  return formatWorkspaceRole(getWorkspaceRoleValue(user, workspace))
}

// Fixed catalog of cosmetic member titles the workspace owner can assign.
// Mirror of the backend WORKSPACE_MEMBER_TITLES (crud/base.py) — keep in sync.
export const memberTitleOptions = [
  'Sócio',
  'Gerente',
  'Supervisor',
  'Coordenador',
  'Financeiro',
  'Comprador',
  'Estoquista',
  'Vendedor',
  'Produção',
  'Assistente',
]

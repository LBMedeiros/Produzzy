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
  admin: 'Administração',
  employee: 'Operação',
  manager: 'Gestão',
  member: 'Membro',
  owner: 'Responsável pelo workspace',
  requester: 'Solicitante',
  viewer: 'Visualizador',
}

// What each access level can do, shown next to the cargo select and in the
// "O que cada cargo pode fazer?" legend.
export const workspaceRoleDescriptions = {
  admin: 'Acesso completo, incluindo membros, cargos e convites.',
  employee: 'Movimenta o estoque e cuida das reposições.',
  manager: 'Acesso completo, exceto membros, cargos e convites.',
  owner: 'Acesso total. Pode transferir a posse do workspace.',
  requester: 'Consulta tudo e abre necessidades de reposição.',
  viewer: 'Apenas consulta.',
}

// Access levels from most to least access (owner excluded: it is the crown,
// not a cargo).
export const workspaceRoleLevels = ['admin', 'manager', 'employee', 'requester', 'viewer']

// Levels an Administração member can give and manage; only the owner hands
// out Administração cargos. Mirror of ADMIN_MEMBER_TARGET_ROLES (crud/base.py).
export const adminManagedRoles = new Set(['manager', 'employee', 'requester', 'viewer'])

// Who can open replenishment needs / work on them. Mirror of
// REPLENISHMENT_CREATE_ROLES and REPLENISHMENT_UPDATE_ROLES (crud/base.py).
export const replenishmentCreateRoles = new Set([
  'owner',
  'admin',
  'manager',
  'employee',
  'requester',
])
export const replenishmentOperateRoles = new Set(['owner', 'admin', 'manager', 'employee'])

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

// Fixed catalog of cargos and the access level each one grants.
// Mirror of the backend WORKSPACE_MEMBER_TITLE_ROLES (crud/base.py) — keep in sync.
export const memberTitleRoles = {
  CEO: 'admin',
  Sócio: 'admin',
  Gerente: 'admin',
  Supervisor: 'manager',
  Coordenador: 'manager',
  'Secretário(a)': 'manager',
  Produção: 'employee',
  Estoquista: 'employee',
  Financeiro: 'requester',
  Comprador: 'requester',
  Vendedor: 'requester',
  Assistente: 'requester',
  Atendente: 'requester',
  Visualizador: 'viewer',
}

export const memberTitleOptions = Object.keys(memberTitleRoles)

export function getTitleRole(title) {
  return memberTitleRoles[title] ?? null
}

// Cargo options for a SelectMenu, grouped by access level. `allowedRoles`
// limits the levels offered (e.g. an admin cannot hand out Administração).
export function getMemberTitleSelectOptions(allowedRoles) {
  return workspaceRoleLevels
    .filter((role) => !allowedRoles || allowedRoles.has(role))
    .flatMap((role) =>
      memberTitleOptions
        .filter((title) => memberTitleRoles[title] === role)
        .map((title) => ({
          group: workspaceRoleLabels[role],
          label: title,
          value: title,
        })),
    )
}

// A member (never the owner) whose cargo is missing or does not match their
// access level — legacy members from before cargos defined permissions.
export function memberNeedsTitle(member) {
  if (!member || member.role === 'owner') {
    return false
  }

  return getTitleRole(member.title) !== member.role
}

export const auditActionLabels = {
  'category.created': 'Categoria criada',
  'category.deleted': 'Categoria removida',
  'category.restored': 'Categoria restaurada',
  'category.updated': 'Categoria atualizada',
  'invite.accepted': 'Convite aceito',
  'invite.created': 'Convite enviado',
  'invite.expired': 'Convite expirado',
  'invite.revoked': 'Convite revogado',
  'invite_link.accepted': 'Convite por link aceito',
  'invite_link.created': 'Link de convite criado',
  'invite_link.expired': 'Link de convite expirado',
  'invite_link.revoked': 'Link de convite revogado',
  'member.removed': 'Membro removido',
  'member.role_updated': 'Permissão de membro atualizada',
  'member.title_updated': 'Cargo de membro atualizado',
  'product.created': 'Produto criado',
  'product.deleted': 'Produto enviado para lixeira',
  'product.image_removed': 'Foto do produto removida',
  'product.image_updated': 'Foto do produto atualizada',
  'product.restored': 'Produto restaurado',
  'product.updated': 'Produto atualizado',
  'replenishment.assignee_added': 'Responsável adicionado à reposição',
  'replenishment.assignee_removed': 'Responsável removido da reposição',
  'replenishment.canceled': 'Necessidade de reposição cancelada',
  'replenishment.completed': 'Necessidade de reposição concluída',
  'replenishment.created': 'Necessidade de reposição criada',
  'replenishment.stocked': 'Entrada da reposição registrada',
  'replenishment.updated': 'Necessidade de reposição atualizada',
  'stock.movement_created': 'Estoque movimentado',
  'workspace.created': 'Workspace criado',
  'workspace.ownership_transferred': 'Posse do workspace transferida',
  'workspace.updated': 'Workspace atualizado',
}

export const auditEntityLabels = {
  category: 'Categoria',
  product: 'Produto',
  replenishment_request: 'Reposição',
  stock_movement: 'Movimento de estoque',
  workspace: 'Workspace',
  workspace_invite: 'Convite',
  workspace_invite_link: 'Link de convite',
  workspace_member: 'Membro',
}

export function humanizeAuditAction(action) {
  if (auditActionLabels[action]) {
    return auditActionLabels[action]
  }

  // Fallback for any unmapped action: strip the "domain." prefix and de-snake.
  const readable = String(action ?? '')
    .split('.')
    .pop()
    .replace(/_/g, ' ')
    .trim()

  return readable
    ? readable.charAt(0).toUpperCase() + readable.slice(1)
    : 'Atividade'
}

// Case- and accent-insensitive text for local searches ("Capitão" ~ "capitao").
export function normalizeSearchText(value) {
  return (value ?? '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

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
  'member.role_updated': 'Papel de membro atualizado',
  'member.title_updated': 'Cargo de membro atualizado',
  'product.created': 'Produto criado',
  'product.deleted': 'Produto enviado para lixeira',
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

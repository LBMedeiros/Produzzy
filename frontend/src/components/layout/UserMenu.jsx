import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getInitials, getWorkspaceRole } from '../../lib/formatters'

function UserMenu({ user }) {
  const { logout } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const role = getWorkspaceRole(user, activeWorkspace)

  return (
    <div className="user-menu" role="menu" aria-label="Menu do usuário">
      <div className="user-menu__profile">
        <div className="avatar avatar--light">{getInitials(user?.name)}</div>
        <div>
          <strong>{user?.name ?? 'Usuário'}</strong>
          {user?.email ? <span>{user.email}</span> : null}
        </div>
      </div>
      <div className="user-menu__meta">
        <span>Cargo</span>
        <strong>{role}</strong>
      </div>
      <button type="button" onClick={logout} role="menuitem">
        Sair
      </button>
    </div>
  )
}

export default UserMenu

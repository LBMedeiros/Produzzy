import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getWorkspaceRole } from '../../lib/formatters'
import UserAvatar from '../ui/UserAvatar'

function UserMenu({ user }) {
  const { logout } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const role = getWorkspaceRole(user, activeWorkspace)

  return (
    <div className="user-menu" role="menu" aria-label="Menu do usuário">
      <div className="user-menu__profile">
        <UserAvatar
          className="avatar--light"
          name={user?.name}
          src={user?.avatar_url}
        />
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

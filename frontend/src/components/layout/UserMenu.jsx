import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { formatWorkspaceRole, getWorkspaceRoleValue } from '../../lib/formatters'
import UserAvatar from '../ui/UserAvatar'
import { LogoutIcon, SettingsIcon } from './SidebarIcons'

function SunIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z" />
    </svg>
  )
}

function UserMenu({ user, onClose }) {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { resolvedTheme, setThemePreference } = useTheme()
  const { activeWorkspace } = useWorkspace()
  const roleLabel = formatWorkspaceRole(
    getWorkspaceRoleValue(user, activeWorkspace),
  )
  // Cosmetic title set by the workspace owner (feature phase 1). Falls back to
  // the access-role label until a title exists.
  const customTitle = activeWorkspace?.current_user_title?.trim() || ''
  const contextLabel = customTitle || roleLabel
  const isDark = resolvedTheme === 'dark'

  function handleSettings() {
    onClose?.()
    navigate('/settings')
  }

  function handleLogout() {
    onClose?.()
    logout()
  }

  function toggleTheme() {
    setThemePreference(isDark ? 'light' : 'dark')
  }

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

      {activeWorkspace ? (
        <div className="user-menu__context">
          <span className="user-menu__context-role">{contextLabel}</span>
          <span aria-hidden="true">·</span>
          <span className="user-menu__context-ws">{activeWorkspace.name}</span>
        </div>
      ) : null}

      <div className="user-menu__divider" role="separator" />

      <button
        className="user-menu__item"
        onClick={handleSettings}
        role="menuitem"
        type="button"
      >
        <SettingsIcon />
        <span>Configurações</span>
      </button>

      <div className="user-menu__row">
        <span>Tema</span>
        <button
          aria-checked={isDark}
          aria-label={`Tema ${isDark ? 'escuro' : 'claro'}. Toque para alternar.`}
          className={`theme-switch ${isDark ? 'is-dark' : ''}`}
          onClick={toggleTheme}
          role="switch"
          type="button"
        >
          <span className="theme-switch__off">
            {isDark ? <SunIcon /> : <MoonIcon />}
          </span>
          <span className="theme-switch__knob">
            {isDark ? <MoonIcon /> : <SunIcon />}
          </span>
        </button>
      </div>

      <div className="user-menu__divider" role="separator" />

      <button
        className="user-menu__item user-menu__item--exit"
        onClick={handleLogout}
        role="menuitem"
        type="button"
      >
        <LogoutIcon />
        <span>Sair</span>
      </button>
    </div>
  )
}

export default UserMenu

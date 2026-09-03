import { NavLink } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getWorkspaceRole } from '../../lib/formatters'
import BrandIcon from '../ui/BrandIcon'
import UserAvatar from '../ui/UserAvatar'
import {
  ChevronIcon,
  DashboardIcon,
  LabelsIcon,
  ProductionIcon,
  SettingsIcon,
  StockIcon,
} from './SidebarIcons'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { to: '/stock', label: 'Estoque', icon: StockIcon },
  { to: '/production', label: 'Reposição', icon: ProductionIcon },
  { to: '/labels', label: 'Etiquetas', icon: LabelsIcon },
  { to: '/settings', label: 'Configurações', icon: SettingsIcon },
]

function Sidebar({ isCollapsed, onNavigate, onToggleCollapsed }) {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const role = getWorkspaceRole(user, activeWorkspace)

  return (
    <aside
      aria-label="Menu lateral"
      className={`sidebar ${isCollapsed ? 'is-collapsed' : ''}`}
    >
      <div className="brand">
        <BrandIcon />
        <div className="brand__text">
          <strong>Produzzy</strong>
          <span>Estoque e reposição</span>
        </div>
      </div>

      <button
        className="sidebar__collapse"
        type="button"
        onClick={onToggleCollapsed}
        title={isCollapsed ? 'Expandir menu' : 'Recolher menu'}
        aria-label={isCollapsed ? 'Expandir menu' : 'Recolher menu'}
        aria-expanded={!isCollapsed}
      >
        <ChevronIcon direction={isCollapsed ? 'right' : 'left'} />
      </button>

      <nav className="sidebar__nav" aria-label="Navegação principal">
        {navItems.map((item) => {
          const Icon = item.icon

          return (
            <NavLink
              className={({ isActive }) =>
                `sidebar__item ${isActive ? 'is-active' : ''}`
              }
              key={item.to}
              to={item.to}
              aria-label={item.label}
              onClick={onNavigate}
              title={item.label}
            >
              <span>
                <Icon />
              </span>
              <strong>{item.label}</strong>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar__user">
        <UserAvatar name={user?.name} src={user?.avatar_url} />
        <div className="sidebar__user-text">
          <strong>{user?.name ?? 'Usuário'}</strong>
          <span>{role}</span>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar

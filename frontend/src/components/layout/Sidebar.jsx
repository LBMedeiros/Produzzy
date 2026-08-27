import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getInitials, getWorkspaceRole } from '../../lib/formatters'
import BrandIcon from '../ui/BrandIcon'
import {
  ChevronIcon,
  DashboardIcon,
  LabelsIcon,
  ProductionIcon,
  SettingsIcon,
  StockIcon,
} from './SidebarIcons'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon },
  { id: 'stock', label: 'Estoque', icon: StockIcon },
  { id: 'production', label: 'Reposição', icon: ProductionIcon },
  { id: 'labels', label: 'Etiquetas', icon: LabelsIcon },
  { id: 'settings', label: 'Configurações', icon: SettingsIcon },
]

function Sidebar({ activePage, isCollapsed, onNavigate, onToggleCollapsed }) {
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
            <button
              className={`sidebar__item ${activePage === item.id ? 'is-active' : ''}`}
              key={item.id}
              type="button"
              aria-label={item.label}
              aria-current={activePage === item.id ? 'page' : undefined}
              onClick={() => onNavigate(item.id)}
              title={item.label}
            >
              <span>
                <Icon />
              </span>
              <strong>{item.label}</strong>
            </button>
          )
        })}
      </nav>

      <div className="sidebar__user">
        <div className="avatar">{getInitials(user?.name)}</div>
        <div className="sidebar__user-text">
          <strong>{user?.name ?? 'Usuário'}</strong>
          <span>{role}</span>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar

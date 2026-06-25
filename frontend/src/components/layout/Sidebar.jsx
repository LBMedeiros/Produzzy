import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getInitials, getWorkspaceRole } from '../../lib/formatters'
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
  { id: 'production', label: 'Produção', icon: ProductionIcon },
  { id: 'labels', label: 'Etiquetas', icon: LabelsIcon },
  { id: 'settings', label: 'Configurações', icon: SettingsIcon },
]

function Sidebar({ activePage, isCollapsed, onNavigate, onToggleCollapsed }) {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const role = getWorkspaceRole(user, activeWorkspace)

  return (
    <aside className={`sidebar ${isCollapsed ? 'is-collapsed' : ''}`}>
      <div className="brand">
        <div className="brand__mark">PZ</div>
        <div className="brand__text">
          <strong>Produzzy</strong>
          <span>Estoque e produção</span>
        </div>
      </div>

      <button
        className="sidebar__collapse"
        type="button"
        onClick={onToggleCollapsed}
        title={isCollapsed ? 'Expandir menu' : 'Recolher menu'}
        aria-label={isCollapsed ? 'Expandir menu' : 'Recolher menu'}
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

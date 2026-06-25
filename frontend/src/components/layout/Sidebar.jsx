import { workspace } from '../../data/mockData'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: 'D' },
  { id: 'stock', label: 'Estoque', icon: 'E' },
  { id: 'production', label: 'Produção', icon: 'P' },
  { id: 'labels', label: 'Etiquetas', icon: 'QR' },
  { id: 'settings', label: 'Configurações', icon: 'C' },
]

function Sidebar({ activePage, isCollapsed, onNavigate, onToggleCollapsed }) {
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
        {isCollapsed ? '>' : '<'}
      </button>

      <nav className="sidebar__nav" aria-label="Navegação principal">
        {navItems.map((item) => (
          <button
            className={`sidebar__item ${activePage === item.id ? 'is-active' : ''}`}
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            title={item.label}
          >
            <span>{item.icon}</span>
            <strong>{item.label}</strong>
          </button>
        ))}
      </nav>

      <div className="sidebar__user">
        <div className="avatar">{workspace.user.initials}</div>
        <div className="sidebar__user-text">
          <strong>{workspace.user.name}</strong>
          <span>{workspace.user.role}</span>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar

import { NavLink } from 'react-router-dom'
import {
  AccountIcon,
  DashboardIcon,
  LabelsIcon,
  ProductionIcon,
  StockIcon,
} from './SidebarIcons'

const tabs = [
  { to: '/dashboard', label: 'Início', icon: DashboardIcon },
  { to: '/stock', label: 'Estoque', icon: StockIcon },
  { to: '/production', label: 'Reposição', icon: ProductionIcon },
  { to: '/labels', label: 'Etiquetas', icon: LabelsIcon },
  { to: '/settings', label: 'Conta', icon: AccountIcon },
]

// Phone navigation (< 640px, docs/redesign §4.2): fixed to the bottom of the
// screen with the iPhone safe area; hidden on larger screens via CSS.
function BottomTabBar() {
  return (
    <nav aria-label="Menu principal" className="bottom-tabs">
      {tabs.map((tab) => {
        const Icon = tab.icon

        return (
          <NavLink
            className={({ isActive }) => `bottom-tabs__item${isActive ? ' is-active' : ''}`}
            key={tab.to}
            to={tab.to}
          >
            <Icon />
            <span>{tab.label}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}

export default BottomTabBar

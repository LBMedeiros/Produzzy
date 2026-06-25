import { useState } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'

function AppLayout({ children, activePage, onNavigate }) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  return (
    <div className={`app-shell ${isSidebarCollapsed ? 'is-sidebar-collapsed' : ''}`}>
      <Sidebar
        activePage={activePage}
        isCollapsed={isSidebarCollapsed}
        onNavigate={onNavigate}
        onToggleCollapsed={() => setIsSidebarCollapsed((value) => !value)}
      />
      <div className="app-shell__main">
        <Header />
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}

export default AppLayout

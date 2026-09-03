import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

function AppLayout() {
  const [isSidebarDrawerOpen, setIsSidebarDrawerOpen] = useState(false)
  const isSidebarCollapsed = !isSidebarDrawerOpen
  const location = useLocation()

  useEffect(() => {
    if (!isSidebarDrawerOpen) {
      return undefined
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsSidebarDrawerOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isSidebarDrawerOpen])

  const shellClasses = [
    'app-shell',
    isSidebarCollapsed ? 'is-sidebar-collapsed' : '',
    isSidebarDrawerOpen ? 'is-sidebar-overlay-open' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={shellClasses}>
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onNavigate={() => setIsSidebarDrawerOpen(false)}
        onToggleCollapsed={() => setIsSidebarDrawerOpen((value) => !value)}
      />
      <button
        aria-hidden={!isSidebarDrawerOpen}
        aria-label="Fechar menu lateral"
        className="sidebar-backdrop"
        tabIndex={isSidebarDrawerOpen ? 0 : -1}
        type="button"
        onClick={() => setIsSidebarDrawerOpen(false)}
      />
      <div className="app-shell__main">
        <Header onNavigated={() => setIsSidebarDrawerOpen(false)} />
        <main className="page-content">
          <div className="page-transition" key={location.pathname}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default AppLayout

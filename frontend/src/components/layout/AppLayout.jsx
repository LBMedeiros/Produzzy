import { useEffect, useState } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'

function AppLayout({ children, activePage, onNavigate }) {
  const [isSidebarDrawerOpen, setIsSidebarDrawerOpen] = useState(false)
  const isSidebarCollapsed = !isSidebarDrawerOpen

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

  function handleNavigate(page, intent = null) {
    onNavigate(page, intent)
    setIsSidebarDrawerOpen(false)
  }

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
        activePage={activePage}
        isCollapsed={isSidebarCollapsed}
        onNavigate={handleNavigate}
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
        <Header onNavigate={handleNavigate} />
        <main className="page-content">
          <div className="page-transition" key={activePage}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default AppLayout

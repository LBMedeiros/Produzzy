import { useEffect, useState } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'

const INTERMEDIATE_SIDEBAR_QUERY = '(min-width: 861px) and (max-width: 1100px)'

function isIntermediateSidebarViewport() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia(INTERMEDIATE_SIDEBAR_QUERY).matches
  )
}

function AppLayout({ children, activePage, onNavigate }) {
  const [isIntermediateViewport, setIsIntermediateViewport] = useState(
    isIntermediateSidebarViewport,
  )
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(
    isIntermediateSidebarViewport,
  )

  useEffect(() => {
    const mediaQuery = window.matchMedia(INTERMEDIATE_SIDEBAR_QUERY)

    function handleViewportChange(event) {
      setIsIntermediateViewport(event.matches)
      setIsSidebarCollapsed(event.matches)
    }

    handleViewportChange(mediaQuery)
    mediaQuery.addEventListener('change', handleViewportChange)

    return () => {
      mediaQuery.removeEventListener('change', handleViewportChange)
    }
  }, [])

  const isSidebarDrawerOpen = isIntermediateViewport && !isSidebarCollapsed

  useEffect(() => {
    if (!isSidebarDrawerOpen) {
      return undefined
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsSidebarCollapsed(true)
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isSidebarDrawerOpen])

  function handleNavigate(page) {
    onNavigate(page)

    if (isIntermediateViewport) {
      setIsSidebarCollapsed(true)
    }
  }

  const shellClasses = [
    'app-shell',
    isSidebarCollapsed ? 'is-sidebar-collapsed' : '',
    isIntermediateViewport ? 'is-sidebar-responsive' : '',
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
        onToggleCollapsed={() => setIsSidebarCollapsed((value) => !value)}
      />
      <button
        aria-hidden={!isSidebarDrawerOpen}
        aria-label="Fechar menu lateral"
        className="sidebar-backdrop"
        tabIndex={isSidebarDrawerOpen ? 0 : -1}
        type="button"
        onClick={() => setIsSidebarCollapsed(true)}
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

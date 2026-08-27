import { useEffect, useState } from 'react'
import AppLayout from './components/layout/AppLayout'
import BrandIcon from './components/ui/BrandIcon'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { WorkspaceProvider, useWorkspace } from './contexts/WorkspaceContext'
import CreateWorkspacePage from './pages/CreateWorkspacePage'
import DashboardPage from './pages/DashboardPage'
import InviteAcceptancePage from './pages/InviteAcceptancePage'
import LabelsPage from './pages/LabelsPage'
import LoginPage from './pages/LoginPage'
import ProductionPage from './pages/ProductionPage'
import SettingsPage from './pages/SettingsPage'
import StockPage from './pages/StockPage'

const pageComponents = {
  dashboard: DashboardPage,
  labels: LabelsPage,
  production: ProductionPage,
  settings: SettingsPage,
  stock: StockPage,
}

function getInviteAcceptTargetFromPath(pathname = window.location.pathname) {
  const individualMatch = pathname.match(/^\/invites\/([^/]+)\/accept\/?$/)
  const linkMatch = pathname.match(/^\/join\/([^/]+)\/?$/)
  const match = individualMatch || linkMatch

  if (!match) {
    return null
  }

  try {
    return {
      token: decodeURIComponent(match[1]),
      type: individualMatch ? 'individual' : 'link',
    }
  } catch {
    return null
  }
}

function clearInviteAcceptPath() {
  if (getInviteAcceptTargetFromPath()) {
    window.history.replaceState(window.history.state, '', '/')
  }
}

function LoadingScreen({ message }) {
  return (
    <main className="loading-screen">
      <BrandIcon />
      <strong>{message}</strong>
    </main>
  )
}

function ProtectedApp() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { activeWorkspace, loading: workspaceLoading } = useWorkspace()
  const [activePage, setActivePage] = useState('dashboard')
  const [navigationIntent, setNavigationIntent] = useState(null)
  const [inviteAcceptTarget, setInviteAcceptTarget] = useState(() =>
    getInviteAcceptTargetFromPath(),
  )

  useEffect(() => {
    function handleLocationChange() {
      setInviteAcceptTarget(getInviteAcceptTargetFromPath())
    }

    window.addEventListener('popstate', handleLocationChange)

    return () => window.removeEventListener('popstate', handleLocationChange)
  }, [])

  function handleNavigate(page, intent = null) {
    setNavigationIntent(intent)
    setActivePage(page)
  }

  function handleInviteDone() {
    clearInviteAcceptPath()
    setInviteAcceptTarget(null)
  }

  if (authLoading) {
    return <LoadingScreen message="Carregando sessão..." />
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  if (inviteAcceptTarget?.token) {
    return (
      <InviteAcceptancePage
        token={inviteAcceptTarget.token}
        type={inviteAcceptTarget.type}
        onDone={handleInviteDone}
      />
    )
  }

  if (workspaceLoading && !activeWorkspace) {
    return <LoadingScreen message="Carregando workspaces..." />
  }

  if (!activeWorkspace) {
    return <CreateWorkspacePage />
  }

  const ActivePage = pageComponents[activePage] ?? DashboardPage

  return (
    <AppLayout activePage={activePage} onNavigate={handleNavigate}>
      <ActivePage
        navigationIntent={navigationIntent}
        onNavigate={handleNavigate}
        onNavigationIntentHandled={() => setNavigationIntent(null)}
      />
    </AppLayout>
  )
}

function WorkspaceScope() {
  const { isAuthenticated, user } = useAuth()
  const workspaceKey = isAuthenticated ? `user-${user?.id ?? 'active'}` : 'guest'

  return (
    <WorkspaceProvider key={workspaceKey}>
      <ProtectedApp />
    </WorkspaceProvider>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <WorkspaceScope />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App

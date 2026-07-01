import { useState } from 'react'
import AppLayout from './components/layout/AppLayout'
import BrandIcon from './components/ui/BrandIcon'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { WorkspaceProvider, useWorkspace } from './contexts/WorkspaceContext'
import CreateWorkspacePage from './pages/CreateWorkspacePage'
import DashboardPage from './pages/DashboardPage'
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

  function handleNavigate(page, intent = null) {
    setNavigationIntent(intent)
    setActivePage(page)
  }

  if (authLoading) {
    return <LoadingScreen message="Carregando sessão..." />
  }

  if (!isAuthenticated) {
    return <LoginPage />
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
    <AuthProvider>
      <WorkspaceScope />
    </AuthProvider>
  )
}

export default App

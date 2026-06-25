import { useState } from 'react'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import StockPage from './pages/StockPage'
import ProductionPage from './pages/ProductionPage'
import LabelsPage from './pages/LabelsPage'
import SettingsPage from './pages/SettingsPage'

const pageComponents = {
  dashboard: DashboardPage,
  stock: StockPage,
  production: ProductionPage,
  labels: LabelsPage,
  settings: SettingsPage,
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [activePage, setActivePage] = useState('dashboard')

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />
  }

  const ActivePage = pageComponents[activePage] ?? DashboardPage

  return (
    <AppLayout activePage={activePage} onNavigate={setActivePage}>
      <ActivePage />
    </AppLayout>
  )
}

export default App

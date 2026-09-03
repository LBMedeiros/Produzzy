import { createElement, lazy, Suspense, useCallback } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import BrandIcon from './components/ui/BrandIcon'
import ErrorBoundary from './components/ErrorBoundary'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { WorkspaceProvider, useWorkspace } from './contexts/WorkspaceContext'

// Each screen is its own bundle chunk, fetched only when first shown.
const CreateWorkspacePage = lazy(() => import('./pages/CreateWorkspacePage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const InviteAcceptancePage = lazy(() => import('./pages/InviteAcceptancePage'))
const LabelsPage = lazy(() => import('./pages/LabelsPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const ProductionPage = lazy(() => import('./pages/ProductionPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const StockPage = lazy(() => import('./pages/StockPage'))

function LoadingScreen({ message }) {
  return (
    <main className="loading-screen">
      <BrandIcon />
      <strong>{message}</strong>
    </main>
  )
}

/**
 * Bridges a page to the (navigationIntent, onNavigate, onNavigationIntentHandled)
 * prop contract it had before routing existed, so the page components did not
 * need to change. Cross-page "intents" (e.g. open a product from search) ride
 * along in `location.state` and are cleared once consumed.
 */
function PageRoute({ component }) {
  const navigate = useNavigate()
  const location = useLocation()
  const intent = location.state?.intent ?? null

  const onNavigate = useCallback(
    (page, nextIntent = null) => {
      navigate(`/${page}`, {
        state: nextIntent ? { intent: nextIntent } : undefined,
      })
    },
    [navigate],
  )

  const onNavigationIntentHandled = useCallback(() => {
    navigate(location.pathname + location.search, {
      replace: true,
      state: null,
    })
  }, [navigate, location.pathname, location.search])

  return createElement(component, {
    navigationIntent: intent,
    onNavigate,
    onNavigationIntentHandled,
  })
}

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <LoadingScreen message="Carregando sessão..." />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}

function RequireWorkspace({ children }) {
  const { activeWorkspace, loading } = useWorkspace()

  if (loading && !activeWorkspace) {
    return <LoadingScreen message="Carregando workspaces..." />
  }

  if (!activeWorkspace) {
    return <Navigate to="/comecar" replace />
  }

  return children
}

function GuestOnly({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <LoadingScreen message="Carregando sessão..." />
  }

  if (isAuthenticated) {
    return <Navigate to={location.state?.from?.pathname ?? '/dashboard'} replace />
  }

  return children
}

function StartWorkspaceRoute() {
  const { activeWorkspace } = useWorkspace()

  if (activeWorkspace) {
    return <Navigate to="/dashboard" replace />
  }

  return <CreateWorkspacePage />
}

function InviteRoute({ type }) {
  const { token } = useParams()
  const navigate = useNavigate()

  return (
    <InviteAcceptancePage
      token={token}
      type={type}
      onDone={() => navigate('/dashboard', { replace: true })}
    />
  )
}

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingScreen message="Carregando..." />}>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnly>
              <LoginPage />
            </GuestOnly>
          }
        />
        <Route
          path="/invites/:token/accept"
          element={
            <RequireAuth>
              <InviteRoute type="individual" />
            </RequireAuth>
          }
        />
        <Route
          path="/join/:token"
          element={
            <RequireAuth>
              <InviteRoute type="link" />
            </RequireAuth>
          }
        />
        <Route
          path="/comecar"
          element={
            <RequireAuth>
              <StartWorkspaceRoute />
            </RequireAuth>
          }
        />
        <Route
          element={
            <RequireAuth>
              <RequireWorkspace>
                <AppLayout />
              </RequireWorkspace>
            </RequireAuth>
          }
        >
          <Route path="/dashboard" element={<PageRoute component={DashboardPage} />} />
          <Route path="/stock" element={<PageRoute component={StockPage} />} />
          <Route
            path="/production"
            element={<PageRoute component={ProductionPage} />}
          />
          <Route path="/labels" element={<PageRoute component={LabelsPage} />} />
          <Route path="/settings" element={<PageRoute component={SettingsPage} />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  )
}

function WorkspaceScope() {
  const { isAuthenticated, user } = useAuth()
  const workspaceKey = isAuthenticated ? `user-${user?.id ?? 'active'}` : 'guest'

  return (
    <WorkspaceProvider key={workspaceKey}>
      <ErrorBoundary>
        <AppRoutes />
      </ErrorBoundary>
    </WorkspaceProvider>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <WorkspaceScope />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App

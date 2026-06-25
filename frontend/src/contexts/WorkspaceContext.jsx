/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useAuth } from './AuthContext'
import {
  createWorkspace as createWorkspaceRequest,
  getWorkspace as getWorkspaceRequest,
  listWorkspaces,
} from '../services/workspaceService'

const WorkspaceContext = createContext(null)
const ACTIVE_WORKSPACE_KEY = 'produzzy_active_workspace_id'

function normalizeError(error) {
  return error?.message ?? 'Não foi possível carregar os workspaces.'
}

function getSavedWorkspaceId() {
  return localStorage.getItem(ACTIVE_WORKSPACE_KEY)
}

function persistActiveWorkspace(workspace) {
  if (!workspace) {
    localStorage.removeItem(ACTIVE_WORKSPACE_KEY)
    return
  }

  localStorage.setItem(ACTIVE_WORKSPACE_KEY, String(workspace.id))
}

function pickWorkspace(workspaces) {
  if (!workspaces.length) {
    return null
  }

  const savedWorkspaceId = getSavedWorkspaceId()
  const savedWorkspace = workspaces.find(
    (workspace) => String(workspace.id) === savedWorkspaceId,
  )

  return savedWorkspace ?? workspaces[0]
}

export function WorkspaceProvider({ children }) {
  const { isAuthenticated, user } = useAuth()
  const [workspaces, setWorkspaces] = useState([])
  const [activeWorkspace, setActiveWorkspace] = useState(null)
  const [loading, setLoading] = useState(() => isAuthenticated)
  const [error, setError] = useState('')

  const selectWorkspace = useCallback((workspace) => {
    setActiveWorkspace(workspace)
    persistActiveWorkspace(workspace)
  }, [])

  const loadWorkspaces = useCallback(async () => {
    if (!isAuthenticated) {
      return []
    }

    setLoading(true)
    setError('')

    try {
      const items = await listWorkspaces()
      const nextWorkspaces = Array.isArray(items) ? items : []
      const nextActiveWorkspace = pickWorkspace(nextWorkspaces)

      setWorkspaces(nextWorkspaces)
      setActiveWorkspace(nextActiveWorkspace)
      persistActiveWorkspace(nextActiveWorkspace)

      return nextWorkspaces
    } catch (loadError) {
      setError(normalizeError(loadError))
      throw loadError
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  const createWorkspace = useCallback(async (name) => {
    const workspaceName = name.trim()

    if (!workspaceName) {
      throw new Error('Informe um nome para o workspace.')
    }

    setLoading(true)
    setError('')

    try {
      const createdWorkspace = await createWorkspaceRequest({ name: workspaceName })

      setWorkspaces((currentWorkspaces) => [
        createdWorkspace,
        ...currentWorkspaces.filter((workspace) => workspace.id !== createdWorkspace.id),
      ])
      setActiveWorkspace(createdWorkspace)
      persistActiveWorkspace(createdWorkspace)

      return createdWorkspace
    } catch (createError) {
      setError(normalizeError(createError))
      throw createError
    } finally {
      setLoading(false)
    }
  }, [])

  const getWorkspace = useCallback((id) => getWorkspaceRequest(id), [])

  useEffect(() => {
    if (!isAuthenticated) {
      return undefined
    }

    const timeoutId = window.setTimeout(() => {
      loadWorkspaces().catch(() => undefined)
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [isAuthenticated, loadWorkspaces, user?.id])

  const value = useMemo(
    () => ({
      activeWorkspace,
      createWorkspace,
      error,
      getWorkspace,
      loadWorkspaces,
      loading,
      selectWorkspace,
      workspaces,
    }),
    [
      activeWorkspace,
      createWorkspace,
      error,
      getWorkspace,
      loadWorkspaces,
      loading,
      selectWorkspace,
      workspaces,
    ],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext)

  if (!context) {
    throw new Error('useWorkspace deve ser usado dentro de WorkspaceProvider.')
  }

  return context
}

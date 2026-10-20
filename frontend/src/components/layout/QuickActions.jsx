/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getWorkspaceRoleValue } from '../../lib/formatters'
import ProductPickerModal from './ProductPickerModal'

// Roles allowed to move stock and to create replenishments (AGENTS.md).
const ACTION_ROLES = new Set(['owner', 'admin', 'employee'])

// Which quick action the "+" button runs on each page (docs/redesign §4.2).
const FAB_ACTIONS = {
  '/dashboard': { label: 'Movimentar estoque', mode: 'movement' },
  '/stock': { label: 'Movimentar estoque', mode: 'movement' },
  '/production': { label: 'Nova reposição', mode: 'replenishment' },
}

const QuickActionsContext = createContext(null)

// "Movimentar estoque" / "Nova reposição" from anywhere: pick the product,
// then hand off to the page that owns the form through a navigation intent,
// so the existing (tested) forms and rules are reused as-is.
export function QuickActionsProvider({ children }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const [pickerMode, setPickerMode] = useState(null)
  const canAct = ACTION_ROLES.has(getWorkspaceRoleValue(user, activeWorkspace))

  const closePicker = useCallback(() => setPickerMode(null), [])

  const handlePick = useCallback(
    (product) => {
      const mode = pickerMode
      setPickerMode(null)

      if (mode === 'replenishment') {
        navigate('/production', {
          state: {
            intent: {
              productId: product.id,
              type: 'replenishment-create',
              workspaceId: activeWorkspace?.id,
            },
          },
        })
        return
      }

      navigate('/stock', {
        state: {
          intent: {
            productId: product.id,
            type: 'product-movement',
            workspaceId: activeWorkspace?.id,
          },
        },
      })
    },
    [activeWorkspace?.id, navigate, pickerMode],
  )

  const value = useMemo(
    () => ({ canAct, openQuickAction: setPickerMode }),
    [canAct],
  )

  return (
    <QuickActionsContext.Provider value={value}>
      {children}
      {pickerMode ? (
        <ProductPickerModal mode={pickerMode} onClose={closePicker} onPick={handlePick} />
      ) : null}
    </QuickActionsContext.Provider>
  )
}

export function useQuickActions() {
  return useContext(QuickActionsContext)
}

// Floating "+" above the bottom tab bar (phones only, via CSS). Hidden on
// Etiquetas and Conta, and for roles that can't act.
export function QuickActionButton() {
  const { pathname } = useLocation()
  const quickActions = useQuickActions()
  const action = FAB_ACTIONS[pathname]

  if (!action || !quickActions?.canAct) {
    return null
  }

  return (
    <button
      aria-label={action.label}
      className="fab"
      title={action.label}
      type="button"
      onClick={() => quickActions.openQuickAction(action.mode)}
    >
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M12 5v14M5 12h14" />
      </svg>
    </button>
  )
}

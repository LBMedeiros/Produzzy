import { useState } from 'react'
import Button from '../ui/Button'
import MemberAvatars from './MemberAvatars'
import MembersPopover from './MembersPopover'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { members } from '../../data/mockData'
import { getFirstName, getInitials } from '../../lib/formatters'

function Header() {
  const [isMembersOpen, setIsMembersOpen] = useState(false)
  const { user } = useAuth()
  const { activeWorkspace, selectWorkspace, workspaces } = useWorkspace()

  function handleWorkspaceChange(event) {
    const selectedWorkspace = workspaces.find(
      (workspace) => String(workspace.id) === event.target.value,
    )

    if (selectedWorkspace) {
      selectWorkspace(selectedWorkspace)
    }
  }

  return (
    <header className="topbar">
      <div className="workspace-switcher">
        <select
          aria-label="Workspace atual"
          onChange={handleWorkspaceChange}
          value={activeWorkspace?.id ?? ''}
        >
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </select>
        <span>v</span>
      </div>

      <label className="search-field">
        <input type="search" placeholder="Buscar produtos, categorias ou membros" />
      </label>

      <div className="topbar__actions">
        <Button icon="+">Novo produto</Button>

        <div className="topbar__user" title={user?.email}>
          <div className="avatar avatar--light">{getInitials(user?.name)}</div>
          <strong>{getFirstName(user?.name)}</strong>
        </div>

        <div className="topbar__members">
          <MemberAvatars
            members={members}
            isOpen={isMembersOpen}
            onToggle={() => setIsMembersOpen((value) => !value)}
          />
          {isMembersOpen ? <MembersPopover members={members} /> : null}
        </div>
      </div>
    </header>
  )
}

export default Header

import { useState } from 'react'
import Button from '../ui/Button'
import CreateWorkspaceModal from './CreateWorkspaceModal'
import MemberAvatars from './MemberAvatars'
import MembersPopover from './MembersPopover'
import ShareWorkspaceModal from './ShareWorkspaceModal'
import UserMenu from './UserMenu'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { members } from '../../data/mockData'
import { getFirstName, getInitials } from '../../lib/formatters'

function Header() {
  const [isCreateWorkspaceOpen, setIsCreateWorkspaceOpen] = useState(false)
  const [isMembersOpen, setIsMembersOpen] = useState(false)
  const [isShareOpen, setIsShareOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
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
    <>
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
          <span className="select-chevron" aria-hidden="true"></span>
        </div>

        <label className="search-field">
          <input type="search" placeholder="Buscar produtos, categorias ou membros" />
        </label>

        <div className="topbar__actions">
          <Button
            className="topbar__create"
            icon="+"
            onClick={() => setIsCreateWorkspaceOpen(true)}
          >
            Criar workspace
          </Button>
          <Button
            className="topbar__share"
            onClick={() => setIsShareOpen(true)}
            variant="secondary"
          >
            Compartilhar
          </Button>

          <div className="topbar__members">
            <MemberAvatars
              members={members}
              isOpen={isMembersOpen}
              onToggle={() => {
                setIsMembersOpen((value) => !value)
                setIsUserMenuOpen(false)
              }}
            />
            {isMembersOpen ? <MembersPopover members={members} /> : null}
          </div>

          <div className="topbar__user-wrap">
            <button
              className={`topbar__user ${isUserMenuOpen ? 'is-open' : ''}`}
              type="button"
              onClick={() => {
                setIsUserMenuOpen((value) => !value)
                setIsMembersOpen(false)
              }}
              aria-expanded={isUserMenuOpen}
              title={user?.email}
            >
              <div className="avatar avatar--light">{getInitials(user?.name)}</div>
              <strong>{getFirstName(user?.name)}</strong>
              <span className="select-chevron" aria-hidden="true"></span>
            </button>
            {isUserMenuOpen ? <UserMenu user={user} /> : null}
          </div>
        </div>
      </header>

      {isCreateWorkspaceOpen ? (
        <CreateWorkspaceModal onClose={() => setIsCreateWorkspaceOpen(false)} />
      ) : null}
      {isShareOpen ? <ShareWorkspaceModal onClose={() => setIsShareOpen(false)} /> : null}
    </>
  )
}

export default Header

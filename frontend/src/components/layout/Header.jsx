import { useState } from 'react'
import Button from '../ui/Button'
import MemberAvatars from './MemberAvatars'
import MembersPopover from './MembersPopover'
import { members, workspace } from '../../data/mockData'

function Header() {
  const [isMembersOpen, setIsMembersOpen] = useState(false)

  return (
    <header className="topbar">
      <div className="workspace-switcher" aria-label="Workspace atual">
        <strong>{workspace.name}</strong>
        <span>v</span>
      </div>

      <label className="search-field">
        <input type="search" placeholder="Buscar produtos, categorias ou membros" />
      </label>

      <div className="topbar__actions">
        <Button icon="+">Novo produto</Button>

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

import Button from '../ui/Button'
import { useWorkspace } from '../../contexts/WorkspaceContext'

function ShareWorkspaceModal({ onClose }) {
  const { activeWorkspace } = useWorkspace()

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workspace-modal" role="dialog" aria-modal="true">
        <div className="workspace-modal__header">
          <div>
            <span>Compartilhamento</span>
            <h2>{activeWorkspace?.name ?? 'Workspace'}</h2>
          </div>
          <button
            aria-label="Fechar modal"
            className="icon-button"
            type="button"
            onClick={onClose}
          >
            x
          </button>
        </div>
        <p className="workspace-modal__text">
          O compartilhamento deste workspace ainda não está disponível.
        </p>
        <div className="workspace-form__actions">
          <Button onClick={onClose}>Fechar</Button>
        </div>
      </section>
    </div>
  )
}

export default ShareWorkspaceModal

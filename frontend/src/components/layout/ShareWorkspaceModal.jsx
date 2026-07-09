import Button from '../ui/Button'
import { useWorkspace } from '../../contexts/WorkspaceContext'

function ShareWorkspaceModal({ onClose }) {
  const { activeWorkspace } = useWorkspace()

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workspace-modal" role="dialog" aria-modal="true">
        <div className="workspace-modal__header">
          <div>
            <span>Recurso futuro</span>
            <h2>Compartilhar workspace</h2>
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
          Em breve você poderá convidar membros para colaborar neste workspace.
        </p>
        <p className="workspace-modal__text">
          Convites por email e permissões de acesso serão adicionados em uma
          próxima etapa.
        </p>
        {activeWorkspace?.name ? (
          <p className="workspace-modal__text">
            Workspace atual: {activeWorkspace.name}
          </p>
        ) : null}
        <div className="workspace-form__actions">
          <Button onClick={onClose}>Entendi</Button>
        </div>
      </section>
    </div>
  )
}

export default ShareWorkspaceModal

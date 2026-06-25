import { useState } from 'react'
import Button from '../ui/Button'
import { useWorkspace } from '../../contexts/WorkspaceContext'

function CreateWorkspaceModal({ onClose }) {
  const { createWorkspace, loading } = useWorkspace()
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    try {
      await createWorkspace(name)
      onClose()
      setName('')
    } catch (submitError) {
      setError(submitError?.message ?? 'Não foi possível criar o workspace.')
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="workspace-modal" role="dialog" aria-modal="true">
        <div className="workspace-modal__header">
          <div>
            <span>Novo workspace</span>
            <h2>Criar workspace</h2>
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

        <form className="workspace-form" onSubmit={handleSubmit}>
          <label>
            Nome do workspace
            <input
              autoFocus
              maxLength="100"
              onChange={(event) => setName(event.target.value)}
              placeholder="TechLeads Enterprise"
              required
              value={name}
            />
          </label>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="workspace-form__actions">
            <Button disabled={loading} type="submit">
              {loading ? 'Criando...' : 'Criar'}
            </Button>
            <Button disabled={loading} onClick={onClose} variant="secondary">
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default CreateWorkspaceModal

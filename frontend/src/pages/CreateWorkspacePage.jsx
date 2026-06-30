import { useState } from 'react'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'

function CreateWorkspacePage() {
  const { logout, user } = useAuth()
  const { createWorkspace, error: workspaceError, loading } = useWorkspace()
  const [name, setName] = useState('')
  const [formError, setFormError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    try {
      await createWorkspace(name)
    } catch (error) {
      setFormError(error?.message ?? 'Não foi possível criar o workspace.')
    }
  }

  return (
    <main className="workspace-empty-page">
      <section className="workspace-empty-card">
        <div className="login-panel__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </div>

        <div className="workspace-empty-card__copy">
          <span>Olá, {user?.name ?? 'bem-vindo'}</span>
          <h1>Crie seu primeiro estoque</h1>
          <p>
            Organize produtos, produção e etiquetas em um workspace. Depois disso,
            você entra no dashboard e continua com as telas mockadas.
          </p>
        </div>

        <form className="workspace-form" onSubmit={handleSubmit}>
          <label>
            Nome do workspace
            <input
              autoFocus
              maxLength="100"
              onChange={(event) => setName(event.target.value)}
              placeholder="Bordados Medeiros"
              required
              value={name}
            />
          </label>

          {formError || workspaceError ? (
            <p className="form-error">{formError || workspaceError}</p>
          ) : null}

          <div className="workspace-form__actions">
            <Button disabled={loading} type="submit">
              {loading ? 'Criando...' : 'Criar workspace'}
            </Button>
            <Button disabled={loading} onClick={logout} variant="secondary">
              Sair
            </Button>
          </div>
        </form>
      </section>
    </main>
  )
}

export default CreateWorkspacePage

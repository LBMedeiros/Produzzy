import Card from '../components/ui/Card'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { getWorkspaceRole } from '../lib/formatters'

function SettingsPage() {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Configurações</h1>
          <p>Preferências do workspace, categorias e perfil</p>
        </div>
      </div>

      <section className="settings-grid">
        <Card title="Dados do workspace" eyebrow="Organização">
          <div className="settings-list">
            <label>
              Nome
              <input value={activeWorkspace?.name ?? ''} readOnly />
            </label>
          </div>
        </Card>

        <Card title="Preferências visuais" eyebrow="Interface">
          <div className="settings-list">
            <label>
              Tema
              <select defaultValue="light">
                <option value="light">Claro</option>
                <option value="system">Sistema</option>
              </select>
            </label>
            <label>
              Densidade
              <select defaultValue="comfortable">
                <option value="comfortable">Confortável</option>
                <option value="compact">Compacta</option>
              </select>
            </label>
          </div>
        </Card>

        <Card title="Categorias" eyebrow="Estoque">
          <p className="settings-muted">
            Cadastre e organize as categorias dos seus produtos na página Estoque.
          </p>
        </Card>

        <Card title="Perfil e conta" eyebrow="Usuário">
          <div className="settings-list">
            <label>
              Nome
              <input value={user?.name ?? ''} readOnly />
            </label>
            <label>
              Cargo
              <input value={getWorkspaceRole(user, activeWorkspace)} readOnly />
            </label>
            <label>
              Email
              <input value={user?.email ?? ''} readOnly />
            </label>
          </div>
        </Card>
      </section>
    </div>
  )
}

export default SettingsPage

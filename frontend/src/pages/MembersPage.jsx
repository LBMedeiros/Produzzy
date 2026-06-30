import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { roleDescriptions } from '../data/mockData'

function MembersPage() {
  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Equipe</h1>
          <p>Membros do workspace e permissões operacionais</p>
        </div>
        <Button icon="+">Convidar membro</Button>
      </div>

      <section className="content-grid content-grid--members">
        <Card title="Membros" eyebrow="Workspace">
          <div className="stock-empty">
            <h2>Equipe conectada à API</h2>
            <p>Consulte os membros pelo menu de equipe no topo da aplicação.</p>
          </div>
        </Card>
        <Card title="Cargos" eyebrow="Permissões">
          <div className="role-list">
            {roleDescriptions.map((role) => (
              <div className="role-list__item" key={role.role}>
                <strong>{role.role}</strong>
                <p>{role.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  )
}

export default MembersPage

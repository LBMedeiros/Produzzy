import Card from '../components/ui/Card'

const roleDescriptions = [
  {
    description: 'Controle total do workspace, membros, produtos e configurações.',
    role: 'Dono',
  },
  {
    description: 'Gerencia produtos, estoque, categorias e operação da equipe.',
    role: 'Admin',
  },
  {
    description: 'Consulta dados e registra movimentações de estoque permitidas.',
    role: 'Funcionário',
  },
  {
    description: 'Acompanha indicadores e dados sem alterar informações.',
    role: 'Visualizador',
  },
]

function MembersPage() {
  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Equipe</h1>
          <p>Membros do workspace e permissões operacionais</p>
        </div>
      </div>

      <section className="content-grid content-grid--members">
        <Card title="Membros" eyebrow="Workspace">
          <div className="stock-empty">
            <h2>Equipe do workspace</h2>
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

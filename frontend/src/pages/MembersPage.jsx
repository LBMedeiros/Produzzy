import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import { members, roleDescriptions } from '../data/mockData'

function MembersPage() {
  const columns = [
    { key: 'name', label: 'Nome' },
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Cargo' },
    {
      key: 'status',
      label: 'Status',
      render: (member) => (
        <Badge tone={member.status === 'Ativo' ? 'success' : 'warning'}>
          {member.status}
        </Badge>
      ),
    },
  ]

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
          <DataTable columns={columns} rows={members} />
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

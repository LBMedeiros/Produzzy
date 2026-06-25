import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import StatCard from '../components/ui/StatCard'
import {
  activities,
  attentionProducts,
  dashboardMetrics,
  productionColumns,
} from '../data/mockData'

function DashboardPage() {
  const attentionColumns = [
    { key: 'name', label: 'Produto' },
    { key: 'category', label: 'Categoria' },
    { key: 'quantity', label: 'Quantidade' },
    { key: 'minimumQuantity', label: 'Mínimo' },
    {
      key: 'status',
      label: 'Status',
      render: (product) => <Badge tone={product.statusTone}>{product.status}</Badge>,
    },
  ]

  const activityColumns = [
    { key: 'title', label: 'Atividade' },
    { key: 'detail', label: 'Detalhe' },
    { key: 'time', label: 'Quando' },
  ]
  const activeProduction = productionColumns.flatMap((column) =>
    column.tasks.map((task) => ({
      ...task,
      stage: column.title,
    })),
  )

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
          <p>Visão geral do estoque e produção</p>
        </div>
        <Button variant="secondary">Exportar resumo</Button>
      </div>

      <section className="stats-grid">
        {dashboardMetrics.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </section>

      <section className="content-grid content-grid--two">
        <Card title="Produtos que precisam de atenção" eyebrow="Estoque">
          <DataTable columns={attentionColumns} rows={attentionProducts} />
        </Card>
        <Card title="Atividades recentes" eyebrow="Operação">
          <DataTable columns={activityColumns} rows={activities} />
        </Card>
      </section>

      <section className="feature-grid">
        <Card className="feature-card" title="Produção em andamento" eyebrow="Kanban">
          <div className="mini-production-list">
            {activeProduction.slice(0, 3).map((task) => (
              <div className="mini-production-item" key={task.id}>
                <div>
                  <strong>{task.product}</strong>
                  <span>{task.stage}</span>
                </div>
                <Badge tone={task.statusTone}>{task.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
        <Card className="feature-card" title="Atalho para etiquetas/QR Code" eyebrow="Identificação">
          <p>
            Gere etiquetas individuais ou folhas A4 para identificar produtos na
            expedição, estoque e produção.
          </p>
          <div className="feature-card__visual">
            <div className="qr-grid"></div>
            <span>Etiqueta pronta para impressão</span>
          </div>
        </Card>
      </section>
    </div>
  )
}

export default DashboardPage

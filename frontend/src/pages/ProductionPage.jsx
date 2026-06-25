import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { productionColumns } from '../data/mockData'

function ProductionPage() {
  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Produção</h1>
          <p>Organize reposições e tarefas geradas pelo baixo estoque</p>
        </div>
        <Button icon="+">Nova tarefa</Button>
      </div>

      <div className="filters-row" aria-label="Filtros de produção">
        <button className="filter-pill is-active" type="button">
          Todas
        </button>
        <button className="filter-pill" type="button">
          Minhas tarefas
        </button>
        <button className="filter-pill" type="button">
          Baixo estoque
        </button>
        <button className="filter-pill" type="button">
          Finalizadas
        </button>
      </div>

      <section className="kanban-board" aria-label="Quadro de produção">
        {productionColumns.map((column) => (
          <article className="kanban-column" key={column.id}>
            <div className="kanban-column__header">
              <h2>{column.title}</h2>
              <span>{column.tasks.length}</span>
            </div>

            <div className="kanban-column__cards">
              {column.tasks.map((task) => (
                <div className="production-card" key={task.id}>
                  <div className="production-card__top">
                    <div>
                      <strong>{task.product}</strong>
                      <span>{task.category}</span>
                    </div>
                    <Badge tone={task.statusTone}>{task.status}</Badge>
                  </div>

                  <div className="production-card__numbers">
                    <span>Atual {task.quantity}</span>
                    <span>Mín. {task.minimumQuantity}</span>
                    <strong>Produzir {task.suggestedQuantity}</strong>
                  </div>

                  <div className="production-card__people">
                    <span>Responsável</span>
                    <strong>{task.assignee}</strong>
                    <span>Atribuído por {task.assignedBy}</span>
                  </div>

                  <div className="production-card__due">Prazo: {task.dueDate}</div>
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>
    </div>
  )
}

export default ProductionPage

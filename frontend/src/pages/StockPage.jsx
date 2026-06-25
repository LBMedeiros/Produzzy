import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import { categories, products } from '../data/mockData'

function StockPage() {
  const columns = [
    {
      key: 'name',
      label: 'Produto',
      render: (product) => (
        <div className="product-cell">
          <strong>{product.name}</strong>
          <span>ID {product.id}</span>
        </div>
      ),
    },
    { key: 'category', label: 'Categoria' },
    { key: 'quantity', label: 'Quantidade' },
    { key: 'minimumQuantity', label: 'Mínimo' },
    {
      key: 'status',
      label: 'Status',
      render: (product) => <Badge tone={product.statusTone}>{product.status}</Badge>,
    },
    { key: 'updatedAt', label: 'Última atualização' },
    {
      key: 'actions',
      label: 'Ações',
      render: () => (
        <div className="table-actions">
          <button type="button">Ver</button>
          <button type="button">Movimentar</button>
          <button type="button">Editar</button>
          <button type="button">Etiqueta</button>
        </div>
      ),
    },
  ]

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Estoque</h1>
          <p>Gerencie produtos, categorias e quantidades</p>
        </div>
        <Button icon="+">Novo produto</Button>
      </div>

      <Card className="stock-panel">
        <div className="stock-toolbar">
          <label className="stock-search">
            <input type="search" placeholder="Buscar no estoque" />
          </label>
          <select defaultValue="Todas as categorias">
            {categories.map((category) => (
              <option key={category}>{category}</option>
            ))}
          </select>
        </div>

        <div className="filters-row" aria-label="Filtros de estoque">
          <button className="filter-pill is-active" type="button">
            Todos
          </button>
          <button className="filter-pill" type="button">
            Baixo estoque
          </button>
          <button className="filter-pill" type="button">
            Sem estoque
          </button>
          <button className="filter-pill" type="button">
            Lixeira
          </button>
        </div>

        <DataTable columns={columns} rows={products} />
      </Card>
    </div>
  )
}

export default StockPage

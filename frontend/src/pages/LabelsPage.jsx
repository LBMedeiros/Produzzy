import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import { products } from '../data/mockData'

function LabelsPage() {
  const columns = [
    { key: 'name', label: 'Produto' },
    { key: 'category', label: 'Categoria' },
    { key: 'id', label: 'ID' },
    {
      key: 'actions',
      label: 'Ações',
      render: () => (
        <div className="table-actions">
          <button type="button">QR Code</button>
          <button type="button">Etiqueta</button>
        </div>
      ),
    },
  ]

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Etiquetas e QR Codes</h1>
          <p>Gere identificação para produtos, caixas e folhas de impressão</p>
        </div>
        <Button icon="+">Folha A4</Button>
      </div>

      <section className="feature-grid feature-grid--four">
        <Card title="QR Code individual" eyebrow="Produto">
          <p>Acesse o detalhe do produto a partir da etiqueta física.</p>
        </Card>
        <Card title="Etiqueta individual" eyebrow="Impressão">
          <p>Gere uma etiqueta com nome, categoria, QR Code e ID.</p>
        </Card>
        <Card title="Folha A4" eyebrow="Lote">
          <p>Organize múltiplas etiquetas para impressão em lote.</p>
        </Card>
        <Card title="Pronto para impressão" eyebrow="Fila">
          <p>Acompanhe etiquetas preparadas para produtos e caixas.</p>
        </Card>
      </section>

      <section className="content-grid content-grid--label">
        <Card title="Prévia da etiqueta" eyebrow="Preview">
          <div className="printed-label">
            <small className="printed-label__brand">Produzzy</small>
            <div>
              <strong>Camiseta algodão premium</strong>
              <span>Vestuário</span>
            </div>
            <div className="qr-grid qr-grid--large"></div>
            <small>ID 1024</small>
          </div>
        </Card>
        <Card title="Produtos para etiqueta" eyebrow="Catálogo">
          <DataTable
            columns={columns}
            rows={products.filter((product) => product.status !== 'Inativo')}
          />
        </Card>
      </section>
    </div>
  )
}

export default LabelsPage

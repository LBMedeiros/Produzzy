import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import StatCard from '../components/ui/StatCard'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getReplenishmentPriority,
  getReplenishmentQuantity,
  getReplenishmentStatus,
  needsReplenishment,
} from '../lib/replenishment'
import { listLowStockProducts } from '../services/productService'

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para visualizar estes dados.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível carregar as necessidades de reposição.'
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value ?? 0)
}

function ProductionPage() {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [products, setProducts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadReplenishment = useCallback(async () => {
    if (!workspaceId) {
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const items = await listLowStockProducts(workspaceId)
      setProducts(items.filter(needsReplenishment))
    } catch (loadError) {
      setProducts([])
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadReplenishment()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReplenishment])

  const stats = useMemo(() => {
    const outOfStock = products.filter((product) => product.quantity === 0).length
    const requiredUnits = products.reduce(
      (total, product) => total + getReplenishmentQuantity(product),
      0,
    )

    return [
      {
        label: 'Produtos em baixo estoque',
        tone: 'yellow',
        trend: 'Itens abaixo do mínimo cadastrado',
        value: formatNumber(products.length),
      },
      {
        label: 'Produtos sem estoque',
        tone: 'slate',
        trend: 'Itens com prioridade alta',
        value: formatNumber(outOfStock),
      },
      {
        label: 'Unidades necessárias',
        tone: 'blue',
        trend: 'Para atingir os estoques mínimos',
        value: formatNumber(requiredUnits),
      },
    ]
  }, [products])

  const columns = [
    {
      key: 'name',
      label: 'Produto',
      render: (product) => (
        <div className="product-cell">
          <strong>{product.name}</strong>
        </div>
      ),
    },
    { key: 'category', label: 'Categoria' },
    {
      key: 'quantity',
      label: 'Estoque atual',
      render: (product) => formatNumber(product.quantity),
    },
    {
      key: 'minimum_quantity',
      label: 'Mínimo',
      render: (product) => formatNumber(product.minimum_quantity),
    },
    {
      key: 'required_quantity',
      label: 'Necessário repor',
      render: (product) => (
        <strong className="replenishment-quantity">
          {formatNumber(getReplenishmentQuantity(product))} un.
        </strong>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (product) => {
        const status = getReplenishmentStatus(product)

        return <Badge tone={status.tone}>{status.label}</Badge>
      },
    },
    {
      key: 'priority',
      label: 'Prioridade',
      render: (product) => {
        const priority = getReplenishmentPriority(product)

        return <Badge tone={priority.tone}>{priority.label}</Badge>
      },
    },
    {
      key: 'suggested_action',
      label: 'Ação sugerida',
      render: () => (
        <span className="replenishment-action">Comprar ou produzir</span>
      ),
    },
  ]

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Reposição</h1>
          <p>Veja produtos que precisam ser comprados, produzidos ou repostos.</p>
        </div>
        <Button onClick={loadReplenishment} variant="secondary">
          Atualizar dados
        </Button>
      </div>

      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

      {isLoading ? (
        <div className="stock-loading">Carregando necessidades de reposição...</div>
      ) : (
        <>
          <section className="stats-grid replenishment-stats">
            {stats.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </section>

          <Card
            className="replenishment-table"
            title="Produtos que precisam de atenção"
            eyebrow="Estoque"
          >
            {products.length ? (
              <DataTable columns={columns} rows={products} />
            ) : (
              <div className="stock-empty">
                <span className="replenishment-empty__symbol" aria-hidden="true">
                  ✓
                </span>
                <h2>Tudo certo por aqui</h2>
                <p>Nenhum produto precisa de reposição no momento.</p>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}

export default ProductionPage

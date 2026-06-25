import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  createCategory,
  listCategories,
} from '../services/categoryService'
import {
  createProduct,
  createStockMovement,
  deleteProduct,
  listLowStockProducts,
  listProducts,
  restoreProduct,
  updateProduct,
} from '../services/productService'

const STOCK_FILTERS = [
  { id: 'active', label: 'Ativos' },
  { id: 'low-stock', label: 'Baixo estoque' },
  { id: 'empty', label: 'Sem estoque' },
  { id: 'deleted', label: 'Lixeira' },
]

const emptyProductForm = {
  category: '',
  minimumQuantity: '0',
  name: '',
  quantity: '0',
}

const emptyMovementForm = {
  movementType: 'entrada',
  quantity: '1',
  reason: '',
}

const emptyCategoryForm = {
  description: '',
  name: '',
}

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para realizar esta ação.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

function getProductStatus(product) {
  if (!product.is_active) {
    return { label: 'Na lixeira', tone: 'neutral' }
  }

  if (product.quantity === 0) {
    return { label: 'Sem estoque', tone: 'danger' }
  }

  if (product.quantity <= product.minimum_quantity) {
    return { label: 'Baixo estoque', tone: 'warning' }
  }

  return { label: 'Em estoque', tone: 'success' }
}

function formatDate(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
  }).format(new Date(value))
}

function normalizeProductForm(product, categories) {
  const firstCategory = categories[0]?.name ?? ''

  if (!product) {
    return {
      ...emptyProductForm,
      category: firstCategory,
    }
  }

  return {
    category: product.category ?? firstCategory,
    minimumQuantity: String(product.minimum_quantity ?? 0),
    name: product.name ?? '',
    quantity: String(product.quantity ?? 0),
  }
}

function StockPage() {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id

  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [activeFilter, setActiveFilter] = useState('active')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [actionProductId, setActionProductId] = useState(null)

  const [productModal, setProductModal] = useState(null)
  const [productForm, setProductForm] = useState(emptyProductForm)
  const [productFormError, setProductFormError] = useState('')
  const [isSavingProduct, setIsSavingProduct] = useState(false)

  const [movementProduct, setMovementProduct] = useState(null)
  const [movementForm, setMovementForm] = useState(emptyMovementForm)
  const [movementError, setMovementError] = useState('')
  const [isMovingStock, setIsMovingStock] = useState(false)

  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false)
  const [categoryForm, setCategoryForm] = useState(emptyCategoryForm)
  const [categoryError, setCategoryError] = useState('')
  const [isSavingCategory, setIsSavingCategory] = useState(false)

  const loadStockData = useCallback(async () => {
    if (!workspaceId) {
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const productRequest =
        activeFilter === 'low-stock'
          ? listLowStockProducts(workspaceId)
          : listProducts(workspaceId, {
              status: activeFilter === 'deleted' ? 'deleted' : 'active',
            })

      const [categoryItems, productItems] = await Promise.all([
        listCategories(workspaceId),
        productRequest,
      ])
      const nextProducts =
        activeFilter === 'empty'
          ? productItems.filter((product) => product.quantity === 0)
          : productItems

      setCategories(categoryItems)
      setProducts(nextProducts)
    } catch (loadError) {
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoading(false)
    }
  }, [activeFilter, workspaceId])

  const refreshCategories = useCallback(async () => {
    if (!workspaceId) {
      return []
    }

    const categoryItems = await listCategories(workspaceId)
    setCategories(categoryItems)

    return categoryItems
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadStockData()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadStockData])

  const filteredProducts = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    return products.filter((product) => {
      const matchesSearch =
        !normalizedSearch ||
        product.name.toLowerCase().includes(normalizedSearch) ||
        product.category.toLowerCase().includes(normalizedSearch) ||
        String(product.id).includes(normalizedSearch)
      const matchesCategory =
        categoryFilter === 'all' || product.category === categoryFilter

      return matchesSearch && matchesCategory
    })
  }, [categoryFilter, products, searchTerm])

  function updateProductField(field, value) {
    setProductForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
  }

  function updateMovementField(field, value) {
    setMovementForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
  }

  function openCreateProduct() {
    setProductForm(normalizeProductForm(null, categories))
    setProductFormError('')
    setProductModal({ mode: 'create', product: null })
  }

  function openEditProduct(product) {
    setProductForm(normalizeProductForm(product, categories))
    setProductFormError('')
    setProductModal({ mode: 'edit', product })
  }

  function openMovementModal(product) {
    setMovementProduct(product)
    setMovementForm(emptyMovementForm)
    setMovementError('')
  }

  async function handleSaveProduct(event) {
    event.preventDefault()

    if (!workspaceId || !productModal) {
      return
    }

    if (!productForm.category) {
      setProductFormError('Crie ou selecione uma categoria antes de salvar.')
      return
    }

    setIsSavingProduct(true)
    setProductFormError('')
    setSuccessMessage('')

    try {
      const payload = {
        category: productForm.category,
        minimum_quantity: Number(productForm.minimumQuantity),
        name: productForm.name.trim(),
      }

      if (productModal.mode === 'create') {
        await createProduct(workspaceId, {
          ...payload,
          quantity: Number(productForm.quantity),
        })
        setSuccessMessage('Produto criado com sucesso.')
      } else {
        await updateProduct(workspaceId, productModal.product.id, payload)
        setSuccessMessage('Produto atualizado com sucesso.')
      }

      setProductModal(null)
      setProductForm(emptyProductForm)
      await loadStockData()
    } catch (saveError) {
      setProductFormError(getFriendlyError(saveError))
    } finally {
      setIsSavingProduct(false)
    }
  }

  async function handleCreateCategory(event) {
    event.preventDefault()

    if (!workspaceId) {
      return
    }

    setIsSavingCategory(true)
    setCategoryError('')
    setSuccessMessage('')

    try {
      const createdCategory = await createCategory(workspaceId, {
        description: categoryForm.description.trim() || null,
        name: categoryForm.name.trim(),
      })

      await refreshCategories()
      setProductForm((currentForm) => ({
        ...currentForm,
        category: createdCategory.name,
      }))
      setCategoryForm(emptyCategoryForm)
      setIsCategoryModalOpen(false)
      setSuccessMessage('Categoria criada com sucesso.')
    } catch (saveError) {
      setCategoryError(getFriendlyError(saveError))
    } finally {
      setIsSavingCategory(false)
    }
  }

  async function handleMoveStock(event) {
    event.preventDefault()

    if (!workspaceId || !movementProduct) {
      return
    }

    setIsMovingStock(true)
    setMovementError('')
    setSuccessMessage('')

    try {
      await createStockMovement(workspaceId, movementProduct.id, {
        movement_type: movementForm.movementType,
        quantity: Number(movementForm.quantity),
        reason: movementForm.reason.trim() || null,
      })

      setMovementProduct(null)
      setMovementForm(emptyMovementForm)
      setSuccessMessage('Movimentação registrada com sucesso.')
      await loadStockData()
    } catch (moveError) {
      setMovementError(getFriendlyError(moveError))
    } finally {
      setIsMovingStock(false)
    }
  }

  async function handleDeleteProduct(product) {
    if (!workspaceId) {
      return
    }

    const shouldDelete = window.confirm(
      `Enviar "${product.name}" para a lixeira?`,
    )

    if (!shouldDelete) {
      return
    }

    setActionProductId(product.id)
    setError('')
    setSuccessMessage('')

    try {
      await deleteProduct(workspaceId, product.id)
      setSuccessMessage('Produto enviado para a lixeira.')
      await loadStockData()
    } catch (deleteError) {
      setError(getFriendlyError(deleteError))
    } finally {
      setActionProductId(null)
    }
  }

  async function handleRestoreProduct(product) {
    if (!workspaceId) {
      return
    }

    setActionProductId(product.id)
    setError('')
    setSuccessMessage('')

    try {
      await restoreProduct(workspaceId, product.id)
      setSuccessMessage('Produto restaurado com sucesso.')
      await loadStockData()
    } catch (restoreError) {
      setError(getFriendlyError(restoreError))
    } finally {
      setActionProductId(null)
    }
  }

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
    {
      key: 'minimum_quantity',
      label: 'Mínimo',
      render: (product) => product.minimum_quantity,
    },
    {
      key: 'status',
      label: 'Status',
      render: (product) => {
        const status = getProductStatus(product)

        return <Badge tone={status.tone}>{status.label}</Badge>
      },
    },
    {
      key: 'updated_at',
      label: 'Última atualização',
      render: (product) => formatDate(product.updated_at),
    },
    {
      key: 'actions',
      label: 'Ações',
      render: (product) =>
        activeFilter === 'deleted' ? (
          <div className="table-actions">
            <button
              disabled={actionProductId === product.id}
              type="button"
              onClick={() => handleRestoreProduct(product)}
            >
              Restaurar
            </button>
          </div>
        ) : (
          <div className="table-actions">
            <button type="button" onClick={() => openMovementModal(product)}>
              Movimentar
            </button>
            <button type="button" onClick={() => openEditProduct(product)}>
              Editar
            </button>
            <button
              disabled={actionProductId === product.id}
              type="button"
              onClick={() => handleDeleteProduct(product)}
            >
              Remover
            </button>
          </div>
        ),
    },
  ]

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Estoque</h1>
          <p>Gerencie produtos, categorias e quantidades reais do workspace</p>
        </div>
        <div className="page-heading__actions">
          <Button onClick={() => setIsCategoryModalOpen(true)} variant="secondary">
            Nova categoria
          </Button>
          <Button icon="+" onClick={openCreateProduct}>
            Novo produto
          </Button>
        </div>
      </div>

      <Card className="stock-panel">
        <div className="stock-toolbar">
          <label className="stock-search">
            <input
              type="search"
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Buscar por nome, categoria ou ID"
              value={searchTerm}
            />
          </label>
          <select
            onChange={(event) => setCategoryFilter(event.target.value)}
            value={categoryFilter}
          >
            <option value="all">Todas as categorias</option>
            {categories.map((category) => (
              <option key={category.id} value={category.name}>
                {category.name}
              </option>
            ))}
          </select>
        </div>

        <div className="filters-row" aria-label="Filtros de estoque">
          {STOCK_FILTERS.map((filter) => (
            <button
              className={`filter-pill ${
                activeFilter === filter.id ? 'is-active' : ''
              }`}
              key={filter.id}
              type="button"
              onClick={() => setActiveFilter(filter.id)}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {successMessage ? (
          <p className="stock-feedback stock-feedback--success">{successMessage}</p>
        ) : null}
        {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

        {isLoading ? (
          <div className="stock-loading">Carregando estoque...</div>
        ) : filteredProducts.length ? (
          <DataTable columns={columns} rows={filteredProducts} />
        ) : (
          <div className="stock-empty">
            <h2>Nenhum produto encontrado</h2>
            <p>
              {activeFilter === 'deleted'
                ? 'A lixeira está vazia para este workspace.'
                : 'Crie um produto ou ajuste os filtros para visualizar o estoque.'}
            </p>
            {activeFilter !== 'deleted' ? (
              <Button onClick={openCreateProduct} variant="secondary">
                Criar produto
              </Button>
            ) : null}
          </div>
        )}
      </Card>

      {productModal ? (
        <div className="modal-backdrop" role="presentation">
          <section className="workspace-modal stock-modal" role="dialog" aria-modal="true">
            <div className="workspace-modal__header">
              <div>
                <span>Produto</span>
                <h2>
                  {productModal.mode === 'create' ? 'Novo produto' : 'Editar produto'}
                </h2>
              </div>
              <button
                aria-label="Fechar modal"
                className="icon-button"
                type="button"
                onClick={() => setProductModal(null)}
              >
                x
              </button>
            </div>

            <form className="stock-form" onSubmit={handleSaveProduct}>
              <label>
                Nome
                <input
                  maxLength="100"
                  onChange={(event) => updateProductField('name', event.target.value)}
                  placeholder="Camiseta algodão premium"
                  required
                  value={productForm.name}
                />
              </label>

              <label>
                Categoria
                <select
                  disabled={!categories.length}
                  onChange={(event) =>
                    updateProductField('category', event.target.value)
                  }
                  required
                  value={productForm.category}
                >
                  {categories.length ? null : (
                    <option value="">Crie uma categoria primeiro</option>
                  )}
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>

              {productModal.mode === 'create' ? (
                <label>
                  Quantidade inicial
                  <input
                    min="0"
                    onChange={(event) =>
                      updateProductField('quantity', event.target.value)
                    }
                    required
                    type="number"
                    value={productForm.quantity}
                  />
                </label>
              ) : null}

              <label>
                Quantidade mínima
                <input
                  min="0"
                  onChange={(event) =>
                    updateProductField('minimumQuantity', event.target.value)
                  }
                  required
                  type="number"
                  value={productForm.minimumQuantity}
                />
              </label>

              {categories.length ? null : (
                <p className="stock-form__hint">
                  O backend atual espera uma categoria em texto. Crie uma categoria
                  antes de salvar produtos.
                </p>
              )}
              {productFormError ? <p className="form-error">{productFormError}</p> : null}

              <div className="workspace-form__actions">
                <Button disabled={isSavingProduct || !categories.length} type="submit">
                  {isSavingProduct ? 'Salvando...' : 'Salvar'}
                </Button>
                <Button
                  disabled={isSavingProduct}
                  onClick={() => setIsCategoryModalOpen(true)}
                  variant="secondary"
                >
                  Nova categoria
                </Button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {movementProduct ? (
        <div className="modal-backdrop" role="presentation">
          <section className="workspace-modal stock-modal" role="dialog" aria-modal="true">
            <div className="workspace-modal__header">
              <div>
                <span>Movimentação</span>
                <h2>{movementProduct.name}</h2>
              </div>
              <button
                aria-label="Fechar modal"
                className="icon-button"
                type="button"
                onClick={() => setMovementProduct(null)}
              >
                x
              </button>
            </div>

            <form className="stock-form" onSubmit={handleMoveStock}>
              <label>
                Tipo
                <select
                  onChange={(event) =>
                    updateMovementField('movementType', event.target.value)
                  }
                  value={movementForm.movementType}
                >
                  <option value="entrada">Entrada</option>
                  <option value="saida">Saída</option>
                  <option value="ajuste">Ajuste</option>
                </select>
              </label>
              <label>
                Quantidade
                <input
                  min="1"
                  onChange={(event) => updateMovementField('quantity', event.target.value)}
                  required
                  type="number"
                  value={movementForm.quantity}
                />
              </label>
              <label>
                Motivo/observação
                <textarea
                  maxLength="255"
                  onChange={(event) => updateMovementField('reason', event.target.value)}
                  placeholder="Reposição, venda, conferência..."
                  value={movementForm.reason}
                />
              </label>

              {movementError ? <p className="form-error">{movementError}</p> : null}

              <div className="workspace-form__actions">
                <Button disabled={isMovingStock} type="submit">
                  {isMovingStock ? 'Movimentando...' : 'Registrar'}
                </Button>
                <Button
                  disabled={isMovingStock}
                  onClick={() => setMovementProduct(null)}
                  variant="secondary"
                >
                  Cancelar
                </Button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {isCategoryModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="workspace-modal stock-modal" role="dialog" aria-modal="true">
            <div className="workspace-modal__header">
              <div>
                <span>Categoria</span>
                <h2>Nova categoria</h2>
              </div>
              <button
                aria-label="Fechar modal"
                className="icon-button"
                type="button"
                onClick={() => setIsCategoryModalOpen(false)}
              >
                x
              </button>
            </div>

            <form className="stock-form" onSubmit={handleCreateCategory}>
              <label>
                Nome
                <input
                  maxLength="100"
                  onChange={(event) =>
                    setCategoryForm((currentForm) => ({
                      ...currentForm,
                      name: event.target.value,
                    }))
                  }
                  placeholder="Vestuário"
                  required
                  value={categoryForm.name}
                />
              </label>
              <label>
                Descrição
                <textarea
                  maxLength="255"
                  onChange={(event) =>
                    setCategoryForm((currentForm) => ({
                      ...currentForm,
                      description: event.target.value,
                    }))
                  }
                  placeholder="Descrição opcional"
                  value={categoryForm.description}
                />
              </label>

              {categoryError ? <p className="form-error">{categoryError}</p> : null}

              <div className="workspace-form__actions">
                <Button disabled={isSavingCategory} type="submit">
                  {isSavingCategory ? 'Criando...' : 'Criar categoria'}
                </Button>
                <Button
                  disabled={isSavingCategory}
                  onClick={() => setIsCategoryModalOpen(false)}
                  variant="secondary"
                >
                  Cancelar
                </Button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default StockPage

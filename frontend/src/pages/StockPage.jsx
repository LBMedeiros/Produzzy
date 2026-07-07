import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import ReplenishmentCreationModal from '../components/replenishment/ReplenishmentCreationModal'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  createCategory,
  deleteCategory,
  listCategories,
  restoreCategory,
  updateCategory,
} from '../services/categoryService'
import {
  createProduct,
  createStockMovement,
  deleteProduct,
  getProduct,
  listLowStockProducts,
  listProductStockMovements,
  listProducts,
  restoreProduct,
  updateProduct,
} from '../services/productService'
import { listWorkspaceStockMovements } from '../services/stockMovementService'
import {
  createReplenishment,
  listReplenishments,
} from '../services/replenishmentService'

const STOCK_FILTERS = [
  { id: 'active', label: 'Ativos' },
  { id: 'low-stock', label: 'Baixo estoque' },
  { id: 'empty', label: 'Sem estoque' },
  { id: 'history', label: 'Histórico' },
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

const MOVEMENT_LABELS = {
  ajuste: 'Ajuste',
  entrada: 'Entrada',
  saida: 'Saída',
}

const MOVEMENT_TONES = {
  ajuste: 'neutral',
  entrada: 'success',
  saida: 'danger',
}

const MOVEMENTS_PAGE_LIMIT = 20
const WORKSPACE_MOVEMENTS_PAGE_LIMIT = 20

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

function formatLinkedProducts(count) {
  if (count === 0) {
    return 'Nenhum produto vinculado'
  }

  return count === 1 ? '1 produto vinculado' : `${count} produtos vinculados`
}

function formatProductsToUpdate(count) {
  if (count === 0) {
    return 'Nenhum produto ativo será atualizado.'
  }

  return count === 1
    ? '1 produto ativo será atualizado.'
    : `${count} produtos ativos serão atualizados.`
}

function formatProductsRemovedWithCategory(count) {
  if (count === 0) {
    return 'Nenhum produto aguardando restauração'
  }

  return count === 1
    ? '1 produto removido junto com a categoria'
    : `${count} produtos removidos junto com a categoria`
}

function uniqueReplenishmentsByProduct(items) {
  const seenProductIds = new Set()

  return items.filter((item) => {
    if (seenProductIds.has(item.product_id)) {
      return false
    }

    seenProductIds.add(item.product_id)
    return true
  })
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

function StockPage({ navigationIntent, onNavigationIntentHandled }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id

  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [deletedCategories, setDeletedCategories] = useState([])
  const [activeFilter, setActiveFilter] = useState('active')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [actionProductId, setActionProductId] = useState(null)
  const [readyReplenishments, setReadyReplenishments] = useState([])
  const [replenishmentProduct, setReplenishmentProduct] = useState(null)
  const [replenishmentError, setReplenishmentError] = useState('')
  const [isSavingReplenishment, setIsSavingReplenishment] = useState(false)

  const [productModal, setProductModal] = useState(null)
  const [productForm, setProductForm] = useState(emptyProductForm)
  const [productFormError, setProductFormError] = useState('')
  const [isSavingProduct, setIsSavingProduct] = useState(false)

  const [movementProduct, setMovementProduct] = useState(null)
  const [movementForm, setMovementForm] = useState(emptyMovementForm)
  const [movementError, setMovementError] = useState('')
  const [isMovingStock, setIsMovingStock] = useState(false)

  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false)
  const [categoryAction, setCategoryAction] = useState('')
  const [isEditCategoriesOpen, setIsEditCategoriesOpen] = useState(false)
  const [categoryForm, setCategoryForm] = useState(emptyCategoryForm)
  const [categoryError, setCategoryError] = useState('')
  const [isSavingCategory, setIsSavingCategory] = useState(false)
  const [editingCategoryId, setEditingCategoryId] = useState(null)
  const [categoryEditForm, setCategoryEditForm] = useState(emptyCategoryForm)
  const [categoryEditError, setCategoryEditError] = useState('')
  const [isSavingCategoryEdit, setIsSavingCategoryEdit] = useState(false)
  const [categorySearchTerm, setCategorySearchTerm] = useState('')
  const [categoryProducts, setCategoryProducts] = useState([])
  const [deletedCategoryProducts, setDeletedCategoryProducts] = useState([])
  const [isLoadingCategoryProducts, setIsLoadingCategoryProducts] =
    useState(false)
  const [categoryManagerError, setCategoryManagerError] = useState('')
  const [categoryManagerSuccess, setCategoryManagerSuccess] = useState('')
  const [updateLinkedProducts, setUpdateLinkedProducts] = useState(false)
  const [deletingCategoryId, setDeletingCategoryId] = useState(null)
  const [restoringCategoryId, setRestoringCategoryId] = useState(null)
  const [categoryManagerView, setCategoryManagerView] = useState('active')

  const [workspaceMovements, setWorkspaceMovements] = useState([])
  const [historyPage, setHistoryPage] = useState(1)
  const [hasMoreHistory, setHasMoreHistory] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [isLoadingMoreHistory, setIsLoadingMoreHistory] = useState(false)
  const [historyError, setHistoryError] = useState('')

  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [detailProduct, setDetailProduct] = useState(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [stockMovements, setStockMovements] = useState([])
  const [isLoadingMovements, setIsLoadingMovements] = useState(false)
  const [isLoadingMoreMovements, setIsLoadingMoreMovements] = useState(false)
  const [movementsPage, setMovementsPage] = useState(1)
  const [hasMoreMovements, setHasMoreMovements] = useState(false)
  const [movementsError, setMovementsError] = useState('')

  const loadWorkspaceHistory = useCallback(
    async (options = {}) => {
      if (!workspaceId) {
        return []
      }

      const page = options.page ?? 1
      const shouldAppend = options.append ?? false

      if (shouldAppend) {
        setIsLoadingMoreHistory(true)
      } else {
        setIsLoadingHistory(true)
      }
      setHistoryError('')

      try {
        const items = await listWorkspaceStockMovements(workspaceId, {
          limit: WORKSPACE_MOVEMENTS_PAGE_LIMIT,
          page,
        })

        setWorkspaceMovements((currentMovements) =>
          shouldAppend ? [...currentMovements, ...items] : items,
        )
        setHistoryPage(page)
        setHasMoreHistory(items.length === WORKSPACE_MOVEMENTS_PAGE_LIMIT)

        return items
      } catch (loadError) {
        setHistoryError(getFriendlyError(loadError))
        if (!shouldAppend) {
          setWorkspaceMovements([])
          setHasMoreHistory(false)
        }

        return []
      } finally {
        if (shouldAppend) {
          setIsLoadingMoreHistory(false)
        } else {
          setIsLoadingHistory(false)
        }
      }
    },
    [workspaceId],
  )

  const loadStockData = useCallback(async () => {
    if (!workspaceId) {
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const [categoryItems, readyItems] = await Promise.all([
        listCategories(workspaceId),
        listReplenishments(workspaceId, {
          limit: 100,
          status: 'completed',
        }),
      ])
      setCategories(categoryItems)
      setReadyReplenishments(uniqueReplenishmentsByProduct(readyItems))

      if (activeFilter === 'history') {
        setProducts([])
        await loadWorkspaceHistory({ page: 1 })
        return
      }

      const productRequest =
        activeFilter === 'low-stock'
          ? listLowStockProducts(workspaceId)
          : listProducts(workspaceId, {
              status: activeFilter === 'deleted' ? 'deleted' : 'active',
            })
      const productItems = await productRequest
      const nextProducts =
        activeFilter === 'empty'
          ? productItems.filter((product) => product.quantity === 0)
          : productItems

      setProducts(nextProducts)
    } catch (loadError) {
      setError(getFriendlyError(loadError))
      setReadyReplenishments([])
    } finally {
      setIsLoading(false)
    }
  }, [activeFilter, loadWorkspaceHistory, workspaceId])

  const refreshCategories = useCallback(async () => {
    if (!workspaceId) {
      return []
    }

    const categoryItems = await listCategories(workspaceId)
    setCategories(categoryItems)

    return categoryItems
  }, [workspaceId])

  const loadDeletedCategories = useCallback(async () => {
    if (!workspaceId) {
      return []
    }

    try {
      const categoryItems = await listCategories(workspaceId, {
        status: 'deleted',
      })
      setDeletedCategories(categoryItems)

      return categoryItems
    } catch (loadError) {
      setCategoryManagerError(getFriendlyError(loadError))
      setDeletedCategories([])

      return []
    }
  }, [workspaceId])

  const loadCategoryProducts = useCallback(async () => {
    if (!workspaceId) {
      return []
    }

    setIsLoadingCategoryProducts(true)
    setCategoryManagerError('')

    try {
      const [activeProducts, deletedProducts] = await Promise.all([
        listProducts(workspaceId, {
          limit: 100,
          status: 'active',
        }),
        listProducts(workspaceId, {
          limit: 100,
          status: 'deleted',
        }),
      ])
      setCategoryProducts(activeProducts)
      setDeletedCategoryProducts(deletedProducts)

      return activeProducts
    } catch (loadError) {
      setCategoryManagerError(getFriendlyError(loadError))
      setCategoryProducts([])
      setDeletedCategoryProducts([])

      return []
    } finally {
      setIsLoadingCategoryProducts(false)
    }
  }, [workspaceId])

  const loadProductMovements = useCallback(
    async (productId, options = {}) => {
      if (!workspaceId || !productId) {
        return []
      }

      const page = options.page ?? 1
      const shouldAppend = options.append ?? false

      if (shouldAppend) {
        setIsLoadingMoreMovements(true)
      } else {
        setIsLoadingMovements(true)
      }
      setMovementsError('')

      try {
        const items = await listProductStockMovements(workspaceId, productId, {
          limit: MOVEMENTS_PAGE_LIMIT,
          page,
        })

        setStockMovements((currentMovements) =>
          shouldAppend ? [...currentMovements, ...items] : items,
        )
        setMovementsPage(page)
        setHasMoreMovements(items.length === MOVEMENTS_PAGE_LIMIT)

        return items
      } catch (loadError) {
        setMovementsError(getFriendlyError(loadError))
        if (!shouldAppend) {
          setStockMovements([])
          setHasMoreMovements(false)
        }

        return []
      } finally {
        if (shouldAppend) {
          setIsLoadingMoreMovements(false)
        } else {
          setIsLoadingMovements(false)
        }
      }
    },
    [workspaceId],
  )

  const loadProductDetail = useCallback(
    async (product, options = {}) => {
      if (!workspaceId) {
        return null
      }

      const productId = typeof product === 'object' ? product.id : product
      const includeDeleted =
        options.includeDeleted ??
        (activeFilter === 'deleted' ||
          (typeof product === 'object' && product.is_active === false))

      setIsDetailOpen(true)
      setDetailError('')
      setMovementsError('')
      setStockMovements([])
      setMovementsPage(1)
      setHasMoreMovements(false)

      if (typeof product === 'object') {
        setDetailProduct(product)
      }

      setIsLoadingDetail(true)

      try {
        const nextProduct = await getProduct(workspaceId, productId, {
          includeDeleted,
        })
        setDetailProduct(nextProduct)
        await loadProductMovements(productId, { page: 1 })

        return nextProduct
      } catch (loadError) {
        setDetailError(getFriendlyError(loadError))

        return null
      } finally {
        setIsLoadingDetail(false)
      }
    },
    [activeFilter, loadProductMovements, workspaceId],
  )

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadStockData()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadStockData])

  useEffect(() => {
    if (
      navigationIntent?.type !== 'replenishment-entry' ||
      navigationIntent.workspaceId !== workspaceId ||
      !navigationIntent.request
    ) {
      return
    }

    const replenishment = navigationIntent.request
    const timeoutId = window.setTimeout(() => {
      setMovementProduct({
        category: replenishment.product_category,
        id: replenishment.product_id,
        name: replenishment.product_name,
        replenishmentRequestId: replenishment.id,
      })
      setMovementForm({
        movementType: 'entrada',
        quantity: String(replenishment.quantity_needed),
        reason: `Entrada da reposição · ${
          replenishment.type === 'purchase' ? 'Compra' : 'Produção'
        }`,
      })
      setMovementError('')
      onNavigationIntentHandled?.()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [navigationIntent, onNavigationIntentHandled, workspaceId])

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

  const filteredWorkspaceMovements = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    if (!normalizedSearch) {
      return workspaceMovements
    }

    return workspaceMovements.filter((movement) => {
      const searchableText = [
        movement.product_name,
        movement.movement_type,
        movement.reason,
        movement.user_name,
        movement.user_email,
        String(movement.product_id),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return searchableText.includes(normalizedSearch)
    })
  }, [searchTerm, workspaceMovements])

  const categoryProductCounts = useMemo(() => {
    return categoryProducts.reduce((counts, product) => {
      counts[product.category] = (counts[product.category] ?? 0) + 1
      return counts
    }, {})
  }, [categoryProducts])

  const deletedCategoryProductCounts = useMemo(() => {
    return deletedCategoryProducts.reduce((counts, product) => {
      if (product.deleted_by_category_id) {
        counts[product.deleted_by_category_id] =
          (counts[product.deleted_by_category_id] ?? 0) + 1
      }

      return counts
    }, {})
  }, [deletedCategoryProducts])

  const filteredManagedCategories = useMemo(() => {
    const normalizedSearch = categorySearchTerm.trim().toLowerCase()
    const managedCategories =
      categoryManagerView === 'deleted' ? deletedCategories : categories

    if (!normalizedSearch) {
      return managedCategories
    }

    return managedCategories.filter((category) =>
      [category.name, category.description]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(normalizedSearch),
    )
  }, [
    categories,
    categoryManagerView,
    categorySearchTerm,
    deletedCategories,
  ])

  const editingCategory =
    categories.find((category) => category.id === editingCategoryId) ?? null
  const isRenamingCategory =
    Boolean(editingCategory) &&
    categoryEditForm.name.trim() !== editingCategory.name

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

  function openMovementModal(product, options = {}) {
    const replenishment = options.replenishment

    setMovementProduct(product)
    setMovementForm(
      replenishment
        ? {
            movementType: 'entrada',
            quantity: String(replenishment.quantity_needed),
            reason: `Entrada da reposição · ${
              replenishment.type === 'purchase' ? 'Compra' : 'Produção'
            }`,
          }
        : emptyMovementForm,
    )
    setMovementError('')
  }

  function openReplenishmentModal(product) {
    setReplenishmentProduct(product)
    setReplenishmentError('')
    setSuccessMessage('')
  }

  function closeReplenishmentModal() {
    if (!isSavingReplenishment) {
      setReplenishmentProduct(null)
      setReplenishmentError('')
    }
  }

  async function handleCreateReplenishment(requestData) {
    if (!workspaceId || !replenishmentProduct) {
      return
    }

    setIsSavingReplenishment(true)
    setReplenishmentError('')
    setSuccessMessage('')

    try {
      await createReplenishment(workspaceId, {
        product_id: replenishmentProduct.id,
        ...requestData,
      })
      setReplenishmentProduct(null)
      setSuccessMessage('Necessidade de reposição criada com sucesso.')
      await loadStockData()
    } catch (createError) {
      setReplenishmentError(getFriendlyError(createError))
    } finally {
      setIsSavingReplenishment(false)
    }
  }

  function openReplenishmentEntry(replenishment) {
    openMovementModal(
      {
        category: replenishment.product_category,
        id: replenishment.product_id,
        name: replenishment.product_name,
        replenishmentRequestId: replenishment.id,
      },
      { replenishment },
    )
  }

  function closeDetail() {
    setIsDetailOpen(false)
    setDetailProduct(null)
    setDetailError('')
    setStockMovements([])
    setMovementsPage(1)
    setHasMoreMovements(false)
    setMovementsError('')
  }

  async function loadMoreMovements() {
    if (!detailProduct) {
      return
    }

    await loadProductMovements(detailProduct.id, {
      append: true,
      page: movementsPage + 1,
    })
  }

  async function loadMoreWorkspaceHistory() {
    await loadWorkspaceHistory({
      append: true,
      page: historyPage + 1,
    })
  }

  function openCreateCategoryModal() {
    setCategoryError('')
    setIsCategoryModalOpen(true)
  }

  function openEditCategoriesModal() {
    setEditingCategoryId(null)
    setCategoryEditForm(emptyCategoryForm)
    setCategoryEditError('')
    setCategorySearchTerm('')
    setCategoryManagerError('')
    setCategoryManagerSuccess('')
    setUpdateLinkedProducts(false)
    setCategoryManagerView('active')
    setIsEditCategoriesOpen(true)
    loadCategoryProducts()
    loadDeletedCategories()
  }

  function handleCategoryAction(event) {
    const action = event.target.value

    setCategoryAction('')

    if (action === 'create') {
      openCreateCategoryModal()
    }

    if (action === 'edit') {
      openEditCategoriesModal()
    }
  }

  function openEditCategory(category) {
    setEditingCategoryId(category.id)
    setCategoryEditForm({
      description: category.description ?? '',
      name: category.name ?? '',
    })
    setCategoryEditError('')
    setCategoryManagerSuccess('')
    setUpdateLinkedProducts(false)
  }

  async function handleSaveCategoryEdit(event) {
    event.preventDefault()

    if (!workspaceId || !editingCategoryId) {
      return
    }

    const nextName = categoryEditForm.name.trim()

    if (!nextName) {
      setCategoryEditError('Informe um nome válido para a categoria.')
      return
    }

    setIsSavingCategoryEdit(true)
    setCategoryEditError('')
    setCategoryManagerError('')
    setCategoryManagerSuccess('')

    const originalName = editingCategory?.name ?? ''
    const shouldRenameProducts =
      updateLinkedProducts && Boolean(originalName) && nextName !== originalName
    const linkedProducts = shouldRenameProducts
      ? categoryProducts.filter((product) => product.category === originalName)
      : []
    let categoryWasUpdated = false

    try {
      await updateCategory(workspaceId, editingCategoryId, {
        description: categoryEditForm.description.trim() || null,
        name: nextName,
      })
      categoryWasUpdated = true

      if (linkedProducts.length) {
        await Promise.all(
          linkedProducts.map((product) =>
            updateProduct(workspaceId, product.id, {
              category: nextName,
            }),
          ),
        )
      }

      await refreshCategories()
      await loadCategoryProducts()
      setProducts((currentProducts) =>
        currentProducts.map((product) =>
          shouldRenameProducts && product.category === originalName
            ? { ...product, category: nextName }
            : product,
        ),
      )
      setCategoryFilter((currentFilter) => {
        if (currentFilter !== originalName) {
          return currentFilter
        }

        return shouldRenameProducts ? nextName : 'all'
      })
      setEditingCategoryId(null)
      setCategoryEditForm(emptyCategoryForm)
      setUpdateLinkedProducts(false)
      setCategoryManagerSuccess(
        linkedProducts.length
          ? `Categoria atualizada e ${linkedProducts.length} ${
              linkedProducts.length === 1 ? 'produto vinculado' : 'produtos vinculados'
            } também ${
              linkedProducts.length === 1 ? 'foi atualizado' : 'foram atualizados'
            }.`
          : 'Categoria atualizada com sucesso.',
      )
    } catch (saveError) {
      if (categoryWasUpdated) {
        setCategoryEditError(
          'A categoria foi salva, mas não foi possível atualizar todos os produtos vinculados.',
        )
        await refreshCategories()
        await loadCategoryProducts()
        await loadStockData()
      } else {
        setCategoryEditError(getFriendlyError(saveError))
      }
    } finally {
      setIsSavingCategoryEdit(false)
    }
  }

  async function handleDeleteCategory(category) {
    if (!workspaceId) {
      return
    }

    const linkedProductsCount = categoryProductCounts[category.name] ?? 0

    setCategoryManagerError('')
    setCategoryManagerSuccess('')

    const shouldDelete = window.confirm(
      linkedProductsCount > 0
        ? `Esta categoria possui ${formatLinkedProducts(
            linkedProductsCount,
          ).toLowerCase()}. Ao continuar, a categoria e os produtos ativos vinculados a ela serão enviados para a lixeira. Você poderá restaurá-los depois. Deseja continuar?`
        : 'Tem certeza que deseja enviar esta categoria para a lixeira?',
    )

    if (!shouldDelete) {
      return
    }

    setDeletingCategoryId(category.id)

    try {
      await deleteCategory(workspaceId, category.id)
      const [remainingCategories] = await Promise.all([
        refreshCategories(),
        loadDeletedCategories(),
        loadCategoryProducts(),
        loadStockData(),
      ])

      setCategoryFilter((currentFilter) =>
        currentFilter === category.name ? 'all' : currentFilter,
      )
      setProductForm((currentForm) =>
        currentForm.category === category.name
          ? {
              ...currentForm,
              category: remainingCategories[0]?.name ?? '',
            }
          : currentForm,
      )
      setCategoryManagerSuccess(
        'Categoria enviada para a lixeira com sucesso.',
      )
    } catch (deleteError) {
      setCategoryManagerError(getFriendlyError(deleteError))
    } finally {
      setDeletingCategoryId(null)
    }
  }

  async function handleRestoreCategory(category) {
    if (!workspaceId) {
      return
    }

    setRestoringCategoryId(category.id)
    setCategoryManagerError('')
    setCategoryManagerSuccess('')

    try {
      const restoreResult = await restoreCategory(workspaceId, category.id)
      const [activeCategories] = await Promise.all([
        refreshCategories(),
        loadDeletedCategories(),
        loadCategoryProducts(),
        loadStockData(),
      ])

      setProductForm((currentForm) =>
        currentForm.category
          ? currentForm
          : {
              ...currentForm,
              category: activeCategories[0]?.name ?? '',
            },
      )
      setCategoryManagerSuccess(
        restoreResult.skipped_products_count > 0
          ? `Categoria restaurada. ${restoreResult.skipped_products_count} ${
              restoreResult.skipped_products_count === 1
                ? 'produto não foi restaurado'
                : 'produtos não foram restaurados'
            } por conflito de nome.`
          : 'Categoria restaurada com sucesso.',
      )
    } catch (restoreError) {
      setCategoryManagerError(
        restoreError?.message ===
          'Another active category with this name already exists in this workspace.'
          ? 'Já existe uma categoria ativa com esse nome neste workspace.'
          : getFriendlyError(restoreError),
      )
    } finally {
      setRestoringCategoryId(null)
    }
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
      const editedProductId = productModal.product?.id

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

      if (
        productModal.mode === 'edit' &&
        isDetailOpen &&
        detailProduct?.id === editedProductId
      ) {
        await loadProductDetail(editedProductId, {
          includeDeleted: detailProduct.is_active === false,
        })
      }
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
      const movedProductId = movementProduct.id
      const replenishmentRequestId =
        movementProduct.replenishmentRequestId ?? null

      await createStockMovement(workspaceId, movedProductId, {
        movement_type: movementForm.movementType,
        quantity: Number(movementForm.quantity),
        reason: movementForm.reason.trim() || null,
        replenishment_request_id: replenishmentRequestId,
      })

      setMovementProduct(null)
      setMovementForm(emptyMovementForm)
      setSuccessMessage(
        replenishmentRequestId
          ? 'Entrada registrada e reposição marcada como estocada.'
          : 'Movimentação registrada com sucesso.',
      )
      await loadStockData()

      if (isDetailOpen && detailProduct?.id === movedProductId) {
        await loadProductDetail(movedProductId, {
          includeDeleted: detailProduct.is_active === false,
        })
      }
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

      if (isDetailOpen && detailProduct?.id === product.id) {
        await loadProductDetail(product.id, {
          includeDeleted: true,
        })
      }
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

      if (isDetailOpen && detailProduct?.id === product.id) {
        await loadProductDetail(product.id)
      }
    } catch (restoreError) {
      setError(getFriendlyError(restoreError))
    } finally {
      setActionProductId(null)
    }
  }

  const historyColumns = [
    {
      key: 'created_at',
      label: 'Data',
      render: (movement) => formatDate(movement.created_at),
    },
    {
      key: 'product_name',
      label: 'Produto',
      render: (movement) => (
        <div className="product-cell">
          <strong>{movement.product_name ?? `Produto #${movement.product_id}`}</strong>
          <span>ID {movement.product_id}</span>
        </div>
      ),
    },
    {
      key: 'movement_type',
      label: 'Tipo',
      render: (movement) => (
        <Badge tone={MOVEMENT_TONES[movement.movement_type] ?? 'neutral'}>
          {MOVEMENT_LABELS[movement.movement_type] ?? movement.movement_type}
        </Badge>
      ),
    },
    { key: 'quantity', label: 'Quantidade' },
    { key: 'quantity_before', label: 'Antes' },
    { key: 'quantity_after', label: 'Depois' },
    {
      key: 'user',
      label: 'Usuário',
      render: (movement) =>
        movement.user_name ?? movement.user_email ?? 'Usuário não informado',
    },
    {
      key: 'reason',
      label: 'Motivo',
      render: (movement) => movement.reason || 'Sem observação',
    },
  ]

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
          <div className="table-actions table-actions--compact">
            <button
              className="table-action table-action--view"
              type="button"
              onClick={() =>
                loadProductDetail(product, {
                  includeDeleted: true,
                })
              }
            >
              Ver
            </button>
            <button
              className="table-action table-action--restore"
              disabled={actionProductId === product.id}
              type="button"
              onClick={() => handleRestoreProduct(product)}
            >
              Restaurar
            </button>
          </div>
        ) : (
          <div className="table-actions">
            <button
              className="table-action table-action--view"
              type="button"
              onClick={() => loadProductDetail(product)}
            >
              Ver
            </button>
            <button
              className="table-action table-action--movement"
              type="button"
              onClick={() => openMovementModal(product)}
            >
              Movimentar
            </button>
            <button
              className="table-action table-action--edit"
              type="button"
              onClick={() => openEditProduct(product)}
            >
              Editar
            </button>
            <button
              className="table-action table-action--replenish"
              type="button"
              onClick={() => openReplenishmentModal(product)}
            >
              Repor
            </button>
            <button
              className="table-action table-action--delete"
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
          <p>Gerencie produtos, categorias e quantidades do workspace</p>
        </div>
        <div className="page-heading__actions">
          <select
            aria-label="Ações de categorias"
            className="category-action-select"
            onChange={handleCategoryAction}
            value={categoryAction}
          >
            <option disabled value="">
              Categorias
            </option>
            <option value="create">Nova categoria</option>
            <option value="edit">Editar categorias</option>
          </select>
          <Button icon="+" onClick={openCreateProduct}>
            Novo produto
          </Button>
        </div>
      </div>

      <Card
        action={
          readyReplenishments.length ? (
            <Badge tone="neutral">{readyReplenishments.length} prontas</Badge>
          ) : null
        }
        className="stock-ready-replenishments"
        title="Reposições prontas para estocar"
        eyebrow="Entrada pendente"
      >
        {readyReplenishments.length ? (
          <div className="stock-ready-replenishments__list">
            {readyReplenishments.map((replenishment) => (
              <div
                className="stock-ready-replenishment"
                key={replenishment.id}
              >
                <div>
                  <strong>{replenishment.product_name}</strong>
                  <span>
                    {replenishment.type === 'purchase' ? 'Compra' : 'Produção'} ·{' '}
                    {replenishment.quantity_needed} un. previstas
                  </span>
                </div>
                <Button
                  className="stock-ready-replenishment__action"
                  onClick={() => openReplenishmentEntry(replenishment)}
                  size="sm"
                >
                  Registrar entrada
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="stock-ready-replenishments__empty">
            Nenhuma reposição aguardando entrada em estoque.
          </p>
        )}
      </Card>

      <Card className="stock-panel">
        <div className="stock-toolbar">
          <label className="stock-search">
            <input
              type="search"
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={
                activeFilter === 'history'
                  ? 'Buscar por produto, usuário, tipo ou motivo'
                  : 'Buscar por nome, categoria ou ID'
              }
              value={searchTerm}
            />
          </label>
          <select
            disabled={activeFilter === 'history'}
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
          <div className="stock-loading">
            {activeFilter === 'history'
              ? 'Carregando histórico...'
              : 'Carregando estoque...'}
          </div>
        ) : activeFilter === 'history' ? (
          <>
            {historyError ? (
              <p className="stock-feedback stock-feedback--error">{historyError}</p>
            ) : null}
            {filteredWorkspaceMovements.length ? (
              <>
                <DataTable
                  columns={historyColumns}
                  rows={filteredWorkspaceMovements}
                />
                {hasMoreHistory ? (
                  <button
                    className="load-more-button"
                    disabled={isLoadingMoreHistory || isLoadingHistory}
                    type="button"
                    onClick={loadMoreWorkspaceHistory}
                  >
                    {isLoadingMoreHistory
                      ? 'Carregando histórico...'
                      : 'Carregar mais'}
                  </button>
                ) : null}
              </>
            ) : (
              <div className="stock-empty">
                <h2>Nenhuma movimentação encontrada</h2>
                <p>
                  As entradas, saídas e ajustes do workspace aparecerão aqui.
                </p>
              </div>
            )}
          </>
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

      {isDetailOpen ? (
        <div className="drawer-backdrop" role="presentation">
          <aside
            className="product-detail-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Detalhe do produto"
          >
            <div className="product-detail-drawer__header">
              <div>
                <span>Detalhe do produto</span>
                <h2>{detailProduct?.name ?? 'Carregando produto...'}</h2>
              </div>
              <button
                aria-label="Fechar detalhe"
                className="icon-button"
                type="button"
                onClick={closeDetail}
              >
                x
              </button>
            </div>

            {isLoadingDetail && !detailProduct ? (
              <div className="stock-loading">Carregando detalhe...</div>
            ) : detailError ? (
              <p className="stock-feedback stock-feedback--error">{detailError}</p>
            ) : detailProduct ? (
              <>
                <div className="product-detail-drawer__title">
                  <Badge tone={getProductStatus(detailProduct).tone}>
                    {getProductStatus(detailProduct).label}
                  </Badge>
                  <span>ID {detailProduct.id}</span>
                </div>

                <div className="product-detail-metrics">
                  <div>
                    <span>Quantidade atual</span>
                    <strong>{detailProduct.quantity}</strong>
                  </div>
                  <div>
                    <span>Quantidade mínima</span>
                    <strong>{detailProduct.minimum_quantity}</strong>
                  </div>
                  <div>
                    <span>Categoria</span>
                    <strong>{detailProduct.category}</strong>
                  </div>
                </div>

                <div className="product-detail-meta">
                  <div>
                    <span>Criado em</span>
                    <strong>{formatDate(detailProduct.created_at)}</strong>
                  </div>
                  <div>
                    <span>Atualizado em</span>
                    <strong>{formatDate(detailProduct.updated_at)}</strong>
                  </div>
                  {!detailProduct.is_active ? (
                    <>
                      <div>
                        <span>Removido em</span>
                        <strong>{formatDate(detailProduct.deleted_at)}</strong>
                      </div>
                      <div>
                        <span>Removido por</span>
                        <strong>
                          {detailProduct.deleted_by_user_id
                            ? `Usuário #${detailProduct.deleted_by_user_id}`
                            : 'Não informado'}
                        </strong>
                      </div>
                    </>
                  ) : null}
                </div>

                <section className="product-detail-actions">
                  <h3>Ações rápidas</h3>
                  <div className="workspace-form__actions">
                    {detailProduct.is_active ? (
                      <>
                        <Button
                          onClick={() => openMovementModal(detailProduct)}
                          variant="secondary"
                        >
                          Movimentar estoque
                        </Button>
                        <Button
                          onClick={() => openEditProduct(detailProduct)}
                          variant="secondary"
                        >
                          Editar produto
                        </Button>
                        <Button
                          disabled={actionProductId === detailProduct.id}
                          onClick={() => handleDeleteProduct(detailProduct)}
                          variant="secondary"
                        >
                          Enviar para lixeira
                        </Button>
                      </>
                    ) : (
                      <Button
                        disabled={actionProductId === detailProduct.id}
                        onClick={() => handleRestoreProduct(detailProduct)}
                      >
                        Restaurar produto
                      </Button>
                    )}
                  </div>
                </section>

                <section className="product-movements">
                  <div className="product-movements__header">
                    <div>
                      <h3>Histórico de movimentações</h3>
                      <p>
                        {stockMovements.length
                          ? `Mostrando ${stockMovements.length} movimentações`
                          : 'Entradas, saídas e ajustes registrados no workspace.'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => loadProductMovements(detailProduct.id, { page: 1 })}
                    >
                      Atualizar
                    </button>
                  </div>

                  {isLoadingMovements ? (
                    <div className="stock-loading">Carregando movimentações...</div>
                  ) : movementsError ? (
                    <p className="stock-feedback stock-feedback--error">
                      {movementsError}
                    </p>
                  ) : stockMovements.length ? (
                    <div className="movement-list">
                      {stockMovements.map((movement) => (
                        <article className="movement-item" key={movement.id}>
                          <div className="movement-item__top">
                            <Badge
                              tone={
                                MOVEMENT_TONES[movement.movement_type] ?? 'neutral'
                              }
                            >
                              {MOVEMENT_LABELS[movement.movement_type] ??
                                movement.movement_type}
                            </Badge>
                            <span>{formatDate(movement.created_at)}</span>
                          </div>
                          <div className="movement-item__numbers">
                            <div>
                              <span>Quantidade</span>
                              <strong>{movement.quantity}</strong>
                            </div>
                            <div>
                              <span>Antes</span>
                              <strong>{movement.quantity_before}</strong>
                            </div>
                            <div>
                              <span>Depois</span>
                              <strong>{movement.quantity_after}</strong>
                            </div>
                          </div>
                          <div className="movement-item__meta">
                            <span>
                              {movement.user_name ??
                                movement.user_email ??
                                'Usuário não informado'}
                            </span>
                            <p>{movement.reason || 'Sem observação.'}</p>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="stock-empty">
                      <h2>Nenhuma movimentação registrada ainda.</h2>
                      <p>
                        Movimente o estoque deste produto para começar o histórico.
                      </p>
                    </div>
                  )}

                  {hasMoreMovements && !isLoadingMovements ? (
                    <button
                      className="load-more-button"
                      disabled={isLoadingMoreMovements}
                      type="button"
                      onClick={loadMoreMovements}
                    >
                      {isLoadingMoreMovements ? 'Carregando histórico...' : 'Carregar mais'}
                    </button>
                  ) : null}
                </section>
              </>
            ) : null}
          </aside>
        </div>
      ) : null}

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
                  Crie uma categoria antes de salvar produtos.
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

      {replenishmentProduct ? (
        <ReplenishmentCreationModal
          error={replenishmentError}
          isSaving={isSavingReplenishment}
          onClose={closeReplenishmentModal}
          onSubmit={handleCreateReplenishment}
          product={replenishmentProduct}
        />
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
              {movementProduct.replenishmentRequestId ? (
                <p className="stock-form__hint">
                  A quantidade veio como previsão da reposição. Confirme os dados
                  abaixo para registrar a entrada real no estoque.
                </p>
              ) : null}
              <label>
                Tipo
                <select
                  disabled={Boolean(
                    movementProduct.replenishmentRequestId,
                  )}
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
                  {isMovingStock
                    ? 'Registrando...'
                    : movementProduct.replenishmentRequestId
                      ? 'Registrar entrada'
                      : 'Registrar movimentação'}
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

      {isEditCategoriesOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section
            aria-labelledby="category-manager-title"
            aria-modal="true"
            className="workspace-modal stock-modal category-manager-modal"
            role="dialog"
          >
            <div className="workspace-modal__header">
              <div>
                <span>Categorias</span>
                <h2 id="category-manager-title">Gerenciar categorias</h2>
                <p>Organize os grupos usados nos produtos do estoque.</p>
              </div>
              <button
                aria-label="Fechar modal"
                className="icon-button"
                type="button"
                onClick={() => {
                  setIsEditCategoriesOpen(false)
                  setEditingCategoryId(null)
                }}
              >
                x
              </button>
            </div>

            <div
              aria-label="Visualização das categorias"
              className="category-manager-tabs"
              role="tablist"
            >
              <button
                aria-selected={categoryManagerView === 'active'}
                className={categoryManagerView === 'active' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => {
                  setCategoryManagerView('active')
                  setEditingCategoryId(null)
                  setCategoryManagerError('')
                  setCategoryManagerSuccess('')
                }}
              >
                Ativas
                <span>{categories.length}</span>
              </button>
              <button
                aria-selected={categoryManagerView === 'deleted'}
                className={categoryManagerView === 'deleted' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => {
                  setCategoryManagerView('deleted')
                  setEditingCategoryId(null)
                  setCategoryManagerError('')
                  setCategoryManagerSuccess('')
                }}
              >
                Lixeira
                <span>{deletedCategories.length}</span>
              </button>
            </div>

            <div
              className={`category-manager-toolbar ${
                categoryManagerView === 'deleted' ? 'is-trash' : ''
              }`}
            >
              <label className="category-manager-search">
                <span>Buscar categoria</span>
                <input
                  onChange={(event) => setCategorySearchTerm(event.target.value)}
                  placeholder="Buscar categoria..."
                  type="search"
                  value={categorySearchTerm}
                />
              </label>
              {categoryManagerView === 'active' ? (
                <Button
                  onClick={() => {
                    setIsEditCategoriesOpen(false)
                    openCreateCategoryModal()
                  }}
                  variant="secondary"
                >
                  Nova categoria
                </Button>
              ) : null}
            </div>

            {isLoadingCategoryProducts ? (
              <p className="category-manager-status">
                Calculando produtos vinculados...
              </p>
            ) : null}
            {categoryManagerError ? (
              <p className="stock-feedback stock-feedback--error">
                {categoryManagerError}
              </p>
            ) : null}
            {categoryManagerSuccess ? (
              <p className="stock-feedback stock-feedback--success">
                {categoryManagerSuccess}
              </p>
            ) : null}

            {filteredManagedCategories.length ? (
              <div className="category-editor-list">
                {filteredManagedCategories.map((category) => (
                  <article
                    className={`category-editor-item ${
                      categoryManagerView === 'active' &&
                      editingCategoryId === category.id
                        ? 'is-editing'
                        : ''
                    }`}
                    key={category.id}
                  >
                    {categoryManagerView === 'deleted' ? (
                      <>
                        <div className="category-editor-item__copy">
                          <strong>{category.name}</strong>
                          <p>{category.description || 'Sem descrição.'}</p>
                          <span>
                            Excluída em {formatDate(category.deleted_at)}
                          </span>
                          <span>
                            {formatProductsRemovedWithCategory(
                              deletedCategoryProductCounts[category.id] ?? 0,
                            )}
                          </span>
                        </div>
                        <div className="category-editor-item__actions">
                          <button
                            className="category-editor-item__restore"
                            disabled={restoringCategoryId === category.id}
                            type="button"
                            onClick={() => handleRestoreCategory(category)}
                          >
                            {restoringCategoryId === category.id
                              ? 'Restaurando...'
                              : 'Restaurar'}
                          </button>
                        </div>
                      </>
                    ) : editingCategoryId === category.id ? (
                      <form
                        className="stock-form category-editor-form"
                        onSubmit={handleSaveCategoryEdit}
                      >
                        <div className="category-editor-form__heading">
                          <div>
                            <strong>Editar categoria</strong>
                            <span>Atualize o nome e a descrição deste grupo.</span>
                          </div>
                        </div>
                        <label>
                          Nome
                          <input
                            maxLength="100"
                            onChange={(event) =>
                              setCategoryEditForm((currentForm) => ({
                                ...currentForm,
                                name: event.target.value,
                              }))
                            }
                            required
                            value={categoryEditForm.name}
                          />
                        </label>
                        <label>
                          Descrição
                          <textarea
                            maxLength="255"
                            onChange={(event) =>
                              setCategoryEditForm((currentForm) => ({
                                ...currentForm,
                                description: event.target.value,
                              }))
                            }
                            placeholder="Descrição opcional"
                            value={categoryEditForm.description}
                          />
                        </label>
                        {isRenamingCategory ? (
                          <div className="category-rename-options">
                            <label className="category-update-products">
                              <input
                                checked={updateLinkedProducts}
                                onChange={(event) =>
                                  setUpdateLinkedProducts(event.target.checked)
                                }
                                type="checkbox"
                              />
                              <span>
                                Atualizar produtos que usam esta categoria
                              </span>
                            </label>
                            <p>
                              {updateLinkedProducts
                                ? formatProductsToUpdate(
                                    categoryProductCounts[category.name] ?? 0,
                                  )
                                : 'Produtos existentes podem continuar vinculados ao nome antigo.'}
                            </p>
                          </div>
                        ) : null}
                        {categoryEditError ? (
                          <p className="form-error">{categoryEditError}</p>
                        ) : null}
                        <div className="workspace-form__actions">
                          <Button disabled={isSavingCategoryEdit} type="submit">
                            {isSavingCategoryEdit ? 'Salvando...' : 'Salvar'}
                          </Button>
                          <Button
                            disabled={isSavingCategoryEdit}
                            onClick={() => {
                              setEditingCategoryId(null)
                              setCategoryEditError('')
                              setUpdateLinkedProducts(false)
                            }}
                            variant="secondary"
                          >
                            Cancelar
                          </Button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="category-editor-item__copy">
                          <strong>{category.name}</strong>
                          <p>{category.description || 'Sem descrição.'}</p>
                          <span>
                            {formatLinkedProducts(
                              categoryProductCounts[category.name] ?? 0,
                            )}
                          </span>
                        </div>
                        <div className="category-editor-item__actions">
                          <button
                            className="category-editor-item__edit"
                            disabled={deletingCategoryId === category.id}
                            type="button"
                            onClick={() => openEditCategory(category)}
                          >
                            Editar
                          </button>
                          <button
                            className="category-editor-item__delete"
                            disabled={deletingCategoryId === category.id}
                            type="button"
                            onClick={() => handleDeleteCategory(category)}
                          >
                            {deletingCategoryId === category.id
                              ? 'Excluindo...'
                              : 'Excluir'}
                          </button>
                        </div>
                      </>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="stock-empty">
                <h2>
                  {(categoryManagerView === 'deleted'
                    ? deletedCategories
                    : categories
                  ).length
                    ? 'Nenhuma categoria encontrada'
                    : categoryManagerView === 'deleted'
                      ? 'A lixeira está vazia'
                      : 'Nenhuma categoria cadastrada'}
                </h2>
                <p>
                  {(categoryManagerView === 'deleted'
                    ? deletedCategories
                    : categories
                  ).length
                    ? 'Tente buscar usando outro nome ou descrição.'
                    : categoryManagerView === 'deleted'
                      ? 'Categorias enviadas para a lixeira aparecerão aqui.'
                      : 'Crie uma categoria para organizar os produtos do estoque.'}
                </p>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default StockPage

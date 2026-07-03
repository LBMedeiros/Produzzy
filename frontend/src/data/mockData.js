export const workspace = {
  name: 'Bordados Medeiros',
  plan: 'Workspace principal',
  user: {
    name: 'Lucas Medeiros',
    role: 'Admin',
    initials: 'LM',
  },
}

export const categories = [
  'Todas as categorias',
  'Vestuário',
  'Insumos',
  'Etiquetas',
  'Especialidades',
  'Camisas',
]

export const dashboardMetrics = [
  {
    label: 'Produtos ativos',
    value: '236',
    trend: '+12 neste mês',
    tone: 'blue',
  },
  {
    label: 'Baixo estoque',
    value: '18',
    trend: '7 precisam produzir',
    tone: 'yellow',
  },
  {
    label: 'Em produção',
    value: '9',
    trend: '3 aguardam conferência',
    tone: 'green',
  },
  {
    label: 'Movimentações recentes',
    value: '96',
    trend: 'últimos 7 dias',
    tone: 'slate',
  },
]

export const products = [
  {
    id: 1024,
    name: 'Camiseta algodão premium',
    category: 'Camisas',
    quantity: 124,
    minimumQuantity: 140,
    status: 'Baixo estoque',
    statusTone: 'warning',
    updatedAt: 'Hoje, 09:42',
  },
  {
    id: 1025,
    name: 'Linha azul marinho',
    category: 'Insumos',
    quantity: 8,
    minimumQuantity: 25,
    status: 'Baixo estoque',
    statusTone: 'warning',
    updatedAt: 'Ontem, 17:10',
  },
  {
    id: 1026,
    name: 'Boné trucker bordado',
    category: 'Vestuário',
    quantity: 56,
    minimumQuantity: 20,
    status: 'Em estoque',
    statusTone: 'success',
    updatedAt: 'Segunda, 14:22',
  },
  {
    id: 1027,
    name: 'Etiqueta interna P',
    category: 'Etiquetas',
    quantity: 0,
    minimumQuantity: 100,
    status: 'Sem estoque',
    statusTone: 'danger',
    updatedAt: '12 Jun, 11:05',
  },
  {
    id: 1028,
    name: 'Patch especial aniversario',
    category: 'Especialidades',
    quantity: 42,
    minimumQuantity: 15,
    status: 'Em estoque',
    statusTone: 'success',
    updatedAt: '11 Jun, 16:30',
  },
  {
    id: 1029,
    name: 'Matriz floral antiga',
    category: 'Especialidades',
    quantity: 0,
    minimumQuantity: 0,
    status: 'Inativo',
    statusTone: 'neutral',
    updatedAt: '08 Jun, 10:12',
  },
]

export const attentionProducts = products.filter((product) =>
  ['Baixo estoque', 'Sem estoque'].includes(product.status),
)

export const movements = [
  {
    id: 1,
    product: 'Camiseta algodão premium',
    type: 'Entrada',
    quantity: '+40',
    user: 'Lucas Medeiros',
    time: 'há 12 min',
  },
  {
    id: 2,
    product: 'Linha azul marinho',
    type: 'Saída',
    quantity: '-6',
    user: 'Marina Costa',
    time: 'há 48 min',
  },
  {
    id: 3,
    product: 'Boné trucker bordado',
    type: 'Ajuste',
    quantity: '56',
    user: 'Rafael Nunes',
    time: 'ontem',
  },
]

export const activities = [
  {
    id: 1,
    title: 'Linha azul marinho entrou em produção',
    detail: 'Marina assumiu a reposição de 60 unidades.',
    time: 'há 18 min',
  },
  {
    id: 2,
    title: 'Etiqueta interna P foi sinalizada sem estoque',
    detail: 'Tarefa criada automaticamente a partir do estoque mínimo.',
    time: 'há 1 h',
  },
  {
    id: 3,
    title: 'Etiquetas para impressão geradas para Camiseta premium',
    detail: '12 etiquetas prontas para impressão.',
    time: 'ontem',
  },
]

export const roleDescriptions = [
  {
    role: 'Owner',
    description: 'Controle total do workspace, membros, convites e produtos.',
  },
  {
    role: 'Admin',
    description: 'Gerencia produtos, estoque, categorias e convites operacionais.',
  },
  {
    role: 'Employee',
    description: 'Consulta dados e registra movimentações de estoque.',
  },
  {
    role: 'Viewer',
    description: 'Acompanha indicadores e dados sem alterar informações.',
  },
]

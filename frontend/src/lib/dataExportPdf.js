import { jsPDF } from 'jspdf'

import { humanizeAuditAction } from './formatters'

// Builds the "Baixar meus dados" (LGPD) document: a readable report in the
// app's visual language (light surfaces, blue accent, cards, tables). Plain
// layout math on A4 in millimetres, so it reads well on screen and in print.

const PAGE = { height: 297, width: 210 }
const MARGIN = { bottom: 22, left: 16, right: 16, top: 18 }
const CONTENT_WIDTH = PAGE.width - MARGIN.left - MARGIN.right
const CONTENT_RIGHT = PAGE.width - MARGIN.right
const LINE = 4.6 // mm per line of 9.5pt text

const CONTACT_NAME = 'Lucas Medeiros'
const CONTACT_EMAIL = 'lucasmedbasil@gmail.com'

const COLOR = {
  blue: [37, 99, 235],
  blueSoft: [234, 241, 254],
  border: [226, 232, 240],
  faint: [138, 153, 174],
  muted: [91, 107, 130],
  navy: [15, 23, 42],
  surface: [245, 248, 252],
  white: [255, 255, 255],
}

const ROLE_LABELS = {
  admin: 'Administrador',
  employee: 'Funcionário',
  owner: 'Dono',
  viewer: 'Visualizador',
}

function roleLabel(role) {
  return ROLE_LABELS[role] ?? role ?? '—'
}

function formatDate(value) {
  if (!value) {
    return '—'
  }

  try {
    return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long' }).format(
      new Date(value),
    )
  } catch {
    return String(value)
  }
}

function formatDateTime(value) {
  if (!value) {
    return '—'
  }

  try {
    return new Intl.DateTimeFormat('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return String(value)
  }
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value) || 0)
}

function initials(name) {
  const parts = String(name ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (!parts.length) {
    return '?'
  }

  const first = parts[0][0]
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return `${first}${last}`.toUpperCase()
}

function setText(doc, [r, g, b]) {
  doc.setTextColor(r, g, b)
}

function setDraw(doc, [r, g, b]) {
  doc.setDrawColor(r, g, b)
}

function setFill(doc, [r, g, b]) {
  doc.setFillColor(r, g, b)
}

function font(doc, style, size, color) {
  doc.setFont('helvetica', style)
  doc.setFontSize(size)
  setText(doc, color)
}

// Pages after the first get a slim running header so loose sheets stay
// identifiable once printed.
function addPage(ctx) {
  const { doc } = ctx
  doc.addPage()

  setFill(doc, COLOR.blue)
  doc.rect(0, 0, PAGE.width, 2, 'F')
  font(doc, 'bold', 8.5, COLOR.navy)
  doc.text('Seus dados no Produzzy', MARGIN.left, 10)
  font(doc, 'normal', 8.5, COLOR.muted)
  doc.text(ctx.ownerName, CONTENT_RIGHT, 10, { align: 'right' })
  setDraw(doc, COLOR.border)
  doc.setLineWidth(0.2)
  doc.line(MARGIN.left, 13, CONTENT_RIGHT, 13)

  ctx.y = MARGIN.top + 2
}

// Reserve vertical space; start a new page when the current one is full.
function ensureSpace(ctx, needed) {
  if (ctx.y + needed > PAGE.height - MARGIN.bottom) {
    addPage(ctx)
    return true
  }

  return false
}

function drawCover(ctx, data, logo) {
  const { doc } = ctx

  setFill(doc, COLOR.blue)
  doc.rect(0, 0, PAGE.width, 3, 'F')

  let brandX = MARGIN.left
  if (logo) {
    try {
      doc.addImage(logo, 'PNG', MARGIN.left, 11, 9, 9, undefined, 'FAST')
      brandX = MARGIN.left + 12
    } catch {
      // Without the logo the wordmark alone still identifies the document.
    }
  }

  font(doc, 'bold', 13, COLOR.navy)
  doc.text('Produzzy', brandX, 17.3)

  font(doc, 'normal', 8.5, COLOR.muted)
  doc.text('Relatório de dados pessoais', CONTENT_RIGHT, 14.2, { align: 'right' })
  doc.text(`Gerado em ${formatDateTime(data?.exported_at)}`, CONTENT_RIGHT, 18.6, {
    align: 'right',
  })

  font(doc, 'bold', 24, COLOR.navy)
  doc.text('Seus dados no Produzzy', MARGIN.left, 40)

  font(doc, 'normal', 10.5, COLOR.muted)
  const intro = doc.splitTextToSize(
    'Esta é uma cópia das informações pessoais que o Produzzy guarda sobre ' +
      'você, gerada a seu pedido conforme a Lei Geral de Proteção de Dados ' +
      '(Lei nº 13.709/2018).',
    CONTENT_WIDTH,
  )
  doc.text(intro, MARGIN.left, 48)

  ctx.y = 48 + intro.length * 5 + 6
}

function drawProfileCard(ctx, account) {
  const { doc } = ctx
  const top = ctx.y
  const height = 24

  setFill(doc, COLOR.surface)
  setDraw(doc, COLOR.border)
  doc.setLineWidth(0.25)
  doc.roundedRect(MARGIN.left, top, CONTENT_WIDTH, height, 3, 3, 'FD')

  const avatarX = MARGIN.left + 13
  const avatarY = top + height / 2
  setFill(doc, COLOR.blue)
  doc.circle(avatarX, avatarY, 7, 'F')
  font(doc, 'bold', 11, COLOR.white)
  doc.text(initials(account.name), avatarX, avatarY + 1.4, { align: 'center' })

  const textX = MARGIN.left + 25
  font(doc, 'bold', 13, COLOR.navy)
  doc.text(String(account.name ?? '—'), textX, top + 10.5)
  font(doc, 'normal', 9.5, COLOR.muted)
  doc.text(String(account.email ?? '—'), textX, top + 16.5)

  const pill =
    account.auth_provider === 'google' ? 'Login com Google' : 'Login com e-mail e senha'
  font(doc, 'bold', 8, COLOR.blue)
  const pillWidth = doc.getTextWidth(pill) + 8
  const pillX = CONTENT_RIGHT - 6 - pillWidth
  setFill(doc, COLOR.blueSoft)
  doc.roundedRect(pillX, avatarY - 3.6, pillWidth, 7.2, 3.6, 3.6, 'F')
  doc.text(pill, pillX + pillWidth / 2, avatarY + 1, { align: 'center' })

  ctx.y = top + height + 6
}

function drawStatTiles(ctx, tiles) {
  const { doc } = ctx
  const gap = 4
  const width = (CONTENT_WIDTH - gap * (tiles.length - 1)) / tiles.length
  const height = 20
  const top = ctx.y

  tiles.forEach((tile, index) => {
    const x = MARGIN.left + index * (width + gap)

    setFill(doc, COLOR.white)
    setDraw(doc, COLOR.border)
    doc.setLineWidth(0.25)
    doc.roundedRect(x, top, width, height, 2.5, 2.5, 'FD')

    font(doc, 'bold', 16, COLOR.blue)
    doc.text(formatNumber(tile.value), x + 5, top + 10)
    font(doc, 'normal', 8.5, COLOR.muted)
    doc.text(tile.label, x + 5, top + 15.5)
  })

  ctx.y = top + height + 4
}

function sectionTitle(ctx, title, subtitle) {
  const { doc } = ctx
  ensureSpace(ctx, subtitle ? 26 : 20)
  ctx.y += 6

  setFill(doc, COLOR.blue)
  doc.roundedRect(MARGIN.left, ctx.y - 4.2, 1.4, 5.4, 0.7, 0.7, 'F')
  font(doc, 'bold', 12.5, COLOR.navy)
  doc.text(title, MARGIN.left + 4, ctx.y)
  ctx.y += 5

  if (subtitle) {
    font(doc, 'normal', 9, COLOR.muted)
    const lines = doc.splitTextToSize(subtitle, CONTENT_WIDTH - 4)
    doc.text(lines, MARGIN.left + 4, ctx.y)
    ctx.y += lines.length * 4.2
  }

  ctx.y += 2.5
}

// Label/value pairs laid out two per row inside a card.
function drawFieldGrid(ctx, fields) {
  const { doc } = ctx
  const padding = 6
  const columnGap = 8
  const columnWidth = (CONTENT_WIDTH - padding * 2 - columnGap) / 2

  font(doc, 'normal', 9.5, COLOR.navy)
  const rows = []
  for (let index = 0; index < fields.length; index += 2) {
    const pair = fields.slice(index, index + 2).map((item) => ({
      ...item,
      lines: doc.splitTextToSize(String(item.value ?? '—'), columnWidth),
    }))
    const lineCount = Math.max(...pair.map((item) => item.lines.length))
    rows.push({ height: 5 + lineCount * LINE + 3, pair })
  }

  const height = rows.reduce((sum, row) => sum + row.height, 0) + padding
  ensureSpace(ctx, height)
  const top = ctx.y

  setFill(doc, COLOR.white)
  setDraw(doc, COLOR.border)
  doc.setLineWidth(0.25)
  doc.roundedRect(MARGIN.left, top, CONTENT_WIDTH, height, 3, 3, 'FD')

  let y = top + padding + 1
  rows.forEach((row) => {
    row.pair.forEach((item, column) => {
      const x = MARGIN.left + padding + column * (columnWidth + columnGap)
      font(doc, 'normal', 8, COLOR.faint)
      doc.text(item.label.toUpperCase(), x, y)
      font(doc, 'normal', 9.5, COLOR.navy)
      doc.text(item.lines, x, y + 5)
    })
    y += row.height
  })

  ctx.y = top + height + 2
}

// A table with a tinted header row that repeats on every new page, zebra
// rows and wrapping cells. `columns` widths are fractions of the content width.
function drawTable(ctx, columns, rows) {
  const { doc } = ctx
  const cellPadding = 3
  const widths = columns.map((column) => column.width * CONTENT_WIDTH)

  function drawHead() {
    const height = 8
    setFill(doc, COLOR.surface)
    doc.roundedRect(MARGIN.left, ctx.y, CONTENT_WIDTH, height, 2, 2, 'F')
    font(doc, 'bold', 8, COLOR.muted)

    let x = MARGIN.left
    columns.forEach((column, index) => {
      const textX =
        column.align === 'right' ? x + widths[index] - cellPadding : x + cellPadding
      doc.text(column.title.toUpperCase(), textX, ctx.y + 5.3, {
        align: column.align === 'right' ? 'right' : 'left',
      })
      x += widths[index]
    })

    ctx.y += height + 1
  }

  ensureSpace(ctx, 18)
  drawHead()

  rows.forEach((row, rowIndex) => {
    font(doc, 'normal', 9.5, COLOR.navy)
    const cells = columns.map((column, index) => {
      // A cell is plain text or { text, sub } for a muted second line.
      const raw = row[column.key]
      const value = raw !== null && typeof raw === 'object' ? raw : { text: raw }
      const main = doc.splitTextToSize(
        String(value.text ?? '—'),
        widths[index] - cellPadding * 2,
      )
      const sub = value.sub
        ? doc.splitTextToSize(String(value.sub), widths[index] - cellPadding * 2)
        : []
      return { main, sub }
    })
    const lineCount = Math.max(
      ...cells.map((cell) => cell.main.length + cell.sub.length),
    )
    const height = lineCount * LINE + 3.4

    if (ensureSpace(ctx, height)) {
      drawHead()
    }

    if (rowIndex % 2 === 1) {
      setFill(doc, COLOR.surface)
      doc.rect(MARGIN.left, ctx.y, CONTENT_WIDTH, height, 'F')
    }

    let x = MARGIN.left
    cells.forEach((cell, index) => {
      const column = columns[index]
      const align = column.align === 'right' ? 'right' : 'left'
      const textX = align === 'right' ? x + widths[index] - cellPadding : x + cellPadding
      const baseline = ctx.y + 4.6

      font(doc, column.bold ? 'bold' : 'normal', 9.5, COLOR.navy)
      doc.text(cell.main, textX, baseline, { align })

      if (cell.sub.length) {
        font(doc, 'normal', 8.5, COLOR.muted)
        doc.text(cell.sub, textX, baseline + cell.main.length * LINE, { align })
      }

      x += widths[index]
    })

    ctx.y += height
    setDraw(doc, COLOR.border)
    doc.setLineWidth(0.15)
    doc.line(MARGIN.left, ctx.y, CONTENT_RIGHT, ctx.y)
  })

  ctx.y += 2
}

function emptyState(ctx, text) {
  const { doc } = ctx
  ensureSpace(ctx, 14)
  setDraw(doc, COLOR.border)
  doc.setLineWidth(0.25)
  doc.setLineDashPattern([1.2, 1.2], 0)
  doc.roundedRect(MARGIN.left, ctx.y, CONTENT_WIDTH, 11, 2.5, 2.5, 'S')
  doc.setLineDashPattern([], 0)
  font(doc, 'normal', 9.5, COLOR.muted)
  doc.text(text, PAGE.width / 2, ctx.y + 6.8, { align: 'center' })
  ctx.y += 13
}

function note(ctx, text) {
  const { doc } = ctx
  font(doc, 'normal', 8.5, COLOR.faint)
  const lines = doc.splitTextToSize(text, CONTENT_WIDTH)
  ensureSpace(ctx, lines.length * 4 + 2)
  doc.text(lines, MARGIN.left, ctx.y + 3)
  ctx.y += lines.length * 4 + 2
}

function drawRightsBox(ctx) {
  const { doc } = ctx
  const padding = 6
  const textWidth = CONTENT_WIDTH - padding * 2 - 3
  const rights = [
    'Corrigir seus dados a qualquer momento em Configurações.',
    'Baixar uma nova cópia destes dados em Configurações > Privacidade e dados.',
    'Excluir sua conta: seus dados pessoais são removidos ou anonimizados.',
    'Saber com quem seus dados são compartilhados, revogar consentimentos e ' +
      'reclamar à ANPD (Autoridade Nacional de Proteção de Dados).',
  ]
  const contact =
    `Controlador e encarregado: ${CONTACT_NAME} · ${CONTACT_EMAIL}. ` +
    'Pedidos são respondidos em até 15 dias.'

  font(doc, 'normal', 9.5, COLOR.navy)
  const rightLines = rights.map((item) => doc.splitTextToSize(item, textWidth - 4))
  font(doc, 'normal', 8.5, COLOR.muted)
  const contactLines = doc.splitTextToSize(contact, textWidth)
  const height =
    padding +
    6 +
    rightLines.reduce((sum, lines) => sum + lines.length * LINE + 1, 0) +
    3 +
    contactLines.length * 4.2 +
    padding

  ensureSpace(ctx, height + 4)
  ctx.y += 4
  const top = ctx.y

  setFill(doc, COLOR.blueSoft)
  doc.roundedRect(MARGIN.left, top, CONTENT_WIDTH, height, 3, 3, 'F')
  setFill(doc, COLOR.blue)
  doc.rect(MARGIN.left, top + 3, 1.4, height - 6, 'F')

  const x = MARGIN.left + padding + 3
  let y = top + padding + 3
  font(doc, 'bold', 11, COLOR.navy)
  doc.text('Seus direitos sobre estes dados', x, y)
  y += 6

  rightLines.forEach((lines) => {
    setFill(doc, COLOR.blue)
    doc.circle(x + 1, y - 1.3, 0.75, 'F')
    font(doc, 'normal', 9.5, COLOR.navy)
    doc.text(lines, x + 4, y)
    y += lines.length * LINE + 1
  })

  y += 2
  font(doc, 'normal', 8.5, COLOR.muted)
  doc.text(contactLines, x, y)

  ctx.y = top + height + 2
}

function drawFooters(doc) {
  const total = doc.getNumberOfPages()

  for (let page = 1; page <= total; page += 1) {
    doc.setPage(page)
    const footerY = PAGE.height - 13

    setDraw(doc, COLOR.border)
    doc.setLineWidth(0.2)
    doc.line(MARGIN.left, footerY, CONTENT_RIGHT, footerY)

    font(doc, 'normal', 7.5, COLOR.faint)
    doc.text(
      'Documento gerado a pedido do titular, conforme a LGPD. Contém dados pessoais: guarde com cuidado.',
      MARGIN.left,
      footerY + 5,
    )
    doc.text(`Página ${page} de ${total}`, CONTENT_RIGHT, footerY + 5, {
      align: 'right',
    })
  }
}

/** Loads the brand icon from /public as a PNG data URL for jsPDF. Resolves to
 * null (never rejects) so a missing/blocked image just omits the logo. */
function loadLogoDataUrl() {
  return new Promise((resolve) => {
    try {
      const img = new Image()

      img.onload = () => {
        try {
          // The logo prints at 9mm, so 128px is plenty and keeps the PDF small.
          const size = 128
          const canvas = document.createElement('canvas')
          canvas.width = size
          canvas.height = size
          const context = canvas.getContext('2d')
          context.drawImage(img, 0, 0, size, size)
          resolve(canvas.toDataURL('image/png'))
        } catch {
          resolve(null)
        }
      }
      img.onerror = () => resolve(null)
      img.src = `${import.meta.env.BASE_URL}brand/produzzy-icon.png`
    } catch {
      resolve(null)
    }
  })
}

/** Renders the raw export payload into a formatted jsPDF document. */
function buildDataExportPdf(data, logo = null) {
  const account = data?.account ?? {}
  const memberships = data?.workspace_memberships ?? []
  const owned = data?.owned_workspaces ?? []
  const summaries = data?.workspace_summaries ?? []
  const activity = data?.activity ?? []

  const doc = new jsPDF({ format: 'a4', unit: 'mm' })
  const ctx = { doc, ownerName: String(account.name ?? ''), y: MARGIN.top }

  drawCover(ctx, data, logo)
  drawProfileCard(ctx, account)

  const sum = (key) => summaries.reduce((total, item) => total + (Number(item[key]) || 0), 0)
  drawStatTiles(ctx, [
    { label: 'Workspaces', value: memberships.length },
    { label: 'Produtos', value: sum('products') },
    { label: 'Movimentações', value: sum('movements') },
    { label: 'Ações suas', value: activity.length },
  ])

  sectionTitle(ctx, 'Dados da conta')
  drawFieldGrid(ctx, [
    { label: 'Nome', value: account.name },
    { label: 'E-mail', value: account.email },
    {
      label: 'Forma de login',
      value: account.auth_provider === 'google' ? 'Google' : 'E-mail e senha',
    },
    { label: 'E-mail confirmado', value: account.email_verified ? 'Sim' : 'Não' },
    {
      label: 'E-mail de recuperação',
      value: account.recovery_email
        ? `${account.recovery_email} (${
            account.recovery_email_verified ? 'confirmado' : 'pendente'
          })`
        : 'Não configurado',
    },
    { label: 'Foto de perfil', value: account.avatar_url ? 'Sim' : 'Não' },
    { label: 'Conta criada em', value: formatDate(account.created_at) },
    { label: 'Última atualização', value: formatDate(account.updated_at) },
  ])

  sectionTitle(
    ctx,
    'Seus workspaces',
    'Onde você participa, com qual permissão e o que cada workspace guarda hoje.',
  )
  if (memberships.length) {
    const ownedByName = new Map(owned.map((item) => [item.name, item]))
    const rows = memberships.map((item, index) => {
      const summary = summaries[index] ?? {}
      const ownedWorkspace = item.role === 'owner' ? ownedByName.get(item.workspace) : null
      return {
        categories: formatNumber(summary.categories),
        movements: formatNumber(summary.movements),
        products: formatNumber(summary.products),
        role: { sub: item.title || null, text: roleLabel(item.role) },
        workspace: {
          sub: ownedWorkspace ? `Criado em ${formatDate(ownedWorkspace.created_at)}` : null,
          text: item.workspace ?? '—',
        },
      }
    })
    drawTable(
      ctx,
      [
        { bold: true, key: 'workspace', title: 'Workspace', width: 0.34 },
        { key: 'role', title: 'Permissão', width: 0.21 },
        { align: 'right', key: 'products', title: 'Produtos', width: 0.14 },
        { align: 'right', key: 'categories', title: 'Categorias', width: 0.15 },
        { align: 'right', key: 'movements', title: 'Mov.', width: 0.16 },
      ],
      rows,
    )
  } else {
    emptyState(ctx, 'Você ainda não participa de nenhum workspace.')
  }

  sectionTitle(
    ctx,
    'Seu histórico de atividade',
    'As ações feitas pela sua conta, da mais recente para a mais antiga.',
  )
  if (activity.length) {
    drawTable(
      ctx,
      [
        { key: 'at', title: 'Data e hora', width: 0.24 },
        { key: 'action', title: 'Ação', width: 0.46 },
        { key: 'workspace', title: 'Workspace', width: 0.3 },
      ],
      activity.map((item) => ({
        action: humanizeAuditAction(item.action),
        at: formatDateTime(item.at),
        workspace: item.workspace ?? '—',
      })),
    )
    note(ctx, 'Mostramos até as 200 ações mais recentes.')
  } else {
    emptyState(ctx, 'Nenhuma atividade registrada.')
  }

  drawRightsBox(ctx)
  drawFooters(doc)

  return doc
}

/** Builds the PDF (with the brand logo when available) and triggers download. */
export async function downloadDataExportPdf(
  data,
  filename = 'meus-dados-produzzy.pdf',
) {
  const logo = await loadLogoDataUrl()
  const doc = buildDataExportPdf(data, logo)
  doc.save(filename)
}

export default buildDataExportPdf

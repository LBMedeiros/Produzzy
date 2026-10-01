import { jsPDF } from 'jspdf'

import { humanizeAuditAction } from './formatters'

// Builds the "Baixar meus dados" (LGPD) document as a clean, formal PDF.
// Everything here is plain layout math (A4, millimetres) so the file reads well
// for a non-technical user and prints nicely.

const PAGE = { height: 297, width: 210 }
const MARGIN = { bottom: 20, left: 18, right: 18, top: 18 }
const CONTENT_WIDTH = PAGE.width - MARGIN.left - MARGIN.right
const CONTENT_RIGHT = PAGE.width - MARGIN.right
const HEADER_HEIGHT = 30
const LOGO_SIZE = 14 // mm (the brand icon is square)

const COLOR = {
  blue: [37, 99, 235],
  line: [226, 232, 240],
  muted: [100, 116, 139],
  navy: [15, 23, 42],
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

function setColor(doc, [r, g, b]) {
  doc.setTextColor(r, g, b)
}

function setDraw(doc, [r, g, b]) {
  doc.setDrawColor(r, g, b)
}

function setFill(doc, [r, g, b]) {
  doc.setFillColor(r, g, b)
}

// Reserve vertical space; start a new page when the current one is full.
function ensureSpace(ctx, needed) {
  if (ctx.y + needed > PAGE.height - MARGIN.bottom) {
    ctx.doc.addPage()
    ctx.y = MARGIN.top
  }
}

function drawHeader(doc, generatedAt, logo) {
  setFill(doc, COLOR.navy)
  doc.rect(0, 0, PAGE.width, HEADER_HEIGHT, 'F')

  let textX = MARGIN.left

  if (logo) {
    const logoY = (HEADER_HEIGHT - LOGO_SIZE) / 2
    try {
      doc.addImage(
        logo,
        'PNG',
        MARGIN.left,
        logoY,
        LOGO_SIZE,
        LOGO_SIZE,
        undefined,
        'FAST',
      )
      textX = MARGIN.left + LOGO_SIZE + 5
    } catch {
      // If the logo can't be drawn, fall back to the text-only header.
      textX = MARGIN.left
    }
  }

  setColor(doc, COLOR.white)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(20)
  doc.text('Produzzy', textX, 15)

  setColor(doc, COLOR.line)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.text('Relatório de dados pessoais', textX, 22)

  doc.setFontSize(9)
  doc.text(`Gerado em ${formatDate(generatedAt)}`, CONTENT_RIGHT, 22, {
    align: 'right',
  })
}

/** Loads the brand icon from /public as a PNG data URL for jsPDF. Resolves to
 * null (never rejects) so a missing/blocked image just omits the logo. */
function loadLogoDataUrl() {
  return new Promise((resolve) => {
    try {
      const img = new Image()

      img.onload = () => {
        try {
          // The logo only prints at 14mm, so 128px is plenty — downscaling
          // keeps the embedded image (and the PDF) small.
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

function drawFooters(doc) {
  const total = doc.getNumberOfPages()

  for (let page = 1; page <= total; page += 1) {
    doc.setPage(page)
    const footerY = PAGE.height - 12

    setDraw(doc, COLOR.line)
    doc.setLineWidth(0.2)
    doc.line(MARGIN.left, footerY, CONTENT_RIGHT, footerY)

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    setColor(doc, COLOR.muted)
    doc.text(
      'Exportado pelo Produzzy conforme a LGPD · Dúvidas: lucasmedbasil@gmail.com',
      MARGIN.left,
      footerY + 5,
    )
    doc.text(`Página ${page} de ${total}`, CONTENT_RIGHT, footerY + 5, {
      align: 'right',
    })
  }
}

function sectionTitle(ctx, text) {
  const { doc } = ctx
  ensureSpace(ctx, 16)
  ctx.y += 4

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  setColor(doc, COLOR.blue)
  doc.text(text.toUpperCase(), MARGIN.left, ctx.y)

  ctx.y += 2.5
  setDraw(doc, COLOR.line)
  doc.setLineWidth(0.3)
  doc.line(MARGIN.left, ctx.y, CONTENT_RIGHT, ctx.y)
  ctx.y += 6
}

// Two-column "label  value" row with wrapping values (used for the account box).
function field(ctx, label, value) {
  const { doc } = ctx
  const labelX = MARGIN.left
  const valueX = MARGIN.left + 42
  const valueWidth = CONTENT_RIGHT - valueX

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  const valueLines = doc.splitTextToSize(String(value ?? '—'), valueWidth)
  const rowHeight = Math.max(valueLines.length * 5, 5)

  ensureSpace(ctx, rowHeight + 1)

  setColor(doc, COLOR.muted)
  doc.text(label, labelX, ctx.y)

  setColor(doc, COLOR.navy)
  doc.text(valueLines, valueX, ctx.y)

  ctx.y += rowHeight + 1
}

function bulletLines(ctx, primary, secondary) {
  const { doc } = ctx
  const textX = MARGIN.left + 5
  const textWidth = CONTENT_RIGHT - textX

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  const primaryLines = doc.splitTextToSize(primary, textWidth)
  const secondaryLines = secondary
    ? doc.splitTextToSize(secondary, textWidth)
    : []
  const blockHeight = (primaryLines.length + secondaryLines.length) * 5

  ensureSpace(ctx, blockHeight + 1)

  const bulletY = ctx.y - 1.4
  setFill(doc, COLOR.blue)
  doc.circle(MARGIN.left + 1.4, bulletY, 0.7, 'F')

  setColor(doc, COLOR.navy)
  doc.text(primaryLines, textX, ctx.y)
  ctx.y += primaryLines.length * 5

  if (secondaryLines.length) {
    setColor(doc, COLOR.muted)
    doc.text(secondaryLines, textX, ctx.y)
    ctx.y += secondaryLines.length * 5
  }

  ctx.y += 1.5
}

function emptyRow(ctx, text) {
  const { doc } = ctx
  ensureSpace(ctx, 6)
  doc.setFont('helvetica', 'italic')
  doc.setFontSize(10)
  setColor(doc, COLOR.muted)
  doc.text(text, MARGIN.left + 5, ctx.y)
  ctx.y += 6
}

function note(ctx, text) {
  const { doc } = ctx
  ensureSpace(ctx, 6)
  ctx.y += 1
  doc.setFont('helvetica', 'italic')
  doc.setFontSize(9)
  setColor(doc, COLOR.muted)
  const lines = doc.splitTextToSize(text, CONTENT_WIDTH)
  doc.text(lines, MARGIN.left, ctx.y)
  ctx.y += lines.length * 4.5
}

/** Renders the raw export payload into a formatted jsPDF document. */
function buildDataExportPdf(data, logo = null) {
  const account = data?.account ?? {}
  const memberships = data?.workspace_memberships ?? []
  const owned = data?.owned_workspaces ?? []
  const summaries = data?.workspace_summaries ?? []
  const activity = data?.activity ?? []

  const doc = new jsPDF({ format: 'a4', unit: 'mm' })
  drawHeader(doc, data?.exported_at, logo)

  const ctx = { doc, y: HEADER_HEIGHT + 12 }

  sectionTitle(ctx, 'Conta')
  field(ctx, 'Nome', account.name ?? '—')
  field(ctx, 'E-mail', account.email ?? '—')
  field(
    ctx,
    'Forma de login',
    account.auth_provider === 'google' ? 'Google' : 'E-mail e senha',
  )
  field(ctx, 'E-mail confirmado', account.email_verified ? 'Sim' : 'Não')
  field(
    ctx,
    'E-mail de recuperação',
    account.recovery_email
      ? `${account.recovery_email} (${
          account.recovery_email_verified ? 'confirmado' : 'pendente'
        })`
      : 'Não configurado',
  )
  field(ctx, 'Conta criada em', formatDate(account.created_at))

  sectionTitle(ctx, 'Workspaces que você participa')
  if (memberships.length) {
    memberships.forEach((item) => {
      const title = item.title ? ` · Cargo: ${item.title}` : ''
      bulletLines(
        ctx,
        `${item.workspace ?? '—'} — Permissão: ${roleLabel(item.role)}${title}`,
      )
    })
  } else {
    emptyRow(ctx, '(nenhum)')
  }

  sectionTitle(ctx, 'Workspaces que você é dono')
  if (owned.length) {
    owned.forEach((item) => {
      bulletLines(
        ctx,
        `${item.name ?? '—'} — criado em ${formatDate(item.created_at)}`,
      )
    })
  } else {
    emptyRow(ctx, '(nenhum)')
  }

  sectionTitle(ctx, 'Resumo dos seus workspaces')
  if (summaries.length) {
    summaries.forEach((item) => {
      bulletLines(
        ctx,
        `${item.workspace ?? '—'} (${roleLabel(item.role)})`,
        `${item.products} produto(s), ${item.categories} categoria(s), ` +
          `${item.movements} movimentação(ões)`,
      )
    })
  } else {
    emptyRow(ctx, '(nenhum)')
  }

  sectionTitle(ctx, 'Seu histórico de atividade')
  if (activity.length) {
    activity.forEach((item) => {
      const where = item.workspace ? ` (${item.workspace})` : ''
      bulletLines(
        ctx,
        `${formatDateTime(item.at)} · ${humanizeAuditAction(item.action)}${where}`,
      )
    })
    note(ctx, 'Mostramos as ações mais recentes; registros antigos podem não aparecer.')
  } else {
    emptyRow(ctx, '(nenhuma atividade registrada)')
  }

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

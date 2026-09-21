import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Button from '../ui/Button'

// On-screen crop viewport (CSS px) and the exported square size (px).
const VIEWPORT = 300
const OUTPUT = 512
const MAX_ZOOM = 3
const DPR = Math.min(typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1, 2)

// Loads the picked file as a drawable source with EXIF orientation already
// applied, so what the user frames is exactly what gets uploaded. Falls back
// to an <img> on browsers without createImageBitmap options support.
async function loadImageSource(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
      return { source: bitmap, width: bitmap.width, height: bitmap.height, isBitmap: true }
    } catch {
      // fall through to the <img> path
    }
  }

  const url = URL.createObjectURL(file)

  try {
    const image = await new Promise((resolve, reject) => {
      const element = new Image()
      element.onload = () => resolve(element)
      element.onerror = () => reject(new Error('load-error'))
      element.src = url
    })

    return {
      source: image,
      width: image.naturalWidth,
      height: image.naturalHeight,
      isBitmap: false,
    }
  } finally {
    URL.revokeObjectURL(url)
  }
}

function AvatarCropModal({ file, isUploading = false, error = '', onCancel, onConfirm }) {
  const canvasRef = useRef(null)
  const dragRef = useRef(null)
  const offsetRef = useRef({ x: 0, y: 0 })
  const scaleRef = useRef(1)

  const [media, setMedia] = useState(null) // { source, width, height }
  const [baseScale, setBaseScale] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  // Constrain the pan so the image always covers the whole viewport (no gaps).
  const clampOffset = useCallback((next, scale, width, height) => {
    const displayedWidth = width * scale
    const displayedHeight = height * scale

    return {
      x: Math.min(0, Math.max(VIEWPORT - displayedWidth, next.x)),
      y: Math.min(0, Math.max(VIEWPORT - displayedHeight, next.y)),
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    let loadedBitmap = null

    // isLoading/loadError already start in their pending state on mount (the
    // modal remounts per open), so we only settle them in the callbacks below
    // — avoids a synchronous setState inside the effect body.
    loadImageSource(file)
      .then((result) => {
        if (!isMounted) {
          if (result.isBitmap) result.source.close()
          return
        }

        if (result.isBitmap) loadedBitmap = result.source

        const nextBaseScale = VIEWPORT / Math.min(result.width, result.height)
        const displayedWidth = result.width * nextBaseScale
        const displayedHeight = result.height * nextBaseScale
        const centered = {
          x: (VIEWPORT - displayedWidth) / 2,
          y: (VIEWPORT - displayedHeight) / 2,
        }

        setMedia({ source: result.source, width: result.width, height: result.height })
        setBaseScale(nextBaseScale)
        setZoom(1)
        setOffset(centered)
        offsetRef.current = centered
        scaleRef.current = nextBaseScale
        setIsLoading(false)
      })
      .catch(() => {
        if (isMounted) {
          setLoadError('Não foi possível abrir esta imagem.')
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
      if (loadedBitmap) loadedBitmap.close()
    }
  }, [file])

  useEffect(() => {
    offsetRef.current = offset
  }, [offset])

  useEffect(() => {
    scaleRef.current = baseScale * zoom
  }, [baseScale, zoom])

  // Lock background scroll while the editor is open.
  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  // Paint the live preview. What is drawn here matches the exported crop 1:1.
  useEffect(() => {
    const canvas = canvasRef.current

    if (!canvas || !media) {
      return
    }

    const context = canvas.getContext('2d')
    const scale = baseScale * zoom

    context.setTransform(DPR, 0, 0, DPR, 0, 0)
    context.clearRect(0, 0, VIEWPORT, VIEWPORT)
    context.imageSmoothingQuality = 'high'
    context.drawImage(
      media.source,
      offset.x,
      offset.y,
      media.width * scale,
      media.height * scale,
    )
  }, [media, baseScale, zoom, offset])

  const handleZoomChange = useCallback(
    (nextZoom) => {
      if (!media) {
        return
      }

      const scaleOld = baseScale * zoom
      const scaleNew = baseScale * nextZoom
      // Keep the point under the viewport centre fixed while zooming.
      const centerX = (VIEWPORT / 2 - offsetRef.current.x) / scaleOld
      const centerY = (VIEWPORT / 2 - offsetRef.current.y) / scaleOld
      const next = clampOffset(
        {
          x: VIEWPORT / 2 - centerX * scaleNew,
          y: VIEWPORT / 2 - centerY * scaleNew,
        },
        scaleNew,
        media.width,
        media.height,
      )

      setZoom(nextZoom)
      setOffset(next)
    },
    [baseScale, clampOffset, media, zoom],
  )

  function handlePointerDown(event) {
    if (isUploading || !media) {
      return
    }

    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      offsetX: offsetRef.current.x,
      offsetY: offsetRef.current.y,
    }
  }

  function handlePointerMove(event) {
    const drag = dragRef.current

    if (!drag || !media) {
      return
    }

    const next = clampOffset(
      {
        x: drag.offsetX + (event.clientX - drag.pointerX),
        y: drag.offsetY + (event.clientY - drag.pointerY),
      },
      scaleRef.current,
      media.width,
      media.height,
    )

    setOffset(next)
  }

  function handlePointerUp(event) {
    dragRef.current = null

    try {
      event.currentTarget.releasePointerCapture(event.pointerId)
    } catch {
      // pointer was already released
    }
  }

  function handleWheel(event) {
    if (isUploading || !media) {
      return
    }

    event.preventDefault()
    const step = event.deltaY < 0 ? 0.1 : -0.1
    const nextZoom = Math.min(MAX_ZOOM, Math.max(1, Number((zoom + step).toFixed(2))))
    handleZoomChange(nextZoom)
  }

  async function handleConfirm() {
    if (!media || isUploading) {
      return
    }

    const scale = baseScale * zoom
    const sourceSize = VIEWPORT / scale
    const sourceX = -offset.x / scale
    const sourceY = -offset.y / scale

    const canvas = document.createElement('canvas')
    canvas.width = OUTPUT
    canvas.height = OUTPUT
    const context = canvas.getContext('2d')
    context.imageSmoothingQuality = 'high'
    context.drawImage(
      media.source,
      sourceX,
      sourceY,
      sourceSize,
      sourceSize,
      0,
      0,
      OUTPUT,
      OUTPUT,
    )

    const blob = await new Promise((resolve) =>
      canvas.toBlob((result) => resolve(result), 'image/webp', 0.9),
    )

    if (blob) {
      onConfirm(blob)
    }
  }

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape' && !isUploading) {
        onCancel()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isUploading, onCancel])

  const modal = (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-labelledby="avatar-crop-title"
        aria-modal="true"
        className="workspace-modal avatar-crop-modal"
        role="dialog"
      >
        <div className="workspace-modal__header">
          <div>
            <span>Foto de perfil</span>
            <h2 id="avatar-crop-title">Enquadrar foto</h2>
          </div>
          <button
            aria-label="Fechar editor"
            className="icon-button"
            disabled={isUploading}
            onClick={onCancel}
            type="button"
          >
            x
          </button>
        </div>

        <div className="avatar-crop">
          <p className="avatar-crop__hint">
            Arraste para posicionar e use o controle abaixo para aproximar.
          </p>

          <div
            className="avatar-crop__stage"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onWheel={handleWheel}
            style={{ width: VIEWPORT, height: VIEWPORT }}
          >
            <canvas
              className="avatar-crop__canvas"
              height={VIEWPORT * DPR}
              ref={canvasRef}
              style={{ width: VIEWPORT, height: VIEWPORT }}
              width={VIEWPORT * DPR}
            />
            <div className="avatar-crop__ring" aria-hidden="true" />
            {isLoading ? (
              <div className="avatar-crop__loading">Carregando imagem...</div>
            ) : null}
          </div>

          <label className="avatar-crop__zoom">
            <span>Zoom</span>
            <input
              disabled={isUploading || isLoading || Boolean(loadError)}
              max={MAX_ZOOM}
              min={1}
              onChange={(event) => handleZoomChange(Number(event.target.value))}
              step={0.01}
              type="range"
              value={zoom}
            />
          </label>

          {loadError ? <p className="form-error">{loadError}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}

          <div className="workspace-form__actions">
            <Button
              disabled={isUploading || isLoading || Boolean(loadError)}
              onClick={handleConfirm}
              type="button"
            >
              {isUploading ? 'Salvando...' : 'Salvar foto'}
            </Button>
            <Button
              disabled={isUploading}
              onClick={onCancel}
              type="button"
              variant="secondary"
            >
              Cancelar
            </Button>
          </div>
        </div>
      </section>
    </div>
  )

  if (typeof document === 'undefined') {
    return null
  }

  return createPortal(modal, document.body)
}

export default AvatarCropModal

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { BrowserMultiFormatReader } from '@zxing/browser'
import { BarcodeFormat, DecodeHintType } from '@zxing/library'
import Button from '../ui/Button'

// `both` is the primary entry point: one camera pass reads either code the app
// generates. The single-format modes stay available for a focused read.
const MODE_CONFIG = {
  both: {
    eyebrow: 'Leitor',
    title: 'Escanear produto',
    hint: 'Aponte a câmera para o QR Code ou código de barras do produto.',
    formats: [BarcodeFormat.QR_CODE, BarcodeFormat.CODE_128],
  },
  qr: {
    eyebrow: 'Leitor',
    title: 'Ler QR Code',
    hint: 'Aponte a câmera para o QR Code do produto.',
    formats: [BarcodeFormat.QR_CODE],
  },
  barcode: {
    eyebrow: 'Leitor',
    title: 'Ler código de barras',
    hint: 'Aponte a câmera para o código de barras do produto.',
    formats: [BarcodeFormat.CODE_128],
  },
}

function buildHints(formats) {
  const hints = new Map()
  hints.set(DecodeHintType.POSSIBLE_FORMATS, formats)
  return hints
}

function describeCameraError(error) {
  const name = error?.name

  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Permita o acesso à câmera no navegador para usar o leitor.'
  }

  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'Nenhuma câmera disponível foi encontrada neste dispositivo.'
  }

  if (name === 'NotReadableError') {
    return 'A câmera está em uso por outro aplicativo. Feche-o e tente novamente.'
  }

  return 'Não foi possível iniciar a câmera. Tente novamente.'
}

/**
 * Full-screen camera reader. `onDetect(text)` is called with each decoded
 * value; it returns `null`/`undefined` to accept (the parent then closes this
 * modal) or a message string to reject and keep scanning (shown as a warning).
 */
function QrScannerModal({ mode = 'both', onDetect, onClose }) {
  const config = MODE_CONFIG[mode] ?? MODE_CONFIG.both
  const videoRef = useRef(null)
  const onDetectRef = useRef(onDetect)
  const acceptedRef = useRef(false)
  const [status, setStatus] = useState('starting')
  const [errorMessage, setErrorMessage] = useState('')
  const [warning, setWarning] = useState('')

  useEffect(() => {
    onDetectRef.current = onDetect
  }, [onDetect])

  useEffect(() => {
    let cancelled = false
    let stopped = false
    let controls = null
    const modeConfig = MODE_CONFIG[mode] ?? MODE_CONFIG.both
    const reader = new BrowserMultiFormatReader(buildHints(modeConfig.formats), {
      delayBetweenScanAttempts: 120,
    })

    const stop = () => {
      if (stopped) {
        return
      }

      stopped = true

      try {
        controls?.stop()
      } catch {
        // Stream already torn down.
      }
    }

    async function start() {
      try {
        controls = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: 'environment' } } },
          videoRef.current,
          (result) => {
            if (cancelled || acceptedRef.current || !result) {
              return
            }

            const message = onDetectRef.current?.(result.getText())

            if (message == null) {
              acceptedRef.current = true
              stop()
            } else {
              setWarning(message)
            }
          },
        )

        if (cancelled) {
          stop()
          return
        }

        setStatus('scanning')
      } catch (startError) {
        if (cancelled) {
          return
        }

        setStatus('error')
        setErrorMessage(describeCameraError(startError))
      }
    }

    start()

    return () => {
      cancelled = true
      stop()
    }
  }, [mode])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [onClose])

  const modal = (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-labelledby="qr-scanner-title"
        aria-modal="true"
        className="workspace-modal qr-scanner-modal"
        role="dialog"
      >
        <div className="workspace-modal__header">
          <div>
            <span>{config.eyebrow}</span>
            <h2 id="qr-scanner-title">{config.title}</h2>
          </div>
          <button
            aria-label="Fechar leitor"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>

        <div className="qr-scanner">
          {status === 'error' ? (
            <div className="qr-scanner__error">
              <strong>Não foi possível abrir a câmera</strong>
              <p>{errorMessage}</p>
            </div>
          ) : (
            <>
              <div className="qr-scanner__stage">
                <video
                  autoPlay
                  className="qr-scanner__video"
                  muted
                  playsInline
                  ref={videoRef}
                />
                <div className="qr-scanner__frame" aria-hidden="true" />
                {status === 'starting' ? (
                  <div className="qr-scanner__loading">Iniciando câmera...</div>
                ) : null}
              </div>
              <p
                className={`qr-scanner__hint ${
                  warning ? 'qr-scanner__hint--warn' : ''
                }`}
              >
                {warning || config.hint}
              </p>
            </>
          )}
        </div>

        <div className="workspace-form__actions">
          <Button onClick={onClose} type="button" variant="secondary">
            {status === 'error' ? 'Fechar' : 'Cancelar'}
          </Button>
        </div>
      </section>
    </div>
  )

  return createPortal(modal, document.body)
}

export default QrScannerModal

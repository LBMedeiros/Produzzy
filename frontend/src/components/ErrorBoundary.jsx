import { Component } from 'react'

/**
 * Catches render errors — most importantly a lazy page chunk that fails to
 * load (network blip after a deploy) — so the user sees a retry prompt
 * instead of a blank screen.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught an error', error, info)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <main className="loading-screen">
        <strong>Não foi possível carregar esta parte do app.</strong>
        <button type="button" onClick={this.handleReload}>
          Recarregar
        </button>
      </main>
    )
  }
}

export default ErrorBoundary

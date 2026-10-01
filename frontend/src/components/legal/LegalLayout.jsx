import { Link, useNavigate } from 'react-router-dom'
import BrandIcon from '../ui/BrandIcon'

/** Shared chrome for the public legal pages (Terms, Privacy). */
function LegalLayout({ title, updatedAt, children }) {
  const navigate = useNavigate()

  return (
    <main className="legal-page">
      <header className="legal-page__top">
        <Link to="/" className="legal-page__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </Link>
        <button
          type="button"
          className="legal-page__back"
          onClick={() => navigate(-1)}
        >
          Voltar
        </button>
      </header>

      <article className="legal-doc">
        <h1>{title}</h1>
        <p className="legal-doc__updated">Última atualização: {updatedAt}</p>
        {children}
      </article>

      <footer className="legal-page__footer">
        <Link to="/termos">Termos de Uso</Link>
        <span aria-hidden="true">·</span>
        <Link to="/privacidade">Política de Privacidade</Link>
      </footer>
    </main>
  )
}

export default LegalLayout

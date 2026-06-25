import Button from '../components/ui/Button'

function LoginPage({ onLogin }) {
  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="login-panel__brand">
          <div className="brand__mark">PZ</div>
          <strong>Produzzy</strong>
        </div>
        <div className="login-panel__copy">
          <h1>Controle seu estoque com clareza</h1>
          <p>
            Organize produtos, movimentações, QR Codes e etiquetas em um fluxo
            simples para equipes de estoque e produção.
          </p>
        </div>

        <form className="login-form" onSubmit={(event) => event.preventDefault()}>
          <label>
            Email
            <input type="email" placeholder="lucas@empresa.com" />
          </label>
          <label>
            Senha
            <input type="password" placeholder="Digite sua senha" />
          </label>
          <Button type="button" onClick={onLogin} className="login-form__submit">
            Entrar
          </Button>
        </form>

        <p className="login-panel__footer">
          Novo por aqui? <button type="button">Começar agora</button>
        </p>
      </section>

      <section className="login-hero" aria-label="Resumo visual do produto">
        <div className="login-hero__header">
          <span>Produção organizada</span>
          <strong>Bordados Medeiros</strong>
        </div>
        <div className="hero-metric hero-metric--wide">
          <span>Produtos monitorados</span>
          <strong>248</strong>
        </div>
        <div className="hero-metric">
          <span>Baixo estoque</span>
          <strong>18</strong>
        </div>
        <div className="hero-metric">
          <span>QR Code e etiquetas</span>
          <strong>1.2k</strong>
        </div>
        <div className="label-preview">
          <div className="qr-grid"></div>
          <div>
            <strong>Camiseta premium</strong>
            <span>ID 1024</span>
          </div>
        </div>
      </section>
    </main>
  )
}

export default LoginPage

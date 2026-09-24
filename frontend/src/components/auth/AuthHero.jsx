const benefits = [
  {
    description:
      'Cadastre produtos, categorias e acompanhe movimentações em tempo real.',
    icon: 'stock',
    title: 'Estoque organizado',
  },
  {
    description:
      'Identifique o que precisa comprar ou produzir antes de faltar.',
    icon: 'restock',
    title: 'Reposição inteligente',
  },
  {
    description:
      'Gere QR Codes, códigos de barras e etiquetas prontas para impressão.',
    icon: 'labels',
    title: 'Etiquetas prontas',
  },
]

function BenefitIcon({ type }) {
  if (type === 'stock') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="m4 7 8-4 8 4-8 4-8-4Z" />
        <path d="m4 7 8 4 8-4M4 12l8 4 8-4M4 17l8 4 8-4" />
      </svg>
    )
  }

  if (type === 'restock') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M20 7v5h-5" />
        <path d="M18.5 16a8 8 0 1 1 .8-8.1L20 12" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 5a2 2 0 0 1 2-2h8l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Z" />
      <path d="M14 3v6h6M8 14h8M8 17h5" />
    </svg>
  )
}

function AuthHero() {
  return (
    <section className="login-hero" aria-labelledby="login-hero-title">
      <div className="login-hero__content">
        <div className="login-hero__header">
          <span>Gestão simples, do cadastro à reposição</span>
          <h2 id="login-hero-title">
            Estoque, etiquetas e reposição no mesmo fluxo
          </h2>
          <p>
            Controle produtos, acompanhe o baixo estoque, gere QR Codes e
            códigos de barras e saiba quando precisa repor.
          </p>
        </div>

        <div className="login-benefits">
          {benefits.map((benefit) => (
            <article className="login-benefit" key={benefit.title}>
              <span className="login-benefit__icon">
                <BenefitIcon type={benefit.icon} />
              </span>
              <div>
                <h3>{benefit.title}</h3>
                <p>{benefit.description}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default AuthHero

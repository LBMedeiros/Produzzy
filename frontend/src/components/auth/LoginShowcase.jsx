import { Link } from 'react-router-dom'

// Decorative QR-like pattern for the sample label: three finder squares plus
// a fixed pseudo-random fill (deterministic, so it never changes on render).
const QR_SIZE = 21
const QR_CELLS = (() => {
  let seed = 7
  const random = () => {
    seed = (seed * 9301 + 49297) % 233280
    return seed / 233280
  }
  const finders = [
    [0, 0],
    [14, 0],
    [0, 14],
  ]
  const cells = []

  for (let y = 0; y < QR_SIZE; y += 1) {
    for (let x = 0; x < QR_SIZE; x += 1) {
      const finder = finders.find(
        ([fx, fy]) => x >= fx && x < fx + 7 && y >= fy && y < fy + 7,
      )
      let filled

      if (finder) {
        const dx = x - finder[0]
        const dy = y - finder[1]
        filled =
          dx === 0 ||
          dy === 0 ||
          dx === 6 ||
          dy === 6 ||
          (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4)
      } else {
        filled = random() > 0.5
      }

      cells.push(filled)
    }
  }

  return cells
})()

const STEPS = [
  {
    title: 'Cadastre e etiquete',
    text: 'Organize produtos por categoria e gere etiquetas com QR Code e código de barras prontas para imprimir.',
  },
  {
    title: 'Movimente pelo celular',
    text: 'Escaneie a etiqueta com a câmera e registre entradas e saídas na hora, com histórico de quem fez o quê.',
  },
  {
    title: 'Reponha antes de faltar',
    text: 'O sistema avisa o que está abaixo do mínimo e a equipe acompanha cada reposição até chegar ao estoque.',
  },
]

const HIGHLIGHTS = [
  'Quadro de reposição com responsáveis e etapas',
  'Alertas de baixo estoque e produtos zerados',
  'Equipe com papéis e permissões por workspace',
  'Funciona no computador e no celular',
]

const SEGMENTS = [
  'Ferragens e peças',
  'Embalagens',
  'Alimentos e bebidas',
  'EPI e limpeza',
  'Material de escritório',
  'Insumos de produção',
  'Farmácia e saúde',
]

function delay(ms) {
  return { '--delay': `${ms}ms` }
}

function LoginShowcase({ onCreateAccount, sectionRef }) {
  return (
    <>
      <section className="auth-section" id="conheca" ref={sectionRef}>
        <p className="auth-eyebrow" data-reveal>
          Para que serve
        </p>
        <h2 data-reveal style={delay(120)}>
          Seu estoque em ordem, <em>do cadastro à reposição</em>
        </h2>
        <p className="auth-lead" data-reveal style={delay(240)}>
          O Produzzy reúne produtos, movimentações e reposição da equipe num só
          lugar, para ninguém ser pego de surpresa com algo em falta.
        </p>
        <ol className="auth-steps">
          {STEPS.map((step, index) => (
            <li
              className="auth-step"
              data-reveal
              key={step.title}
              style={delay(330 + index * 180)}
            >
              <span className="auth-step__number">{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="auth-section auth-section--split">
        <div data-reveal>
          <p className="auth-eyebrow">Como é por dentro</p>
          <h2>
            Tudo que precisa de atenção, <em>numa olhada</em>
          </h2>
          <ul className="auth-highlights">
            {HIGHLIGHTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="auth-preview" aria-hidden="true">
          <div className="auth-window auth-window--board" data-reveal style={delay(180)}>
            <div className="auth-window__bar">
              <i />
              <i />
              <i />
            </div>
            <div className="auth-board">
              <div className="auth-board__column">
                <h4>
                  Necessário repor <b>12</b>
                </h4>
                <div className="auth-mini">
                  <strong>Caixa de papelão 40×30</strong>
                  <span>18 de 100 un.</span>
                  <div className="auth-progress">
                    <i style={{ width: '18%' }} />
                  </div>
                </div>
                <div className="auth-mini">
                  <strong>Luva nitrílica M</strong>
                  <span>6 de 20 cx.</span>
                  <div className="auth-progress">
                    <i style={{ width: '30%' }} />
                  </div>
                </div>
              </div>
              <div className="auth-board__column">
                <h4>
                  Em andamento <b>3</b>
                </h4>
                <div className="auth-mini">
                  <strong>Toner 85A</strong>
                  <span>Ana · compra</span>
                </div>
                <div className="auth-mini">
                  <strong>Etiqueta térmica</strong>
                  <span>Rafael · compra</span>
                </div>
              </div>
              <div className="auth-board__column">
                <h4>
                  Pronto <b>2</b>
                </h4>
                <div className="auth-mini">
                  <strong>Fita adesiva 48 mm</strong>
                  <span className="auth-pill auth-pill--ok">Estocar</span>
                </div>
              </div>
            </div>
          </div>

          <div className="auth-window auth-window--product" data-reveal style={delay(400)}>
            <span className="auth-pill auth-pill--warn">Baixo estoque</span>
            <h3>Café em grãos 1 kg</h3>
            <small>Alimentos · Copa</small>
            <div className="auth-product__numbers">
              <div>
                <span>Atual</span>
                <b>8</b>
              </div>
              <div>
                <span>Mínimo</span>
                <b>30</b>
              </div>
              <div>
                <span>Repor</span>
                <b>22</b>
              </div>
            </div>
            <span className="auth-product__button">Repor</span>
          </div>

          <div
            className="auth-window auth-window--label"
            data-reveal
            data-reveal-rotate="-4deg"
            style={delay(630)}
          >
            <b>Parafuso sextavado M8</b>
            <small>Ferragens · ID 214</small>
            <div className="auth-qr">
              {QR_CELLS.map((filled, index) => (
                <i className={filled ? 'is-filled' : ''} key={index} />
              ))}
            </div>
            <small className="auth-qr__caption">Escaneie para movimentar</small>
          </div>
        </div>
      </section>

      <section className="auth-section auth-section--center">
        <p className="auth-eyebrow" data-reveal>
          Para qualquer estoque
        </p>
        <h2 data-reveal style={delay(120)}>
          Feito para o seu tipo de negócio
        </h2>
        <ul className="auth-segments">
          {SEGMENTS.map((segment, index) => (
            <li data-reveal key={segment} style={delay(285 + index * 105)}>
              {segment}
            </li>
          ))}
        </ul>
        <button
          className="auth-cta"
          data-reveal
          onClick={onCreateAccount}
          style={delay(1050)}
          type="button"
        >
          Criar minha conta
        </button>
      </section>

      <footer className="auth-footer">
        Produzzy · <Link to="/termos">Termos de Uso</Link> ·{' '}
        <Link to="/privacidade">Política de Privacidade</Link>
      </footer>
    </>
  )
}

export default LoginShowcase

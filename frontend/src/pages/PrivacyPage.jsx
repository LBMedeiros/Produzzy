import LegalLayout from '../components/legal/LegalLayout'

const UPDATED_AT = '30 de setembro de 2026'
const CONTACT_EMAIL = 'lucasmedbasil@gmail.com'

function PrivacyPage() {
  return (
    <LegalLayout title="Política de Privacidade" updatedAt={UPDATED_AT}>
      <p>
        Esta Política explica como o <strong>Produzzy</strong> coleta, usa e
        protege seus dados pessoais, em conformidade com a Lei Geral de Proteção
        de Dados (Lei nº 13.709/2018 — LGPD). Ao usar o serviço, você entende as
        práticas descritas aqui.
      </p>

      <h2>1. Quem é o controlador</h2>
      <p>
        O responsável pelo tratamento dos dados é o Produzzy. Para qualquer
        assunto relacionado a privacidade ou ao exercício dos seus direitos,
        entre em contato pelo e-mail{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>

      <h2>2. Dados que coletamos</h2>
      <ul>
        <li>
          <strong>Dados de cadastro:</strong> nome, e-mail e senha (armazenada de
          forma criptografada/hash — nunca em texto puro). Opcionalmente, foto de
          perfil e um e-mail de recuperação.
        </li>
        <li>
          <strong>Login com Google (opcional):</strong> se você entrar com o
          Google, recebemos seu identificador, e-mail, nome e foto da conta
          Google, apenas para autenticar e criar/vincular sua conta.
        </li>
        <li>
          <strong>Dados que você insere:</strong> workspaces, produtos,
          categorias, movimentações de estoque e demais informações operacionais
          cadastradas por você ou pela sua equipe.
        </li>
        <li>
          <strong>Dados de uso:</strong> registros técnicos como data/hora de
          acesso e ações realizadas (log de auditoria), usados para segurança e
          funcionamento do serviço.
        </li>
      </ul>

      <h2>3. Como usamos os dados</h2>
      <ul>
        <li>autenticar seu acesso e manter sua conta e workspaces;</li>
        <li>operar as funcionalidades (estoque, etiquetas, reposição, equipe);</li>
        <li>
          enviar e-mails transacionais essenciais (confirmação de e-mail,
          redefinição de senha, convites);
        </li>
        <li>garantir segurança, prevenir fraudes e cumprir obrigações legais.</li>
      </ul>
      <p>Não vendemos seus dados e não enviamos propaganda sem seu consentimento.</p>

      <h2>4. Bases legais (LGPD)</h2>
      <p>
        Tratamos seus dados com base na <strong>execução do contrato</strong>
        (prestar o serviço que você contratou), no <strong>cumprimento de
        obrigação legal</strong>, no <strong>legítimo interesse</strong> (segurança
        e melhoria do serviço) e no <strong>consentimento</strong>, quando
        aplicável.
      </p>

      <h2>5. Compartilhamento com terceiros</h2>
      <p>
        Compartilhamos dados apenas com provedores que viabilizam o serviço, e
        somente no necessário:
      </p>
      <ul>
        <li><strong>Hospedagem da aplicação</strong> (ex.: Render);</li>
        <li><strong>Banco de dados</strong> (ex.: Neon / PostgreSQL);</li>
        <li><strong>Armazenamento de imagens</strong> para as fotos de perfil (ex.: Cloudinary);</li>
        <li><strong>Envio de e-mail</strong> e <strong>login com Google</strong>, quando usados.</li>
      </ul>
      <p>Esses provedores tratam os dados conforme nossas instruções e suas próprias políticas.</p>

      <h2>6. Cookies e armazenamento local</h2>
      <p>
        Usamos o armazenamento do navegador (como o token de sessão) para manter
        você conectado e lembrar preferências (por exemplo, tema claro/escuro).
        Não usamos cookies de rastreamento publicitário.
      </p>

      <h2>7. Transferência internacional</h2>
      <p>
        Alguns provedores podem armazenar dados em servidores fora do Brasil
        (por exemplo, nos Estados Unidos). Nesses casos, buscamos garantias
        adequadas de proteção, conforme a LGPD.
      </p>

      <h2>8. Segurança</h2>
      <p>
        Adotamos medidas como criptografia de senha, isolamento de dados entre
        workspaces, controle de acesso por papéis, limitação de tentativas de
        login e tráfego por HTTPS. Nenhum sistema é 100% imune, mas trabalhamos
        para proteger suas informações.
      </p>

      <h2>9. Retenção</h2>
      <p>
        Mantemos seus dados enquanto sua conta estiver ativa. Ao excluir a conta,
        seus dados pessoais são anonimizados ou removidos; alguns registros podem
        ser mantidos de forma anonimizada quando necessário para integridade,
        segurança ou cumprimento de obrigações legais.
      </p>

      <h2>10. Seus direitos</h2>
      <p>Como titular dos dados, você pode, a qualquer momento:</p>
      <ul>
        <li><strong>Acessar</strong> e <strong>corrigir</strong> seus dados em Configurações;</li>
        <li>
          <strong>Exportar</strong> seus dados (portabilidade) em{' '}
          <strong>Configurações → Privacidade e dados → Baixar meus dados</strong>;
        </li>
        <li>
          <strong>Excluir</strong> sua conta em{' '}
          <strong>Configurações → Privacidade e dados → Excluir minha conta</strong>
          {' '}(seus dados pessoais são anonimizados/removidos);
        </li>
        <li>revogar consentimentos e obter informações sobre o tratamento.</li>
      </ul>
      <p>
        Também é possível exercer esses direitos pelo e-mail{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>

      <h2>11. Crianças e adolescentes</h2>
      <p>
        O serviço não é destinado a menores sem o consentimento e a supervisão
        de um responsável legal.
      </p>

      <h2>12. Alterações nesta Política</h2>
      <p>
        Podemos atualizar esta Política periodicamente. Mudanças relevantes serão
        comunicadas pela plataforma ou por e-mail, indicando a nova data de
        atualização.
      </p>

      <h2>13. Encarregado (DPO) e contato</h2>
      <p>
        Para dúvidas, solicitações ou reclamações sobre privacidade, fale com o
        nosso encarregado pelo e-mail{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>
    </LegalLayout>
  )
}

export default PrivacyPage

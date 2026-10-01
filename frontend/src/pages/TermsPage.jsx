import LegalLayout from '../components/legal/LegalLayout'

const UPDATED_AT = '30 de setembro de 2026'
const CONTACT_EMAIL = 'lucasmedbasil@gmail.com'

function TermsPage() {
  return (
    <LegalLayout title="Termos de Uso" updatedAt={UPDATED_AT}>
      <p>
        Estes Termos de Uso regulam o acesso e a utilização do <strong>Produzzy</strong>,
        uma plataforma de gestão de estoque, etiquetas e reposição. Ao criar uma
        conta ou utilizar o serviço, você concorda com estes termos. Se não
        concordar, não utilize a plataforma.
      </p>

      <h2>1. O serviço</h2>
      <p>
        O Produzzy permite cadastrar produtos e categorias, controlar
        movimentações de estoque, gerar QR Codes e etiquetas, acompanhar
        necessidades de reposição e colaborar em equipe por meio de workspaces.
        O serviço é fornecido pela internet, no estado em que se encontra, e pode
        evoluir ou mudar ao longo do tempo.
      </p>

      <h2>2. Conta e cadastro</h2>
      <ul>
        <li>Você deve fornecer informações verdadeiras e mantê-las atualizadas.</li>
        <li>
          É necessário confirmar o e-mail para ativar o acesso. Você é
          responsável por manter sua senha em segurança e por toda atividade
          realizada na sua conta.
        </li>
        <li>
          Você deve ter capacidade legal para aceitar estes termos. O serviço
          não se destina a menores de idade sem autorização do responsável.
        </li>
      </ul>

      <h2>3. Uso aceitável</h2>
      <p>Ao usar o Produzzy, você concorda em não:</p>
      <ul>
        <li>violar leis aplicáveis ou direitos de terceiros;</li>
        <li>
          tentar acessar dados de outros usuários ou workspaces sem autorização,
          burlar mecanismos de segurança ou sobrecarregar a plataforma;
        </li>
        <li>
          enviar conteúdo ilícito, ofensivo ou que não tenha o direito de usar.
        </li>
      </ul>

      <h2>4. Seus dados e conteúdo</h2>
      <p>
        Os produtos, categorias e demais informações que você cadastra
        continuam sendo seus. Você nos concede apenas a licença necessária para
        armazenar e processar esses dados com a finalidade de operar o serviço
        para você. O tratamento de dados pessoais é descrito na{' '}
        <a href="/privacidade">Política de Privacidade</a>.
      </p>

      <h2>5. Planos e pagamento</h2>
      <p>
        Atualmente o Produzzy é oferecido gratuitamente. Poderemos, no futuro,
        introduzir planos pagos e limites de uso — nesse caso, as condições
        serão informadas com antecedência e as funcionalidades pagas só serão
        cobradas mediante sua contratação.
      </p>

      <h2>6. Disponibilidade e suporte</h2>
      <p>
        Nos esforçamos para manter o serviço disponível e seguro, mas ele é
        fornecido "como está", sem garantia de funcionamento ininterrupto ou
        livre de erros. Podemos realizar manutenções, atualizações e
        interrupções quando necessário.
      </p>

      <h2>7. Limitação de responsabilidade</h2>
      <p>
        Na máxima extensão permitida pela lei, o Produzzy não se responsabiliza
        por danos indiretos, lucros cessantes ou perda de dados decorrentes do
        uso ou da impossibilidade de uso do serviço. Recomendamos que você
        mantenha cópias próprias de informações críticas.
      </p>

      <h2>8. Encerramento</h2>
      <p>
        Você pode excluir sua conta a qualquer momento em{' '}
        <strong>Configurações → Privacidade e dados</strong>. Podemos suspender
        ou encerrar contas que violem estes termos. Ao encerrar, seus dados
        pessoais são tratados conforme a Política de Privacidade.
      </p>

      <h2>9. Alterações nestes termos</h2>
      <p>
        Podemos atualizar estes termos periodicamente. Mudanças relevantes serão
        comunicadas pela plataforma ou por e-mail. O uso continuado após a
        atualização representa concordância com a nova versão.
      </p>

      <h2>10. Lei aplicável e foro</h2>
      <p>
        Estes termos são regidos pelas leis da República Federativa do Brasil.
        Fica eleito o foro do domicílio do usuário para dirimir eventuais
        controvérsias, salvo disposição legal em contrário.
      </p>

      <h2>11. Contato</h2>
      <p>
        Dúvidas sobre estes termos? Fale com a gente pelo e-mail{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>
    </LegalLayout>
  )
}

export default TermsPage

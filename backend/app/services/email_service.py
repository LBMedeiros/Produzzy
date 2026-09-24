"""services.email_service — envio de e-mail via SMTP (provider-agnostic).

Funciona com Gmail (senha de app), Brevo, SendGrid, Mailgun, etc. — basta
configurar as variáveis PRODUZZY_SMTP_* no ambiente. Se não estiver
configurado, `send_email` levanta EmailNotConfiguredError (o chamador decide
o que fazer, sem vazar essa informação para o usuário final)."""
import logging
import smtplib
from email.message import EmailMessage

from app.config import (
    PRODUZZY_SMTP_FROM,
    PRODUZZY_SMTP_FROM_NAME,
    PRODUZZY_SMTP_HOST,
    PRODUZZY_SMTP_PASSWORD,
    PRODUZZY_SMTP_PORT,
    PRODUZZY_SMTP_USER,
    PRODUZZY_SMTP_USE_TLS,
)


logger = logging.getLogger("produzzy.email")


class EmailNotConfiguredError(RuntimeError):
    """SMTP não está configurado neste ambiente."""


class EmailSendError(RuntimeError):
    """Falha ao enviar o e-mail pelo servidor SMTP."""


def _sender_address() -> str:
    return PRODUZZY_SMTP_FROM or PRODUZZY_SMTP_USER


def is_configured() -> bool:
    return bool(PRODUZZY_SMTP_HOST and _sender_address())


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
):
    if not is_configured():
        raise EmailNotConfiguredError("Envio de e-mail não está configurado.")

    message = EmailMessage()
    message["Subject"] = subject
    from_name = PRODUZZY_SMTP_FROM_NAME or "Produzzy"
    message["From"] = f"{from_name} <{_sender_address()}>"
    message["To"] = to_email
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(PRODUZZY_SMTP_HOST, PRODUZZY_SMTP_PORT, timeout=15) as server:
            if PRODUZZY_SMTP_USE_TLS:
                server.starttls()

            if PRODUZZY_SMTP_USER:
                server.login(PRODUZZY_SMTP_USER, PRODUZZY_SMTP_PASSWORD)

            server.send_message(message)
    except EmailNotConfiguredError:
        raise
    except Exception as error:  # noqa: BLE001 - normaliza qualquer falha de SMTP
        raise EmailSendError(str(error)) from error


def send_password_reset_email(to_email: str, reset_link: str):
    subject = "Redefinição de senha • Produzzy"

    text_body = (
        "Olá,\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta Produzzy.\n"
        "Abra o link abaixo para criar uma nova senha:\n\n"
        f"{reset_link}\n\n"
        "Se você não fez esse pedido, pode ignorar este e-mail — sua senha "
        "continua a mesma.\n\n"
        "Por segurança, o link expira em alguns minutos.\n\n"
        "Equipe Produzzy"
    )

    html_body = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;background:#0f172a;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:16px;padding:32px">
    <h1 style="margin:0 0 8px;font-size:20px;color:#0f172a">Redefinir sua senha</h1>
    <p style="margin:0 0 20px;font-size:14px;color:#475569;line-height:1.6">
      Recebemos um pedido para redefinir a senha da sua conta
      <strong>Produzzy</strong>. Clique no botão abaixo para criar uma nova senha.
    </p>
    <a href="{reset_link}"
       style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;
              font-weight:700;font-size:14px;padding:12px 22px;border-radius:10px">
      Criar nova senha
    </a>
    <p style="margin:22px 0 0;font-size:12px;color:#94a3b8;line-height:1.6">
      Se você não fez esse pedido, pode ignorar este e-mail — sua senha continua
      a mesma. Por segurança, o link expira em alguns minutos.
    </p>
    <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;word-break:break-all">
      Se o botão não funcionar, copie e cole este endereço no navegador:<br>
      {reset_link}
    </p>
  </div>
</div>"""

    send_email(to_email, subject, text_body, html_body)

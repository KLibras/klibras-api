import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import aiosmtplib
import logging
from app.core.config import settings

# Configura o logger do módulo
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def send_welcome_email(user_email: str) -> bool:
    """Envia um e-mail de boas-vindas de forma assíncrona para um novo usuário.

    Args:
        user_email (str): O endereço de e-mail do destinatário.

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    logger.info("Preparando e-mail de boas-vindas para: %s", user_email)
    try:
        subject = "Sejá bem-vindo a nossa plataforma!"

        # Versão em texto plano da mensagem
        plain_text = f"""
Olá!

Sua conta foi criada com sucessso {user_email}

Agradecemos o registro!!

KLibras
        """.strip()

        # Versão em HTML da mensagem com formatação
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4CAF50;">Welcome!</h2>
                    <p>Olá</p>
                    <p>Sua conta foi criada com sucessso <strong>{user_email}</strong></p>
                    <p>Agradecemos o registro!</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 14px;">Best regards,<br>KLibras</p>
                </div>
            </body>
        </html>
        """

        # Envia o e-mail de forma assíncrona
        result = await _send_email_async(
            to_emails=[user_email],
            subject=subject,
            plain_text=plain_text,
            html_content=html_content
        )

        if result:
            logger.info("E-mail de boas-vindas enviado para: %s", user_email)
        else:
            logger.warning("Falha ao enviar e-mail de boas-vindas para: %s", user_email)

        return result

    except Exception as e:
        logger.exception("Exceção ao enviar e-mail de boas-vindas para %s: %s", user_email, e)
        return False


async def _send_email_async(
    to_emails: List[str],
    subject: str,
    plain_text: str,
    html_content: Optional[str] = None
) -> bool:
    """Função auxiliar para enviar e-mails de forma assíncrona.

    Args:
        to_emails (List[str]): Lista de e-mails dos destinatários.
        subject (str): Assunto do e-mail.
        plain_text (str): Conteúdo do e-mail em texto plano.
        html_content (Optional[str]): Conteúdo do e-mail em HTML (opcional).

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("Credenciais SMTP não configuradas")
        return False

    try:
        logger.info("Enviando e-mail assíncrono para: %s", to_emails)

        # Compõe a mensagem MIME com partes de texto e HTML
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.smtp_username
        message["To"] = ", ".join(to_emails)

        text_part = MIMEText(plain_text, "plain")
        message.attach(text_part)

        if html_content:
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

        # Envia o e-mail usando o cliente SMTP assíncrono
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_server,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_username,
            password=settings.smtp_password,
        )

        logger.info("E-mail enviado com sucesso para %s", to_emails)
        return True

    except Exception as e:
        logger.exception("Erro ao enviar e-mail assíncrono para %s: %s", to_emails, e)
        return False


def send_email_sync(
    to_emails: List[str],
    subject: str,
    plain_text: str,
    html_content: Optional[str] = None
) -> bool:
    """Função auxiliar para enviar e-mails de forma síncrona.

    Args:
        to_emails (List[str]): Lista de e-mails dos destinatários.
        subject (str): Assunto do e-mail.
        plain_text (str): Conteúdo do e-mail em texto plano.
        html_content (Optional[str]): Conteúdo do e-mail em HTML (opcional).

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("Credenciais SMTP não configuradas")
        return False

    try:
        logger.info("Enviando e-mail síncrono para: %s", to_emails)

        # Compõe a mensagem MIME com partes de texto e HTML
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.smtp_username
        message["To"] = ", ".join(to_emails)

        text_part = MIMEText(plain_text, "plain")
        message.attach(text_part)

        if html_content:
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

        # Estabelece conexão SMTP segura e envia o e-mail
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls(context=context)
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_username, to_emails, message.as_string())

        logger.info("E-mail enviado com sucesso para %s", to_emails)
        return True

    except Exception as e:
        logger.exception("Erro ao enviar e-mail síncrono para %s: %s", to_emails, e)
        return False



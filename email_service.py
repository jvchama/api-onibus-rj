import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------------------------------------------------------------------------
# Configuração SMTP via variáveis de ambiente.
# Para dev/testes, usar Mailtrap (sandbox gratuito, sem envio real):
#   SMTP_HOST=sandbox.smtp.mailtrap.io
#   SMTP_PORT=2525
#   SMTP_USER e SMTP_PASS obtidos no dashboard do Mailtrap.
# ---------------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "alertas@riobus.dev")


def send_bus_alert(
    to_email: str,
    bus_line: str,
    bus_ordem: str,
    eta_minutes: float,
    stop_lat: float,
    stop_lon: float,
    stop_name: str | None = None,
) -> bool:
    """Envia e-mail de alerta informando que um ônibus está próximo da parada.

    Retorna True se o envio foi bem-sucedido, False caso contrário.
    Usa apenas stdlib (smtplib + email.mime) — sem dependências externas.
    """
    if not SMTP_USER:
        print("[email] SMTP_USER não configurado — e-mail não enviado.")
        return False

    # Usa o endereço legível se disponível; caso contrário, mostra coordenadas
    local_parada = stop_name if stop_name else f"(lat: {stop_lat}, lon: {stop_lon})"

    subject = f"[BusCarioca] Ônibus {bus_line} chegando em ~{eta_minutes} min"
    body = (
        f"Olá!\n\n"
        f"O ônibus da linha {bus_line} (ordem: {bus_ordem}) está a aproximadamente "
        f"{eta_minutes} minutos da sua parada "
        f"{local_parada}.\n\n"
        f"Prepare-se para sair!\n\n"
        f"— BusCarioca"
    )

    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        print(f"[email] Alerta enviado para {to_email} — linha {bus_line}, ETA {eta_minutes} min")
        return True
    except Exception as e:
        print(f"[email] Falha ao enviar para {to_email}: {e}")
        return False

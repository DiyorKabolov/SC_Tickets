import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from dotenv import load_dotenv

load_dotenv()

MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_HOST = os.getenv("MAIL_HOST", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "1") == "1"
MAIL_TIMEOUT = int(os.getenv("MAIL_TIMEOUT", "15"))


def _build_message(to_email, username, code):
    safe_username = escape(username)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Код подтверждения — SC Tickets"
    msg["From"] = MAIL_FROM
    msg["To"] = to_email

    html = f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="margin:0 0 12px">SC Tickets</h2>
      <p style="margin:0 0 12px">Привет, <b>{safe_username}</b>!</p>
      <p style="margin:0 0 18px">Ваш код подтверждения:</p>
      <div style="margin:20px 0;text-align:center">
        <span style="font-size:34px;font-weight:700;letter-spacing:10px;font-family:monospace;background:#f4f4f7;padding:14px 20px;border-radius:12px;color:#111">
          {code}
        </span>
      </div>
      <p style="color:#666;font-size:12px;margin:0">Никому не сообщайте этот код.</p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))
    return msg


def send_verify_email(to_email, username, code):
    if not MAIL_FROM or not MAIL_PASSWORD:
        print("Email is not configured: set MAIL_FROM and MAIL_PASSWORD")
        return False

    try:
        msg = _build_message(to_email, username, code)
        if MAIL_USE_SSL:
            with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT, timeout=MAIL_TIMEOUT) as server:
                server.login(MAIL_FROM, MAIL_PASSWORD)
                server.sendmail(MAIL_FROM, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=MAIL_TIMEOUT) as server:
                server.starttls()
                server.login(MAIL_FROM, MAIL_PASSWORD)
                server.sendmail(MAIL_FROM, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print(f"Error sending email: {exc}")
        return False

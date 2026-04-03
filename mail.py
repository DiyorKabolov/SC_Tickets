import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

MAIL_FROM = "dierkabolov34@gmail.com"        # замени
MAIL_PASSWORD = "loylqdzpldrxzkbm"  # замени, без пробелов

def send_verify_email(to_email, username, code):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Код подтверждения — SC Tickets"
    msg["From"]    = MAIL_FROM
    msg["To"]      = to_email

    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="margin-bottom:8px">SC·TICKETS</h2>
      <p>Привет, <b>{username}</b>!</p>
      <p>Ваш код подтверждения:</p>
      <div style="margin:24px 0;text-align:center">
        <span style="font-size:36px;font-weight:700;letter-spacing:12px;
                     font-family:monospace;background:#f0f0f0;
                     padding:16px 24px;border-radius:12px;color:#0c0c0e">
          {code}
        </span>
      </div>
      <p style="color:#888;font-size:12px">Код действует 24 часа. Никому не сообщайте его.</p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(MAIL_FROM, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, to_email, msg.as_string())
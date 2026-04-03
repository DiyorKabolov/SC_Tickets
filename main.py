import qrcode
import io
import os
import uuid
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
from database import init_db, save_ticket

# --- Конфиг ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
TEMPLATE_PATH = os.path.join(BASE_DIR, "ghb.pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "Generated_tickets")
QR_PATH = os.path.join(BASE_DIR, "qr_ticket.png")
# --------------

init_db()
pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_ticket(ticket_id: str, event: dict = None):
    qr_img = qrcode.make(ticket_id)
    qr_img.save(QR_PATH)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.setFont("Arial", 10)
    c.drawString(50, 750, f"ID: {ticket_id}")

    if event:
        c.drawString(50, 735, f"Мероприятие: {event['title']}")
        c.drawString(50, 720, f"Дата: {event['date']}")
        c.drawString(50, 705, f"Место: {event.get('location', '—')}")

    c.drawImage(QR_PATH, 200, 300, width=400, height=400)
    c.save()
    packet.seek(0)

    template_pdf = PdfReader(TEMPLATE_PATH)
    overlay_pdf  = PdfReader(packet)
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])

    output_pdf = PdfWriter()
    output_pdf.add_page(page)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(OUTPUT_DIR, f"ticket_{timestamp}.pdf")

    with open(result_path, "wb") as f_out:
        output_pdf.write(f_out)

    print(f"Файл успешно создан: {result_path}")
    return result_path


if __name__ == "__main__":
    # Для ручного теста — генерирует один билет без события
    init_db()
    generate_ticket(ticket_id=str(uuid.uuid4()))
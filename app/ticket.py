import qrcode
import io
import os
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
from app.database import init_db

# --- Конфиг ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Попробуем стандартный путь, если нет — можно положить шрифт в папку проекта
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
if not os.path.exists(FONT_PATH):
    # Запасной вариант (например, если шрифт в корне проекта)
    FONT_PATH = os.path.join(BASE_DIR, "arial.ttf")

TEMPLATE_PATH = os.path.join(BASE_DIR, "..", "assets", "ghb.pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "Generated_tickets")
# --------------

os.makedirs(OUTPUT_DIR, exist_ok=True)
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))
else:
    print(f"Warning: Font not found at {FONT_PATH}. PDF might have issues with Cyrillic.")


def generate_ticket(ticket_id: str, event: dict = None):
    # Кэширование: если билет уже есть, просто возвращаем путь
    result_path = os.path.join(OUTPUT_DIR, f"ticket_{ticket_id}.pdf")
    if os.path.exists(result_path):
        return result_path

    # Unique QR file per ticket to avoid race conditions
    qr_path = os.path.join(OUTPUT_DIR, f"qr_{ticket_id}.png")
    qr_img = qrcode.make(ticket_id)
    qr_img.save(qr_path)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    
    # Используем Arial если он загружен
    font_name = "Arial" if os.path.exists(FONT_PATH) else "Helvetica"
    c.setFont(font_name, 10)
    
    c.drawString(50, 750, f"ID: {ticket_id}")

    if event:
        c.drawString(50, 735, f"Мероприятие: {event['title']}")
        c.drawString(50, 720, f"Дата: {event['date']}")
        c.drawString(50, 705, f"Место: {event.get('location', '—')}")

    c.drawImage(qr_path, 200, 300, width=400, height=400)
    c.save()
    packet.seek(0)


    if not os.path.exists(TEMPLATE_PATH):
        # Если шаблона нет, создаем просто PDF с данными
        with open(result_path, "wb") as f_out:
            f_out.write(packet.getbuffer())
    else:
        template_pdf = PdfReader(TEMPLATE_PATH)
        overlay_pdf  = PdfReader(packet)
        page = template_pdf.pages[0]
        page.merge_page(overlay_pdf.pages[0])

        output_pdf = PdfWriter()
        output_pdf.add_page(page)

        with open(result_path, "wb") as f_out:
            output_pdf.write(f_out)

    # Cleanup temp QR image
    try:
        os.remove(qr_path)
    except OSError:
        pass

    return result_path


if __name__ == "__main__":
    init_db()
    generate_ticket(ticket_id=str(uuid.uuid4()))

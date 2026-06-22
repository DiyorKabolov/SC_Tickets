import io
import os
import uuid

import qrcode
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.database import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "Generated_tickets")
TEMPLATE_DIR = os.path.join(BASE_DIR, "..", "assets", "ticket_templates")
DEFAULT_TEMPLATE_PATH = os.path.join(BASE_DIR, "..", "assets", "ghb.pdf")

DEFAULT_FONT_CANDIDATES = [
    os.getenv("PDF_FONT_PATH", ""),
    os.path.join(BASE_DIR, "arial.ttf"),
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)


def _register_pdf_font():
    for font_path in DEFAULT_FONT_CANDIDATES:
        if font_path and os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("SCTicketsFont", font_path))
                return "SCTicketsFont"
            except Exception:
                continue
    return "Helvetica"


PDF_FONT_NAME = _register_pdf_font()


def _get_template_path(event):
    if event and event.get("ticket_template"):
        custom_path = os.path.join(TEMPLATE_DIR, event["ticket_template"])
        if os.path.exists(custom_path):
            return custom_path
    return DEFAULT_TEMPLATE_PATH


def _build_overlay(ticket_id, event=None):
    buffer = io.BytesIO()
    qr_img = qrcode.make(ticket_id)
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.setFont(PDF_FONT_NAME, 10)
    c.drawString(50, 750, f"ID: {ticket_id}")

    if event:
        c.drawString(50, 735, f"Мероприятие: {event['title']}")
        c.drawString(50, 720, f"Дата: {event['date']}")
        c.drawString(50, 705, f"Место: {event.get('location', '—')}")

    c.drawImage(ImageReader(buffer), 200, 300, width=400, height=400, mask="auto")
    c.save()
    packet.seek(0)
    return packet


def generate_ticket(ticket_id: str, event: dict = None):
    result_path = os.path.join(OUTPUT_DIR, f"ticket_{ticket_id}.pdf")
    if os.path.exists(result_path):
        return result_path

    overlay_pdf = _build_overlay(ticket_id, event)
    template_path = _get_template_path(event)

    if not os.path.exists(template_path):
        with open(result_path, "wb") as f_out:
            f_out.write(overlay_pdf.getbuffer())
        return result_path

    template_pdf = PdfReader(template_path)
    overlay_reader = PdfReader(overlay_pdf)
    page = template_pdf.pages[0]
    page.merge_page(overlay_reader.pages[0])

    output_pdf = PdfWriter()
    output_pdf.add_page(page)

    with open(result_path, "wb") as f_out:
        output_pdf.write(f_out)

    return result_path


if __name__ == "__main__":
    init_db()
    generate_ticket(ticket_id=str(uuid.uuid4()))

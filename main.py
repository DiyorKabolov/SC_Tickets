import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
import uuid
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from database import init_db, save_ticket
import socket
import os
from datetime import datetime

init_db()

pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))

tamplate_path = r"C:\Users\krieg\OneDrive\Desktop\QR generator\SC_Tickets\ghb.pdf"

output_dir = "C:\Users\krieg\OneDrive\Desktop\QR generator\SC_Tickets\Generated_tickets"
os.makedirs(output_dir, exist_ok=True)

ticket_id = str(uuid.uuid4())

save_ticket(ticket_id)

qr_img = qrcode.make(ticket_id)
qr_path = "qr_ticket.png"
qr_img.save(qr_path)

packet = io.BytesIO()

c = canvas.Canvas(packet, pagesize=A4)

c.setFont("Arial", 10)
c.drawString(50, 750, f"Уникальный ID: {ticket_id}")
c.drawImage(qr_path, 200, 300, width=400, height=400)

c.save()
packet.seek(0)

template_pdf = PdfReader(tamplate_path)
overlay_pdf = PdfReader(packet)

page = template_pdf.pages[0]
page.merge_page(overlay_pdf.pages[0])

output_pdf = PdfWriter()
output_pdf.add_page(page)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_filename = f"ticket{timestamp}.pdf"
result_path = os.path.join(output_dir, result_filename)

with open(result_path, "wb") as f_out: output_pdf.write(f_out)

print(f"Файл успешно создан: {result_path}")

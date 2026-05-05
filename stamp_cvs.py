import os
import glob
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_overlay(name):
    packet = io.BytesIO()
    # Create a new PDF with Reportlab
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica-Bold", 16)
    # Draw string near the top left/center
    can.drawString(50, 750, f"Name: {name}")
    can.save()
    packet.seek(0)
    return PdfReader(packet)

files = glob.glob('example_data/CVs/**/*.pdf', recursive=True)

for file in files:
    filename = os.path.basename(file)
    name_without_ext = os.path.splitext(filename)[0]
    readable_name = name_without_ext.replace('_', ' ')
    
    print(f"Stamping {file} with '{readable_name}'")
    
    reader = PdfReader(file)
    writer = PdfWriter()
    
    # create the overlay pdf
    overlay_pdf = create_overlay(readable_name)
    overlay_page = overlay_pdf.pages[0]
    
    for i, page in enumerate(reader.pages):
        if i == 0:
            page.merge_page(overlay_page)
        writer.add_page(page)
        
    with open(file, "wb") as f:
        writer.write(f)

print("Finished stamping CVs.")

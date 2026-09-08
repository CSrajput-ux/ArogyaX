"""
ArogyaX Healthcare Platform — Digital Prescription PDF Generator
Built with ReportLab Document Engine
"""

import os
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from backend.config import Config

def draw_clinical_background(canvas, doc, doctor_name, doctor_spec):
    """Draw a clean clinical header & footer background on the prescription PDF."""
    teal = colors.HexColor('#0d9488')
    blue = colors.HexColor('#0066ff')
    grey = colors.HexColor('#f1f5f9')

    canvas.saveState()
    
    # Top Header Background
    canvas.setFillColor(blue)
    canvas.rect(0, 792 - 120, 612, 120, fill=1, stroke=0)

    # Doctor Text Header
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawString(40, 792 - 50, f"Dr. {doctor_name}")
    canvas.setFont("Helvetica", 11)
    canvas.drawString(40, 792 - 75, f"SPECIALIST IN {doctor_spec.upper()}")

    # Top Right Cross Icon
    canvas.setFillColor(colors.white)
    canvas.circle(530, 792 - 60, 42, fill=1, stroke=0)
    canvas.setFillColor(blue)
    canvas.setFont("Helvetica-Bold", 38)
    canvas.drawCentredString(530, 792 - 74, "+")

    # Bottom Footer Bar
    canvas.setFillColor(grey)
    canvas.rect(0, 0, 612, 40, fill=1, stroke=0)

    # Footer Text
    canvas.setFillColor(colors.HexColor('#334155'))
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(40, 15, "AROGYAX CLINICAL PLATFORM")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(250, 15, "Verified Digital Prescription")
    canvas.drawString(460, 15, "support@arogyax.com")

    canvas.restoreState()

def generate_prescription_pdf(appointment_id, appt, doctor_name, doctor_spec, selected_medicines, advice_notes=""):
    """
    Generate and save a hospital-grade digital prescription PDF.
    Returns the relative filepath in static directory.
    """
    os.makedirs(Config.PRESCRIPTIONS_FOLDER, exist_ok=True)
    pdf_filename = f"prescription_{appointment_id}.pdf"
    pdf_filepath = os.path.join(Config.PRESCRIPTIONS_FOLDER, pdf_filename)
    
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    content = []
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.textColor = colors.HexColor('#334155')

    # Patient Meta Row 1: Name and Date
    p_name = Paragraph("Patient Name:", normal_style)
    p_name_val = Paragraph(f"<b>{appt.get('name', 'Patient')}</b>", normal_style)
    p_date = Paragraph("Date:", normal_style)
    p_date_val = Paragraph(f"<b>{datetime.utcnow().strftime('%d %b %Y')}</b>", normal_style)

    t1 = Table([[p_name, p_name_val, p_date, p_date_val]], colWidths=[80, 260, 40, 152])
    t1.setStyle(TableStyle([
        ('LINEBELOW', (1, 0), (1, 0), 1, colors.HexColor('#94a3b8')),
        ('LINEBELOW', (3, 0), (3, 0), 1, colors.HexColor('#94a3b8')),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    content.append(t1)
    content.append(Spacer(1, 12))

    # Patient Meta Row 2: Age, Blood Group, Gender
    p_age = Paragraph("Age:", normal_style)
    p_age_val = Paragraph(f"<b>{appt.get('age', 'N/A')} yrs</b>", normal_style)
    p_bg = Paragraph("Blood Group:", normal_style)
    p_bg_val = Paragraph(f"<b>{appt.get('blood_group', 'N/A')}</b>", normal_style)
    p_phone = Paragraph("Contact:", normal_style)
    p_phone_val = Paragraph(f"<b>{appt.get('phone_number', 'N/A')}</b>", normal_style)

    t2 = Table([[p_age, p_age_val, p_bg, p_bg_val, p_phone, p_phone_val]], colWidths=[30, 80, 75, 80, 55, 212])
    t2.setStyle(TableStyle([
        ('LINEBELOW', (1, 0), (1, 0), 1, colors.HexColor('#94a3b8')),
        ('LINEBELOW', (3, 0), (3, 0), 1, colors.HexColor('#94a3b8')),
        ('LINEBELOW', (5, 0), (5, 0), 1, colors.HexColor('#94a3b8')),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    content.append(t2)
    content.append(Spacer(1, 24))

    # Rx Symbol
    rx_style = ParagraphStyle('Rx', fontName='Helvetica-Bold', fontSize=28, textColor=colors.HexColor('#0066ff'), spaceAfter=15)
    content.append(Paragraph("Rx", rx_style))

    # Medicines List
    med_style = ParagraphStyle('Med', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#0f172a'), spaceAfter=4)
    inst_style = ParagraphStyle('Inst', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#64748b'), leftIndent=16, spaceAfter=12)

    for idx, m in enumerate(selected_medicines):
        content.append(Paragraph(f"{idx+1}. {m}", med_style))
        content.append(Paragraph("Take as directed by physician after meals.", inst_style))

    if advice_notes:
        content.append(Spacer(1, 15))
        content.append(Paragraph("<b>Clinical Advice & Follow-up:</b>", med_style))
        content.append(Paragraph(advice_notes, inst_style))

    content.append(Spacer(1, 30))

    # Signature Block
    sig_data = [
        [f"Dr. {doctor_name}"],
        ["_______________________"],
        ["Authorized Signatory & Seal"]
    ]
    sig_table = Table(sig_data, colWidths=[200])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (0, 2), 'Helvetica'),
        ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#64748b')),
        ('FONTSIZE', (0, 2), (0, 2), 8),
    ]))
    main_sig_table = Table([["", sig_table]], colWidths=[332, 200])
    content.append(main_sig_table)

    # Build PDF with background callback
    pdf = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=150, bottomMargin=60)
    
    def canvas_maker(canvas, doc):
        draw_clinical_background(canvas, doc, doctor_name, doctor_spec)
        
    pdf.build(content, onFirstPage=canvas_maker, onLaterPages=canvas_maker)
    
    buffer.seek(0)
    with open(pdf_filepath, 'wb') as f:
        f.write(buffer.read())
        
    # Relative path in static folder
    return f"prescriptions/{pdf_filename}"

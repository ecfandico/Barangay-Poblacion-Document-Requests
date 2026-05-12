"""
PDF Generation Utilities for Documents
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import FileResponse
import os
from django.conf import settings
import calendar
from django.utils import timezone


def generate_clearance_pdf(service_request, staff_name="Barangay Secretary"):
    """
    Generate PDF clearance document for service request
    """
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1a1a1a')
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=5,
        textColor=colors.HexColor('#333333')
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=12,
        leading=16
    )
    
    # Document titles
    document_titles = {
        "Barangay Clearance": "BARANGAY CLEARANCE",
        "Barangay ID": "BARANGAY IDENTIFICATION CARD",
        "Business Permit": "BUSINESS PERMIT",
        "Residency Certificate": "CERTIFICATE OF RESIDENCY",
        "Certificate of Indigency": "CERTIFICATE OF INDIGENCY",
    }
    
    document_title = document_titles.get(service_request.service_type.name, "CERTIFICATE")
    
    # Header content
    elements.append(Paragraph("REPUBLIC OF THE PHILIPPINES", header_style))
    elements.append(Paragraph("PROVINCE OF NORTH COTABATO", header_style))
    elements.append(Paragraph("CITY OF KIDAPAWAN", header_style))
    elements.append(Paragraph("BARANGAY POBLACIÓN", header_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(document_title, title_style))
    elements.append(Spacer(1, 30))
    
    # Body content
    ctc_issued_on = service_request.ctc_issued_on
    if ctc_issued_on:
        ctc_issued_on_str = ctc_issued_on.strftime('%B %d, %Y')
    else:
        ctc_issued_on_str = "Not provided"
    
    body_text = f"""
    <b>TO WHOM IT MAY CONCERN:</b><br/><br/>
    
    This is to certify that <b>{service_request.resident.get_full_name()}</b>, 
    {service_request.resident_age if service_request.resident_age else 'N/A'} years of age, is a bonafide resident of 
    {service_request.resident_address if service_request.resident_address else 'Not provided'}, Barangay Población, Kidapawan City.<br/><br/>
    
    He/She has been residing in this barangay for {service_request.years_in_residence} years 
    and {service_request.months_in_residence} months.<br/><br/>
    
    This certification is issued upon the request of the above-named person for 
    <b>{service_request.purpose}</b>.<br/><br/>
    
    Community Tax Certificate No.: <b>{service_request.community_tax_cert_no if service_request.community_tax_cert_no else 'Not provided'}</b><br/>
    Date Issued: <b>{ctc_issued_on_str}</b><br/>
    Place Issued: <b>{service_request.ctc_issued_at if service_request.ctc_issued_at else 'Not provided'}</b><br/>
    Official Receipt No.: <b>{service_request.or_number if service_request.or_number else 'Not provided'}</b><br/><br/>
    
    Issued this <b>{service_request.date_requested.strftime('%d')}</b> day of 
    <b>{service_request.date_requested.strftime('%B %Y')}</b> at Barangay Población, Kidapawan City.
    """
    
    elements.append(Paragraph(body_text, body_style))
    elements.append(Spacer(1, 40))
    
    # Signature section
    current_date = timezone.now()
    
    signature_table_data = [
        ["", f"Date Issued: {current_date.strftime('%B %d, %Y')}"],
    ]
    
    signature_table = Table(signature_table_data, colWidths=[250, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(signature_table)
    elements.append(Spacer(1, 20))
    
    # Footer note
    footer_note = Paragraph(
        "<i>This document is electronically generated and does not require a signature.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    )
    elements.append(footer_note)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


def generate_monthly_statistics_pdf(monthly_stats, current_stats, total_requests, total_revenue, popular_services):
    """
    Generate PDF report of monthly statistics (Summary view)
    """
    buffer = BytesIO()
    
    # Use landscape orientation for better table display
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a1a')
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor('#667eea')
    )
    
    # Title
    current_date = timezone.now()
    elements.append(Paragraph("BARANGAY POBLACIÓN", title_style))
    elements.append(Paragraph(f"Monthly Statistics Report", title_style))
    elements.append(Paragraph(f"Generated on: {current_date.strftime('%B %d, %Y at %H:%M')}", 
                              ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)))
    elements.append(Spacer(1, 20))
    
    # Summary Section
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Spacer(1, 10))
    
    summary_data = [
        ['Total Requests (All Time)', f"{total_requests:,}"],
        ['Total Revenue (All Time)', f"₱{total_revenue:,.2f}"],
        ['Current Month', f"{current_stats.year}-{current_stats.month:02d}"],
        ['Current Month Requests', f"{current_stats.total_requests:,}"],
        ['Current Month Revenue', f"₱{current_stats.total_revenue:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Popular Services Section
    elements.append(Paragraph("Most Requested Services", heading_style))
    elements.append(Spacer(1, 10))
    
    popular_data = [['Service Name', 'Request Count', 'Processing Fee']]
    for service in popular_services:
        count = getattr(service, 'request_count', 0)
        popular_data.append([
            service.name,
            str(count),
            f"₱{float(service.processing_fee):,.2f}"
        ])
    
    popular_table = Table(popular_data, colWidths=[250, 100, 100])
    popular_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(popular_table)
    elements.append(Spacer(1, 20))
    
    # Monthly Statistics Table
    elements.append(Paragraph("Monthly Statistics (Last 12 Months)", heading_style))
    elements.append(Spacer(1, 10))
    
    monthly_data = [['Month', 'Total', 'Approved', 'Completed', 'Pending', 'Revenue']]
    
    for stat in monthly_stats:
        monthly_data.append([
            stat.year_month,
            str(stat.total_requests),
            str(stat.approved_requests),
            str(stat.completed_requests),
            str(stat.pending_requests),
            f"₱{float(stat.total_revenue):,.2f}"
        ])
    
    monthly_table = Table(monthly_data, colWidths=[80, 60, 60, 60, 60, 100])
    monthly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(monthly_table)
    elements.append(Spacer(1, 20))
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_text = Paragraph(
        "<i>This report is automatically generated by the Barangay Población Online System. "
        "Data is accurate as of the generation date.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    )
    elements.append(footer_text)
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


def generate_monthly_requests_pdf(year, month, requests_data, stats):
    """
    Generate PDF report of all requests for a specific month
    """
    buffer = BytesIO()
    
    # Use landscape orientation for better table display
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=50,
        bottomMargin=50,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor('#1a1a1a')
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.HexColor('#667eea')
    )
    
    # Get month name
    month_name = calendar.month_name[month]
    
    # Title
    current_date = timezone.now()
    elements.append(Paragraph("BARANGAY POBLACIÓN", title_style))
    elements.append(Paragraph(f"Service Requests Report", title_style))
    elements.append(Paragraph(f"{month_name} {year}", title_style))
    elements.append(Paragraph(f"Generated on: {current_date.strftime('%B %d, %Y at %H:%M')}", 
                              ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9)))
    elements.append(Spacer(1, 15))
    
    # Summary Section
    elements.append(Paragraph("Summary", heading_style))
    
    summary_data = [
        ['Total Requests', str(stats['total'])],
        ['Approved Requests', str(stats['approved'])],
        ['Completed Requests', str(stats['completed'])],
        ['Pending Requests', str(stats['pending'])],
        ['Rejected Requests', str(stats['rejected'])],
        ['Total Revenue', f"₱{stats['revenue']:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Detailed Requests Table
    elements.append(Paragraph("Detailed Service Requests", heading_style))
    elements.append(Spacer(1, 10))
    
    # Table headers
    headers = ['ID', 'Resident Name', 'Email', 'Service Type', 'Date Requested', 'Status', 'Purpose', 'Payment Status']
    
    # Prepare table data
    table_data = [headers]
    
    for req in requests_data:
        # Truncate purpose if too long
        purpose = req['purpose'][:50] + '...' if len(req['purpose']) > 50 else req['purpose']
        
        row = [
            str(req['id']),
            req['resident_name'],
            req['email'],
            req['service_type'],
            req['date_requested'],
            req['status_display'],
            purpose,
            'Paid' if req['payment_verified'] else ('Pending' if req['has_payment_proof'] else 'Not Paid')
        ]
        table_data.append(row)
    
    # Create table with column widths
    col_widths = [40, 120, 130, 100, 80, 80, 150, 80]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the table
    table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Body style
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        
        # Row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = Paragraph(
        "<i>This report includes all service requests submitted during the specified month. "
        "Data is accurate as of the generation date.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    )
    elements.append(footer_text)
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def generate_simple_clearance_pdf(service_request):
    """
    Alternative simpler PDF generator as fallback
    """
    from reportlab.pdfgen import canvas
    from io import BytesIO
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 100, "BARANGAY POBLACIÓN")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 115, "Kidapawan City, North Cotabato")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, height - 145, service_request.service_type.name.upper())
    
    # Body
    y_position = height - 180
    c.setFont("Helvetica", 11)
    
    # Format CTC date safely
    ctc_issued_on_str = service_request.ctc_issued_on.strftime('%B %d, %Y') if service_request.ctc_issued_on else "Not provided"
    
    lines = [
        f"TO WHOM IT MAY CONCERN:",
        "",
        f"This is to certify that {service_request.resident.get_full_name()}, "
        f"{service_request.resident_age if service_request.resident_age else 'N/A'} years of age, is a bonafide resident of "
        f"{service_request.resident_address if service_request.resident_address else 'Not provided'}, Barangay Población, Kidapawan City.",
        "",
        f"He/She has been residing in this barangay for {service_request.years_in_residence} years "
        f"and {service_request.months_in_residence} months.",
        "",
        f"This certification is issued upon the request of the above-named person for "
        f"{service_request.purpose}.",
        "",
        f"CTC No.: {service_request.community_tax_cert_no if service_request.community_tax_cert_no else 'Not provided'}",
        f"CTC Issued On: {ctc_issued_on_str}",
        f"CTC Issued At: {service_request.ctc_issued_at if service_request.ctc_issued_at else 'Not provided'}",
        f"OR No.: {service_request.or_number if service_request.or_number else 'Not provided'}",
        "",
        f"Issued this {service_request.date_requested.strftime('%B %d, %Y')} at Barangay Población, Kidapawan City.",
    ]
    
    for line in lines:
        if line:
            c.drawString(72, y_position, line)
        y_position -= 20
        
        if y_position < 100:
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 11)
    
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf
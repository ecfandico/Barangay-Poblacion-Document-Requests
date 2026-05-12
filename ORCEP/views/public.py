"""
Public views (home, document verification, etc.)
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from ..models import ServiceRequest


def home_view(request):
    """Home page view"""
    return render(request, 'ORCEP/home.html')


def verify_document(request, token):
    """Public document verification via QR code"""
    service_request = get_object_or_404(ServiceRequest, verification_token=token)
    
    # Check token validity
    if not service_request.is_token_valid():
        return render(request, 'ORCEP/verification_expired.html')
    
    # Check if request is ready
    if service_request.status not in ['approved', 'ready']:
        return render(request, 'ORCEP/document_not_ready.html', {
            'status': service_request.get_status_display()
        })
    
    context = {
        'service_request': service_request,
        'document_title': service_request.service_type.name,
        'resident_name': service_request.resident.get_full_name(),
    }
    return render(request, 'ORCEP/document_verification.html', context)


def download_document(request, token):
    """Download the document as PDF after verification"""
    from io import BytesIO
    from django.http import FileResponse
    from ..utils.pdf_generator import generate_clearance_pdf
    
    service_request = get_object_or_404(ServiceRequest, verification_token=token)
    
    # Check if token is valid
    if not service_request.is_token_valid():
        return HttpResponse("Verification token has expired.", status=400)
    
    # Check if request is approved
    if service_request.status not in ['approved', 'ready', 'completed']:
        return HttpResponse("Document is not ready for download.", status=400)
    
    try:
        # Generate PDF
        pdf_content = generate_clearance_pdf(service_request, staff_name="Barangay Secretary")
        
        # Create filename
        filename = f"{service_request.service_type.name.replace(' ', '_')}_{service_request.id}.pdf"
        
        # Return PDF as download
        response = FileResponse(
            BytesIO(pdf_content),
            as_attachment=True,
            filename=filename,
            content_type='application/pdf'
        )
        
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating document: {str(e)}", status=500)
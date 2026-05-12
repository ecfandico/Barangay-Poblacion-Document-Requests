"""
User-specific views (dashboard, service requests, etc.)
"""
from io import BytesIO
from django.http import FileResponse
from ..utils.pdf_generator import generate_clearance_pdf, generate_simple_clearance_pdf
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import ServiceType, ServiceRequest

@login_required
def services_dashboard(request):
    """Display available services and user's requests"""
    available_services = ServiceType.objects.filter(is_active=True)
    user_requests = ServiceRequest.objects.filter(
        resident=request.user
    ).order_by('-date_requested')
    
    context = {
        'available_services': available_services,
        'user_requests': user_requests,
    }
    return render(request, 'ORCEP/services_dashboard.html', context)


@login_required
def service_request_form(request, service_id):
    """Handle new service request form"""
    service_type = get_object_or_404(ServiceType, id=service_id, is_active=True)
    
    if request.method == 'POST':
        # Get form data
        purpose = request.POST['purpose']
        resident_age = request.POST['resident_age']
        resident_address = request.POST['resident_address']
        years_in_residence = request.POST['years_in_residence']
        months_in_residence = request.POST.get('months_in_residence', 0)
        community_tax_cert_no = request.POST['community_tax_cert_no']
        ctc_issued_on = request.POST['ctc_issued_on']
        ctc_issued_at = request.POST['ctc_issued_at']
        or_number = request.POST['or_number']
        payment_proof = request.FILES.get('payment_proof')
        
        # Create service request
        service_request = ServiceRequest.objects.create(
            resident=request.user,
            service_type=service_type,
            purpose=purpose,
            resident_age=resident_age,
            resident_address=resident_address,
            years_in_residence=years_in_residence,
            months_in_residence=months_in_residence,
            community_tax_cert_no=community_tax_cert_no,
            ctc_issued_on=ctc_issued_on,
            ctc_issued_at=ctc_issued_at,
            or_number=or_number,
            status='pending',
            payment_proof=payment_proof,
            payment_date=timezone.now() if payment_proof else None,
        )
        
        messages.success(request, 
            f"Your {service_type.name} request has been submitted successfully!"
        )
        return redirect('services_dashboard')
    
    return render(request, 'ORCEP/service_request_form.html', {'service_type': service_type})


@login_required
def user_dashboard(request):
    """User dashboard with recent requests"""
    recent_requests = ServiceRequest.objects.filter(
        resident=request.user
    ).order_by('-date_requested')[:10]
    
    # Generate QR codes for approved requests
    for req in recent_requests:
        if req.status in ['approved', 'ready', 'completed'] and not req.qr_code:
            if hasattr(req, 'generate_qr_code'):
                req.generate_qr_code()
    
    return render(request, 'ORCEP/user_dashboard.html', {
        'recent_requests': recent_requests
    })


@login_required
def user_qr_code(request, request_id):
    """Display QR code for user's own request"""
    service_request = get_object_or_404(
        ServiceRequest, 
        id=request_id, 
        resident=request.user
    )
    
    # Authorization check
    if service_request.resident != request.user:
        messages.error(request, "You are not authorized to view this QR code.")
        return redirect('user_dashboard')
    
    # Generate QR code if needed
    if service_request.status in ['approved', 'ready', 'completed'] and not service_request.qr_code:
        if hasattr(service_request, 'generate_qr_code'):
            service_request.generate_qr_code()
    
    context = {
        'service_request': service_request,
        'verification_url': service_request.get_verification_url(),
        'full_verification_url': f"http://10.0.0.19:8000{service_request.get_verification_url()}",
    }
    return render(request, 'ORCEP/user_qr_code.html', context)


def generate_clearance(request, request_id):
    """Generate and download PDF clearance document"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Check if the request belongs to the logged-in user
    if service_request.resident != request.user:
        messages.error(request, "You are not authorized to download this document.")
        return redirect('services_dashboard')
    
    # Check if request is approved or ready
    if service_request.status not in ['approved', 'ready', 'completed']:
        messages.error(request, "This request has not been approved yet.")
        return redirect('services_dashboard')
    
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
        print(f"PDF generation error: {e}")
        # Fallback to simple PDF or show error
        try:
            pdf_content = generate_simple_clearance_pdf(service_request)
            filename = f"clearance_{service_request.id}.pdf"
            response = FileResponse(
                BytesIO(pdf_content),
                as_attachment=True,
                filename=filename,
                content_type='application/pdf'
            )
            return response
        except Exception as e2:
            messages.error(request, f"Error generating PDF: {str(e2)}")
            return redirect('user_dashboard')

@login_required
def user_request_detail(request, request_id):
    """Show detailed information for a specific request"""
    service_request = get_object_or_404(
        ServiceRequest, 
        id=request_id, 
        resident=request.user
    )
    
    # Check if user is authorized to view this request
    if service_request.resident != request.user:
        messages.error(request, "You are not authorized to view this request.")
        return redirect('user_dashboard')
    
    context = {
        'service_request': service_request,
    }
    return render(request, 'ORCEP/user_request_detail.html', context)
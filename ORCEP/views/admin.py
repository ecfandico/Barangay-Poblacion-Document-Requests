"""
Admin-specific views (dashboard, statistics, management)
"""
from django.http import FileResponse
from io import BytesIO
from ..utils.pdf_generator import generate_clearance_pdf, generate_monthly_statistics_pdf, generate_monthly_requests_pdf
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Count
import json
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import time
import os
import calendar
from ..models import (
    User, ResidentProfile, ServiceType, ServiceRequest, 
    MonthlyStatistics
)
from django.conf import settings

@staff_member_required
def admin_resident_delete(request, user_id):
    """Delete a resident user account"""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.contrib.auth.models import User
    from ..models import ResidentProfile, ServiceRequest
    
    print("=" * 50)
    print(f"DELETE FUNCTION CALLED")
    print(f"User ID: {user_id}")
    print(f"Request Method: {request.method}")
    print(f"POST data: {request.POST}")
    print("=" * 50)
    
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # Check if trying to delete own account
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('admin_resident_list')
    
    if request.method == 'POST':
        print("PROCESSING POST REQUEST - DELETING USER")
        user_name = user_to_delete.get_full_name()
        
        try:
            # Delete service requests first (optional, cascade should handle)
            ServiceRequest.objects.filter(resident=user_to_delete).delete()
            # Delete the user
            user_to_delete.delete()
            print(f"SUCCESS: User {user_name} deleted")
            messages.success(request, f"User '{user_name}' has been permanently deleted.")
        except Exception as e:
            print(f"ERROR: {e}")
            messages.error(request, f"Error deleting user: {str(e)}")
        
        return redirect('admin_resident_list')
    
    # GET request - show confirmation page
    print("SHOWING CONFIRMATION PAGE")
    resident_profile = get_object_or_404(ResidentProfile, user=user_to_delete)
    service_requests_count = ServiceRequest.objects.filter(resident=user_to_delete).count()
    
    context = {
        'resident_user': user_to_delete,
        'resident_profile': resident_profile,
        'service_requests_count': service_requests_count,
    }
    return render(request, 'ORCEP/admin_resident_delete_confirm.html', context)

def staff_member_required(function=None):
    """Custom decorator for barangay staff"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'barangaystaff') and u.barangaystaff.is_active
    )
    return actual_decorator(function) if function else actual_decorator


@staff_member_required
def admin_requests(request):
    """List all service requests with filtering"""
    
    # Get statistics (same as dashboard)
    total_requests = ServiceRequest.objects.count()
    pending_requests = ServiceRequest.objects.filter(status='pending').count()
    approved_requests = ServiceRequest.objects.filter(status='approved').count()
    completed_requests = ServiceRequest.objects.filter(status='completed').count()
    
    # Get filtered service requests
    service_requests = ServiceRequest.objects.all().order_by('-date_requested')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        service_requests = service_requests.filter(status=status_filter)

    context = {
        'service_requests': service_requests,
        'current_filter': status_filter,
        # Add statistics to context
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'completed_requests': completed_requests,
    }
    return render(request, 'ORCEP/admin_requests.html', context)


@staff_member_required
def admin_statistics(request):
    """Display monthly statistics dashboard"""
    print("DEBUG: admin_statistics view called")

    """Monthly statistics dashboard"""
    # Update current month's statistics
    current_stats = MonthlyStatistics.update_monthly_statistics()

    # Get statistics for the last 12 months
    monthly_stats = MonthlyStatistics.objects.all().order_by('-year', '-month')[:12]
    
    # Calculate overall statistics
    total_requests = ServiceRequest.objects.count()
    total_revenue = sum(
        float(request.service_type.processing_fee) 
        for request in ServiceRequest.objects.filter(status__in=['approved', 'completed', 'ready'])
    )
    
    # Get today's statistics
    today = timezone.now().date()
    today_requests = ServiceRequest.objects.filter(date_requested__date=today).count()
    
    # Get this week's statistics
    week_start = today - timezone.timedelta(days=today.weekday())
    week_requests = ServiceRequest.objects.filter(
        date_requested__date__gte=week_start
    ).count()
    
    # Get popular service types - FIXED THIS LINE
    popular_services = ServiceType.objects.annotate(
        request_count=Count('requests')
    ).order_by('-request_count')[:5]
    
    context = {
        'monthly_stats': monthly_stats,
        'current_stats': current_stats,
        'total_requests': total_requests,
        'total_revenue': total_revenue,
        'today_requests': today_requests,
        'week_requests': week_requests,
        'popular_services': popular_services,
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
    }
    
    return render(request, 'ORCEP/admin_statistics.html', context)


@staff_member_required
def admin_request_detail(request, request_id):
    """View and manage specific service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Handle quick status updates
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(ServiceRequest.STATUS_CHOICES):
            service_request.status = new_status
            service_request.save()
            messages.success(request, 
                f"Request status updated to {service_request.get_status_display()}."
            )
            return redirect('admin_request_detail', request_id=request_id)
    
    return render(request, 'ORCEP/admin_request_detail.html', {
        'service_request': service_request
    })


def admin_generate_clearance(request, request_id):
    """Generate and download PDF clearance document (admin version)"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    try:
        # Generate PDF
        pdf_content = generate_clearance_pdf(service_request, staff_name=request.user.get_full_name())
        
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
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('admin_request_detail', request_id=request_id)


@staff_member_required
def admin_request_create(request):
    """Create a new service request (for admins)"""
    if request.method == 'POST':
        resident_email = request.POST.get('resident_email')
        service_type_id = request.POST.get('service_type')
        purpose = request.POST.get('purpose')
        
        try:
            resident = User.objects.get(email=resident_email)
            service_type = ServiceType.objects.get(id=service_type_id)
            
            ServiceRequest.objects.create(
                resident=resident,
                service_type=service_type,
                purpose=purpose,
                status='pending'
            )
            
            messages.success(request, f"Service request created for {resident.get_full_name()}")
            return redirect('admin_requests')
            
        except User.DoesNotExist:
            messages.error(request, "Resident with this email does not exist.")
        except ServiceType.DoesNotExist:
            messages.error(request, "Invalid service type selected.")
    
    service_types = ServiceType.objects.filter(is_active=True)
    return render(request, 'ORCEP/admin_request_create.html', {'service_types': service_types})


@staff_member_required
def admin_request_update(request, request_id):
    """Update a service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        # Update basic fields
        service_request.purpose = request.POST.get('purpose', service_request.purpose)
        service_request.resident_age = request.POST.get('resident_age', service_request.resident_age)
        service_request.resident_address = request.POST.get('resident_address', service_request.resident_address)
        service_request.years_in_residence = request.POST.get('years_in_residence', service_request.years_in_residence)
        service_request.months_in_residence = request.POST.get('months_in_residence', service_request.months_in_residence)
        service_request.community_tax_cert_no = request.POST.get('community_tax_cert_no', service_request.community_tax_cert_no)
        service_request.ctc_issued_on = request.POST.get('ctc_issued_on', service_request.ctc_issued_on)
        service_request.ctc_issued_at = request.POST.get('ctc_issued_at', service_request.ctc_issued_at)
        service_request.or_number = request.POST.get('or_number', service_request.or_number)
        service_request.admin_notes = request.POST.get('admin_notes', service_request.admin_notes)
        
        # Update status
        new_status = request.POST.get('status')
        if new_status in dict(ServiceRequest.STATUS_CHOICES):
            service_request.status = new_status
        
        service_request.save()
        messages.success(request, "Service request updated successfully!")
        return redirect('admin_request_detail', request_id=request_id)
    
    context = {
        'service_request': service_request,
        'status_choices': ServiceRequest.STATUS_CHOICES,
    }
    return render(request, 'ORCEP/admin_request_update.html', context)


@staff_member_required
def admin_request_delete(request, request_id):
    """Delete a service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        resident_name = service_request.resident.get_full_name()
        service_request.delete()
        messages.success(request, f"Service request for {resident_name} has been deleted.")
        return redirect('admin_requests')
    
    return render(request, 'ORCEP/admin_request_delete.html', {'service_request': service_request})


@staff_member_required
def admin_service_type_list(request):
    """List all service types"""
    service_types = ServiceType.objects.all()
    return render(request, 'ORCEP/admin_service_type_list.html', {'service_types': service_types})


@staff_member_required
def admin_service_type_create(request):
    """Create a new service type"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        requirements = request.POST.get('requirements')
        processing_fee = request.POST.get('processing_fee', 0)
        processing_days = request.POST.get('processing_days', 3)
        is_active = 'is_active' in request.POST
        
        ServiceType.objects.create(
            name=name,
            description=description,
            requirements=requirements,
            processing_fee=processing_fee,
            processing_days=processing_days,
            is_active=is_active
        )
        
        messages.success(request, f"Service type '{name}' created successfully!")
        return redirect('admin_service_type_list')
    
    return render(request, 'ORCEP/admin_service_type_create.html')


@staff_member_required
def admin_service_type_update(request, type_id):
    """Update a service type"""
    service_type = get_object_or_404(ServiceType, id=type_id)
    
    if request.method == 'POST':
        service_type.name = request.POST.get('name')
        service_type.description = request.POST.get('description')
        service_type.requirements = request.POST.get('requirements')
        service_type.processing_fee = request.POST.get('processing_fee', 0)
        service_type.processing_days = request.POST.get('processing_days', 3)
        service_type.is_active = 'is_active' in request.POST
        service_type.save()
        
        messages.success(request, f"Service type '{service_type.name}' updated successfully!")
        return redirect('admin_service_type_list')
    
    return render(request, 'ORCEP/admin_service_type_update.html', {'service_type': service_type})


@staff_member_required
def admin_service_type_delete(request, type_id):
    """Delete a service type"""
    service_type = get_object_or_404(ServiceType, id=type_id)
    
    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        return redirect('admin_service_type_list')
    
    return render(request, 'ORCEP/admin_service_type_delete.html', {'service_type': service_type})


@staff_member_required
def generate_qr_code(request, request_id):
    """Generate and display QR code for a request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Generate verification token if not exists
    if not service_request.verification_token:
        service_request.generate_verification_token()
    
    # Generate QR code image if not exists
    if not service_request.qr_code:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Get the verification URL - USING CORRECT IP
        verification_url = f"http://10.13.68.235:8000{service_request.get_verification_url()}"
        
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        # Save to model
        filename = f'qr_code_{service_request.id}_{int(time.time())}.png'
        service_request.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        service_request.save()
    
    context = {
        'service_request': service_request,
        'verification_url': service_request.get_verification_url(),
        'full_verification_url': f"http://10.13.68.235:8000{service_request.get_verification_url()}",  # FIXED
    }
    return render(request, 'ORCEP/admin_qr_code.html', context)


@staff_member_required
def email_qr_code(request, request_id):
    """Send QR code to resident via email (simulated for now)"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Generate QR code if not exists
    if not service_request.qr_code:
        service_request.generate_qr_code()
    
    # For now, just show a success message
    # In production, you'd integrate with an email service
    messages.success(
        request, 
        f"QR code has been prepared for {service_request.resident.get_full_name()}. "
        f"In a production system, this would be emailed to {service_request.resident.email}"
    )
    
    return redirect('generate_qr_code', request_id=request_id)


@staff_member_required
def admin_resident_list(request):
    """List all residents with their profiles"""
    # Get all users who have resident profiles
    residents = User.objects.filter(residentprofile__isnull=False).order_by('-date_joined')
    
    # Get filter parameters
    verification_filter = request.GET.get('verification', '')
    search_query = request.GET.get('search', '')
    
    # Apply filters
    if verification_filter:
        residents = residents.filter(residentprofile__verification_status=verification_filter)
    
    if search_query:
        residents = residents.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'residents': residents,
        'verification_filter': verification_filter,
        'search_query': search_query,
    }
    return render(request, 'ORCEP/admin_resident_list.html', context)


@staff_member_required
def admin_resident_detail(request, user_id):
    """View and manage a specific resident's profile"""
    resident_user = get_object_or_404(User, id=user_id)
    resident_profile = get_object_or_404(ResidentProfile, user=resident_user)
    
    # Handle verification actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            resident_profile.verification_status = 'approved'
            resident_profile.verified_by = request.user
            resident_profile.verified_at = timezone.now()
            messages.success(request, f"Resident {resident_user.get_full_name()} has been verified.")
        
        elif action == 'reject':
            resident_profile.verification_status = 'rejected'
            resident_profile.verification_notes = request.POST.get('rejection_reason', '')
            resident_profile.verified_by = request.user
            resident_profile.verified_at = timezone.now()
            messages.warning(request, f"Resident {resident_user.get_full_name()} has been rejected.")
        
        elif action == 'pending':
            resident_profile.verification_status = 'pending'
            messages.info(request, f"Resident {resident_user.get_full_name()} status set to pending.")
        
        elif action == 'update_notes':
            resident_profile.verification_notes = request.POST.get('verification_notes', '')
            messages.success(request, "Verification notes updated.")
        
        resident_profile.save()
        return redirect('admin_resident_detail', user_id=user_id)
    
    # Get resident's service requests
    service_requests = ServiceRequest.objects.filter(resident=resident_user).order_by('-date_requested')
    
    context = {
        'resident_user': resident_user,
        'resident_profile': resident_profile,
        'service_requests': service_requests,
    }
    return render(request, 'ORCEP/admin_resident_detail.html', context)


@staff_member_required
def admin_resident_verify(request, user_id, action):
    """Quick verify/reject resident (for AJAX or quick actions)"""
    resident_user = get_object_or_404(User, id=user_id)
    resident_profile = get_object_or_404(ResidentProfile, user=resident_user)
    
    if action == 'approve':
        resident_profile.verification_status = 'approved'
        resident_profile.verified_by = request.user
        resident_profile.verified_at = timezone.now()
        messages.success(request, f"Resident {resident_user.get_full_name()} has been verified.")
    elif action == 'reject':
        resident_profile.verification_status = 'rejected'
        resident_profile.verified_by = request.user
        resident_profile.verified_at = timezone.now()
        messages.warning(request, f"Resident {resident_user.get_full_name()} has been rejected.")
    
    resident_profile.save()
    return redirect('admin_resident_list')


@staff_member_required
def verify_payment(request, request_id):
    """Verify payment for a service request"""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except:
            data = {}
        
        service_request = get_object_or_404(ServiceRequest, id=request_id)
        
        if data.get('verified') or True:  # Allow verification
            service_request.payment_verified = True
            service_request.payment_verified_by = request.user
            service_request.payment_verified_at = timezone.now()
            service_request.save()
            
            return JsonResponse({'success': True, 'message': 'Payment verified successfully'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def test_media(request):
    """Test if media files are accessible"""
    from django.http import HttpResponse
    
    # Create a test file
    test_file = os.path.join(settings.MEDIA_ROOT, 'test.txt')
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, 'w') as f:
        f.write('Test file for media URL checking')
    
    test_html = f"""
    <h1>Media Files Test</h1>
    <p>MEDIA_URL: {settings.MEDIA_URL}</p>
    <p>MEDIA_ROOT: {settings.MEDIA_ROOT}</p>
    <p>DEBUG: {settings.DEBUG}</p>
    <p>Try accessing: <a href="{settings.MEDIA_URL}test.txt">{settings.MEDIA_URL}test.txt</a></p>
    """
    
    return HttpResponse(test_html)

@staff_member_required
def admin_statistics_pdf(request):
    """Generate and download monthly statistics PDF report"""
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from io import BytesIO
    from django.utils import timezone
    
    print("=" * 50)
    print("PDF DOWNLOAD REQUEST RECEIVED")
    print(f"Time: {timezone.now()}")
    print(f"User: {request.user}")
    print("=" * 50)
    
    try:
        # Create the HttpResponse object with PDF headers
        response = HttpResponse(content_type='application/pdf')
        filename = f"monthly_statistics_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create the PDF object
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width/2, height - 50, "BARANGAY POBLACIÓN")
        
        p.setFont("Helvetica", 12)
        p.drawCentredString(width/2, height - 70, "Monthly Statistics Report")
        
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, height - 90, f"Generated on: {timezone.now().strftime('%B %d, %Y at %H:%M')}")
        
        # Get statistics
        from ..models import MonthlyStatistics, ServiceRequest, ServiceType
        
        # Monthly statistics
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 130, "Monthly Statistics (Last 12 Months)")
        
        monthly_stats = MonthlyStatistics.objects.all().order_by('-year', '-month')[:12]
        
        y = height - 150
        p.setFont("Helvetica", 9)
        
        # Table headers
        p.drawString(50, y, "Month")
        p.drawString(130, y, "Total")
        p.drawString(190, y, "Approved")
        p.drawString(260, y, "Completed")
        p.drawString(340, y, "Pending")
        p.drawString(420, y, "Revenue")
        
        y -= 20
        p.line(50, y + 8, 520, y + 8)
        
        for stat in monthly_stats:
            p.drawString(50, y, f"{stat.year}-{stat.month:02d}")
            p.drawString(130, y, str(stat.total_requests))
            p.drawString(190, y, str(stat.approved_requests))
            p.drawString(260, y, str(stat.completed_requests))
            p.drawString(340, y, str(stat.pending_requests))
            p.drawString(420, y, f"₱{float(stat.total_revenue):,.2f}")
            y -= 20
            
            if y < 100:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 9)
        
        # Footer
        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width/2, 30, "This report is automatically generated by the Barangay Población Online System")
        
        p.save()
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        print("PDF generated successfully!")
        return response
        
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error generating PDF report: {str(e)}")
        return redirect('admin_statistics')

@staff_member_required
def test_pdf(request):
    """Test if PDF generation is working"""
    from django.http import HttpResponse
    return HttpResponse("PDF test view is working! Status: OK")

@staff_member_required
def admin_monthly_report_pdf(request, year, month):
    """Generate PDF report of all requests for a specific month"""
    
    print(f"DEBUG: Generating PDF for {year}-{month}")
    
    try:
        # Get date range
        first_day = timezone.datetime(int(year), int(month), 1)
        if int(month) == 12:
            last_day = timezone.datetime(int(year) + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            last_day = timezone.datetime(int(year), int(month) + 1, 1) - timezone.timedelta(days=1)
        
        # Get all requests for this month
        monthly_requests = ServiceRequest.objects.filter(
            date_requested__gte=first_day,
            date_requested__lte=last_day
        ).order_by('-date_requested')
        
        # Prepare data for PDF
        requests_data = []
        total_revenue = 0
        
        for req in monthly_requests:
            # Calculate revenue for paid/completed requests
            if req.status in ['approved', 'completed', 'ready']:
                total_revenue += float(req.service_type.processing_fee)
            
            requests_data.append({
                'id': req.id,
                'resident_name': req.resident.get_full_name(),
                'email': req.resident.email,
                'service_type': req.service_type.name,
                'date_requested': req.date_requested.strftime('%Y-%m-%d %H:%M'),
                'status': req.status,
                'status_display': req.get_status_display(),
                'purpose': req.purpose,
                'payment_verified': req.payment_verified,
                'has_payment_proof': bool(req.payment_proof),
            })
        
        # Calculate statistics
        stats = {
            'total': monthly_requests.count(),
            'approved': monthly_requests.filter(status='approved').count(),
            'completed': monthly_requests.filter(status='completed').count(),
            'pending': monthly_requests.filter(status='pending').count(),
            'rejected': monthly_requests.filter(status='rejected').count(),
            'revenue': total_revenue,
        }
        
        # Generate PDF
        pdf_content = generate_monthly_requests_pdf(
            year=int(year),
            month=int(month),
            requests_data=requests_data,
            stats=stats
        )
        
        # Create filename
        month_name = calendar.month_name[int(month)]
        filename = f"service_requests_{month_name}_{year}.pdf"
        
        # Return PDF as download
        response = FileResponse(
            BytesIO(pdf_content),
            as_attachment=True,
            filename=filename,
            content_type='application/pdf'
        )
        
        print(f"DEBUG: PDF generated for {year}-{month} with {len(requests_data)} requests")
        return response
        
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error generating report: {str(e)}")
        return redirect('admin_statistics')

@staff_member_required
def admin_monthly_requests_view(request, year, month):
    """View all requests for a specific month"""
    from django.utils import timezone
    import calendar
    
    print(f"DEBUG: Viewing requests for {year}-{month}")
    
    try:
        # Get date range
        first_day = timezone.datetime(int(year), int(month), 1)
        if int(month) == 12:
            last_day = timezone.datetime(int(year) + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            last_day = timezone.datetime(int(year), int(month) + 1, 1) - timezone.timedelta(days=1)
        
        # Get all requests for this month
        monthly_requests = ServiceRequest.objects.filter(
            date_requested__gte=first_day,
            date_requested__lte=last_day
        ).order_by('-date_requested')
        
        # Calculate statistics
        total_requests = monthly_requests.count()
        approved_requests = monthly_requests.filter(status='approved').count()
        completed_requests = monthly_requests.filter(status='completed').count()
        pending_requests = monthly_requests.filter(status='pending').count()
        rejected_requests = monthly_requests.filter(status='rejected').count()
        
        # Calculate revenue
        total_revenue = sum(
            float(req.service_type.processing_fee) 
            for req in monthly_requests.filter(status__in=['approved', 'completed', 'ready'])
        )
        
        context = {
            'year': year,
            'month': month,
            'month_name': calendar.month_name[int(month)],
            'requests': monthly_requests,
            'total_requests': total_requests,
            'approved_requests': approved_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'rejected_requests': rejected_requests,
            'total_revenue': total_revenue,
        }
        
        return render(request, 'ORCEP/admin_monthly_requests_view.html', context)
        
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        messages.error(request, f"Error loading requests: {str(e)}")
        return redirect('admin_statistics')
    
from django.http import JsonResponse

@staff_member_required
def admin_delete_statistics(request, year, month):
    """Delete monthly statistics record"""
    if request.method == 'POST':
        try:
            stat = MonthlyStatistics.objects.filter(year=year, month=month).first()
            
            if stat:
                stat.delete()
                return JsonResponse({'success': True, 'message': f'Statistics for {year}-{month} deleted successfully'})
            else:
                return JsonResponse({'success': False, 'error': f'No statistics found for {year}-{month}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
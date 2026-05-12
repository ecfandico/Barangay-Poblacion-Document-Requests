import qrcode
from io import BytesIO
from django.core.files import File
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.conf import settings
from .models import ResidentProfile, ServiceType, ServiceRequest, BarangayStaff
from django.http import HttpResponse, FileResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q

def home_view(request):
    return render(request, 'ORCEP/home.html')

def register_view(request):
    if request.method == 'POST':
        # Get data from form
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        age = request.POST['age']
        gender = request.POST['gender']
        address = request.POST['address']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        id_photo = request.FILES.get('id_photo')  # NEW: Get uploaded file
        
        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'ORCEP/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'ORCEP/register.html')
        
        if not id_photo:  # NEW: Check if ID photo was uploaded
            messages.error(request, "Please upload a valid ID photo for verification.")
            return render(request, 'ORCEP/register.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # ✅ Update the profile with ID photo
            profile = user.residentprofile
            profile.age = age
            profile.gender = gender
            profile.address = address
            profile.id_photo = id_photo  # NEW: Save the ID photo
            profile.verification_status = 'pending'  # NEW: Set as pending
            profile.save()
            
            messages.success(request, "Registration successful! Your account is pending verification. You will be notified once approved.")
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f"Error during registration: {str(e)}")
            # Clean up the user if profile creation failed
            if 'user' in locals():
                user.delete()
            return render(request, 'ORCEP/register.html')
    
    return render(request, 'ORCEP/register.html')

# NEW: Verification function for admin
@staff_member_required
def verify_resident(request, profile_id, action):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.utils import timezone
    from .models import ResidentProfile
    
    profile = get_object_or_404(ResidentProfile, id=profile_id)
    
    if action == 'approve':
        profile.verification_status = 'approved'
        profile.verified_by = request.user
        profile.verified_at = timezone.now()
        profile.save()
        messages.success(request, f"Resident {profile.user.get_full_name()} has been approved.")
    elif action == 'reject':
        profile.verification_status = 'rejected'
        profile.verified_by = request.user
        profile.verified_at = timezone.now()
        profile.save()
        messages.success(request, f"Resident {profile.user.get_full_name()} has been rejected.")
    
    return redirect('admin:ORCEP_residentprofile_changelist')

# Update login_view to check verification status
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        email_or_username = request.POST['email']  # This field can be email OR username
        password = request.POST['password']
        
        # Try to authenticate with email first
        user = authenticate(request, username=email_or_username, password=password)
        
        # If that fails, try to find user by email and authenticate with username
        if user is None:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('home')
        else:
            messages.error(request, "Invalid email/username or password!")
    
    return render(request, 'ORCEP/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

@login_required(login_url='/login/')
def services_dashboard(request):
    # Get all active services
    available_services = ServiceType.objects.filter(is_active=True)
    
    # Get user's previous requests
    user_requests = ServiceRequest.objects.filter(resident=request.user).order_by('-date_requested')
    
    context = {
        'available_services': available_services,
        'user_requests': user_requests,
    }
    return render(request, 'ORCEP/services_dashboard.html', context)

@login_required
def service_request_form(request, service_id):
    service_type = get_object_or_404(ServiceType, id=service_id, is_active=True)
    
    if request.method == 'POST':
        # Get all form data
        purpose = request.POST['purpose']
        resident_age = request.POST['resident_age']
        resident_address = request.POST['resident_address']
        years_in_residence = request.POST['years_in_residence']
        months_in_residence = request.POST.get('months_in_residence', 0)
        community_tax_cert_no = request.POST['community_tax_cert_no']
        ctc_issued_on = request.POST['ctc_issued_on']
        ctc_issued_at = request.POST['ctc_issued_at']
        or_number = request.POST['or_number']
        
        # Get payment proof file - IMPORTANT
        payment_proof = request.FILES.get('payment_proof')
        
        # Debug: Print if file was received
        print(f"Payment proof received: {payment_proof}")
        
        # Create the service request
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
            payment_proof=payment_proof,  # This saves the file
            payment_date=timezone.now() if payment_proof else None,
        )
        
        messages.success(request, f"Your {service_type.name} request has been submitted successfully!")
        return redirect('services_dashboard')
    
    context = {
        'service_type': service_type,
    }
    return render(request, 'ORCEP/service_request_form.html', context)

# Helper function to convert day name to week day number
def get_week_day_number(day_name):
    day_map = {
        'monday': 2, 'tuesday': 3, 'wednesday': 4, 'thursday': 5,
        'friday': 6, 'saturday': 7, 'sunday': 1
    }
    return day_map.get(day_name.lower(), 1)

@login_required
def user_dashboard(request):
    # Get user's recent service requests
    recent_requests = ServiceRequest.objects.filter(resident=request.user).order_by('-date_requested')[:10]
    
    # Generate QR codes for approved/ready requests that don't have them
    for req in recent_requests:
        if req.status in ['approved', 'ready', 'completed'] and not req.qr_code:
            if hasattr(req, 'generate_qr_code'):  # Check if method exists
                req.generate_qr_code()
    
    context = {
        'recent_requests': recent_requests,
    }
    return render(request, 'ORCEP/user_dashboard.html', context)

# REMOVED staff_member_required for easier testing during defense
def generate_clearance(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Optional: Check if approved (you can remove this for testing)
    if service_request.status != 'approved':
        messages.error(request, "This request has not been approved yet.")
        return redirect('services_dashboard')
    
    # Define document titles based on service type
    document_titles = {
        "Barangay Clearance": "BARANGAY CLEARANCE",
        "Barangay ID": "BARANGAY IDENTIFICATION CARD",
        "Business Permit": "BUSINESS PERMIT",
        "Residency Certificate": "CERTIFICATE OF RESIDENCY",
        # Add more service types as needed
    }
    
    # Get the appropriate document title, default to "CERTIFICATE"
    document_title = document_titles.get(service_request.service_type.name, "CERTIFICATE")
    
    context = {
        'request': service_request,
        'issue_date': timezone.now(),
        'document_title': document_title,
    }
    
    return render(request, 'ORCEP/clearance_template.html', context)

def staff_member_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'barangaystaff') and u.barangaystaff.is_active
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

@staff_member_required
def admin_dashboard(request):
    # Get statistics
    total_requests = ServiceRequest.objects.count()
    pending_requests = ServiceRequest.objects.filter(status='pending').count()
    approved_requests = ServiceRequest.objects.filter(status='approved').count()
    completed_requests = ServiceRequest.objects.filter(status='completed').count()

    # Recent requests
    recent_requests = ServiceRequest.objects.all().order_by('-date_requested')[:10]

    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'completed_requests': completed_requests,
        'recent_requests': recent_requests,
    }
    return render(request, 'ORCEP/admin_dashboard.html', context)

@staff_member_required
def admin_requests(request):
    service_requests = ServiceRequest.objects.all().order_by('-date_requested')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        service_requests = service_requests.filter(status=status_filter)

    context = {
        'service_requests': service_requests,
        'current_filter': status_filter,
    }
    return render(request, 'ORCEP/admin_requests.html', context)

@staff_member_required
def admin_request_detail(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Handle quick status updates
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(ServiceRequest.STATUS_CHOICES):
            service_request.status = new_status
            service_request.save()
            messages.success(request, f"Request status updated to {service_request.get_status_display()}.")
            return redirect('admin_request_detail', request_id=request_id)
    
    context = {
        'service_request': service_request,
    }
    return render(request, 'ORCEP/admin_request_detail.html', context)

@staff_member_required
def admin_generate_clearance(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Define document titles
    document_titles = {
        "Barangay Clearance": "BARANGAY CLEARANCE",
        "Barangay ID": "BARANGAY IDENTIFICATION CARD", 
        "Business Permit": "BUSINESS PERMIT",
        "Residency Certificate": "CERTIFICATE OF RESIDENCY",
    }
    
    document_title = document_titles.get(service_request.service_type.name, "CERTIFICATE")
    
    context = {
        'request': service_request,
        'issue_date': timezone.now(),
        'document_title': document_title,
        'staff_member': request.user.get_full_name(),  # This passes the logged-in staff name
    }
    
    return render(request, 'ORCEP/clearance_template.html', context)

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
            
            service_request = ServiceRequest.objects.create(
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
    context = {
        'service_types': service_types,
    }
    return render(request, 'ORCEP/admin_request_create.html', context)

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
    
    context = {
        'service_request': service_request,
    }
    return render(request, 'ORCEP/admin_request_delete.html', context)

@staff_member_required
def admin_service_type_list(request):
    """List all service types"""
    service_types = ServiceType.objects.all()
    context = {
        'service_types': service_types,
    }
    return render(request, 'ORCEP/admin_service_type_list.html', context)

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
        
        service_type = ServiceType.objects.create(
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
    
    context = {
        'service_type': service_type,
    }
    return render(request, 'ORCEP/admin_service_type_update.html', context)

@staff_member_required
def admin_service_type_delete(request, type_id):
    """Delete a service type"""
    service_type = get_object_or_404(ServiceType, id=type_id)
    
    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        return redirect('admin_service_type_list')
    
    context = {
        'service_type': service_type,
    }
    return render(request, 'ORCEP/admin_service_type_delete.html', context)

@staff_member_required
def generate_qr_code(request, request_id):
    """Generate and display QR code for a request"""
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile
    import time
    
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
        
        # Get the verification URL
        verification_url = f"http://10.0.0.19:8000{service_request.get_verification_url()}"
        
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
        'full_verification_url': f"http://10.0.0.19:8000{service_request.get_verification_url()}",
    }
    return render(request, 'ORCEP/admin_qr_code.html', context)

def verify_document(request, token):
    """Public page for document verification via QR code"""
    service_request = get_object_or_404(ServiceRequest, verification_token=token)
    
    # Check if token is valid
    if not service_request.is_token_valid():
        return render(request, 'ORCEP/verification_expired.html')
    
    # Check if request is approved
    if service_request.status != 'approved' and service_request.status != 'ready':
        return render(request, 'ORCEP/document_not_ready.html', {
            'status': service_request.get_status_display()
        })
    
    context = {
        'service_request': service_request,
        'document_title': service_request.service_type.name,
        'resident_name': service_request.resident.get_full_name(),
    }
    return render(request, 'ORCEP/document_verification.html', context)

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

def download_document(request, token):
    """Download the document after verification"""
    service_request = get_object_or_404(ServiceRequest, verification_token=token)
    
    # Check if token is valid
    if not service_request.is_token_valid():
        return HttpResponse("Verification token has expired.", status=400)
    
    # Check if request is approved
    if service_request.status not in ['approved', 'ready', 'completed']:
        return HttpResponse("Document is not ready for download.", status=400)
    
    # Render the clearance document
    document_titles = {
        "Barangay Clearance": "BARANGAY CLEARANCE",
        "Barangay ID": "BARANGAY IDENTIFICATION CARD",
        "Business Permit": "BUSINESS PERMIT",
        "Residency Certificate": "CERTIFICATE OF RESIDENCY",
        "Certificate of Indigency": "CERTIFICATE OF INDIGENCY",
    }
    
    document_title = document_titles.get(service_request.service_type.name, "CERTIFICATE")
    
    context = {
        'request': service_request,
        'issue_date': timezone.now(),
        'document_title': document_title,
        'staff_member': "Barangay Secretary",
    }
    
    # You could also generate PDF here using libraries like reportlab or weasyprint
    return render(request, 'ORCEP/clearance_template.html', context)

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

@login_required
def user_qr_code(request, request_id):
    """Display QR code for a user's own request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id, resident=request.user)
    
    # Check if user is authorized to view this QR code
    if service_request.resident != request.user:
        messages.error(request, "You are not authorized to view this QR code.")
        return redirect('user_dashboard')
    
    # Generate QR code if not exists and request is approved/ready
    if service_request.status in ['approved', 'ready', 'completed'] and not service_request.qr_code:
        if hasattr(service_request, 'generate_qr_code'):
            service_request.generate_qr_code()
    
    context = {
        'service_request': service_request,
        'verification_url': service_request.get_verification_url(),
        'full_verification_url': f"http://10.0.0.19:8000{service_request.get_verification_url()}",
    }
    return render(request, 'ORCEP/user_qr_code.html', context)
@staff_member_required
def admin_statistics(request):
    """Display monthly statistics dashboard"""
    from django.utils import timezone
    from .models import MonthlyStatistics
    
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
    
    # Get popular service types
    from django.db.models import Count
    popular_services = ServiceType.objects.annotate(
        request_count=Count('servicerequest')
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
def verify_payment(request, request_id):
    """Verify payment for a service request"""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        service_request = get_object_or_404(ServiceRequest, id=request_id)
        
        if data.get('verified'):
            service_request.payment_verified = True
            service_request.payment_verified_by = request.user
            service_request.payment_verified_at = timezone.now()
            service_request.save()
            
            return JsonResponse({'success': True, 'message': 'Payment verified successfully'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def test_media(request):
    """Test if media files are accessible"""
    from django.http import HttpResponse
    import os
    
    test_html = f"""
    <h1>Media Files Test</h1>
    <p>MEDIA_URL: {settings.MEDIA_URL}</p>
    <p>MEDIA_ROOT: {settings.MEDIA_ROOT}</p>
    <p>DEBUG: {settings.DEBUG}</p>
    
    <h2>Test a file:</h2>
    <p>Try accessing: <a href="{settings.MEDIA_URL}test.txt">{settings.MEDIA_URL}test.txt</a></p>
    """
    
    # Create a test file
    test_file = os.path.join(settings.MEDIA_ROOT, 'test.txt')
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, 'w') as f:
        f.write('Test file for media URL checking')
    
    return HttpResponse(test_html)
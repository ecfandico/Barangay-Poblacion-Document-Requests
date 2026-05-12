"""
Authentication views (login, register, logout)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from ..models import ResidentProfile


def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        email_or_username = request.POST['email']
        password = request.POST['password']
        
        # Try authentication with provided credentials
        user = authenticate(request, username=email_or_username, password=password)
        
        # If authentication fails, try finding by email
        if user is None:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            
            # Redirect to next page or home
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'home')
        else:
            messages.error(request, "Invalid email/username or password!")
    
    return render(request, 'ORCEP/login.html')


def register_view(request):
    """Handle new user registration"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        age = request.POST['age']
        gender = request.POST['gender']
        address = request.POST['address']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        id_photo = request.FILES.get('id_photo')
        
        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'ORCEP/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'ORCEP/register.html')
        
        if not id_photo:
            messages.error(request, "Please upload a valid ID photo for verification.")
            return render(request, 'ORCEP/register.html')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Update profile with ID photo
            profile = user.residentprofile
            profile.age = age
            profile.gender = gender
            profile.address = address
            profile.id_photo = id_photo
            profile.verification_status = 'pending'
            profile.save()
            
            messages.success(request, 
                "Registration successful! Your account is pending verification. "
                "You will be notified once approved."
            )
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f"Error during registration: {str(e)}")
            # Clean up on failure
            if 'user' in locals():
                user.delete()
            return render(request, 'ORCEP/register.html')
    
    return render(request, 'ORCEP/register.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


def verify_resident(request, profile_id, action):
    """Admin verification of resident profiles"""
    profile = get_object_or_404(ResidentProfile, id=profile_id)
    
    if action == 'approve':
        profile.verification_status = 'approved'
        profile.verified_by = request.user
        profile.verified_at = timezone.now()
        messages.success(request, f"Resident {profile.user.get_full_name()} has been approved.")
    elif action == 'reject':
        profile.verification_status = 'rejected'
        profile.verified_by = request.user
        profile.verified_at = timezone.now()
        messages.success(request, f"Resident {profile.user.get_full_name()} has been rejected.")
    
    profile.save()
    return redirect('admin:ORCEP_residentprofile_changelist')
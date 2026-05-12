"""
Models for ORCEP (Online Request and Community Events Portal)
"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import hashlib
import uuid
from django.utils import timezone


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ResidentProfile(models.Model):
    """Profile information for barangay residents"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_registered = models.DateTimeField(auto_now_add=True)
    
    # ID Verification fields
    id_photo = models.ImageField(
        upload_to='resident_ids/',
        null=True, 
        blank=True,
        verbose_name='Valid ID Photo'
    )
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS, 
        default='pending'
    )
    verification_notes = models.TextField(blank=True, help_text="Admin notes for verification")
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_profiles'
    )
    
    class Meta:
        verbose_name = "Resident Profile"
        verbose_name_plural = "Resident Profiles"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.verification_status}"
    
    def is_verified(self):
        return self.verification_status == 'approved'


class ServiceType(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True) 
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    processing_days = models.IntegerField(default=3)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ServiceRequest(models.Model):
    """Service requests made by residents"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    # Basic Information
    resident = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_requests')
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='requests')
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    purpose = models.TextField()
    
    # Resident Details for Document
    resident_age = models.IntegerField(null=True, blank=True)
    resident_address = models.TextField(null=True, blank=True)
    years_in_residence = models.IntegerField(default=0)
    months_in_residence = models.IntegerField(default=0)
    
    # Community Tax Certificate Details
    community_tax_cert_no = models.CharField(max_length=100, blank=True)
    ctc_issued_on = models.DateField(null=True, blank=True)
    ctc_issued_at = models.CharField(max_length=200, blank=True)
    or_number = models.CharField(max_length=100, blank=True)
    
    # Admin Information
    admin_notes = models.TextField(blank=True)
    
    # QR Code System
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    verification_token = models.CharField(max_length=100, unique=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    
    # Payment Information
    payment_proof = models.ImageField(
        upload_to='payment_proofs/',
        null=True,
        blank=True,
        verbose_name='Proof of Payment'
    )
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_verified = models.BooleanField(default=False)
    payment_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        ordering = ['-date_requested']
    
    def __str__(self):
        return f"{self.resident.get_full_name()} - {self.service_type.name}"
    
    def save(self, *args, **kwargs):
        """Override save to handle verification token generation"""
        if not self.pk and not self.verification_token:
            self.verification_token = f"temp_{uuid.uuid4()}"
        
        super().save(*args, **kwargs)
        
        if self.verification_token.startswith('temp_'):
            self.generate_verification_token()
            super().save(update_fields=['verification_token', 'token_expiry'])
    
    def generate_verification_token(self):
        """Generate a unique verification token for QR code"""
        unique_string = f"{self.id}-{self.resident.email}-{timezone.now().timestamp()}"
        token = hashlib.sha256(unique_string.encode()).hexdigest()[:50]
        self.verification_token = token
        self.token_expiry = timezone.now() + timezone.timedelta(days=30)
        return token
    
    def get_verification_url(self):
        """Generate the URL for document verification"""
        if not self.verification_token:
            self.generate_verification_token()
        return f"/verify-document/{self.verification_token}/"
    
    def is_token_valid(self):
        """Check if the verification token is still valid"""
        if not self.token_expiry:
            return False
        return timezone.now() < self.token_expiry
    
    def get_processing_fee(self):
        """Get the processing fee for this request"""
        return self.service_type.processing_fee


class MonthlyStatistics(models.Model):
    """Track monthly service request statistics"""
    
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    total_requests = models.IntegerField(default=0)
    approved_requests = models.IntegerField(default=0)
    completed_requests = models.IntegerField(default=0)
    pending_requests = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']
        verbose_name = "Monthly Statistics"
        verbose_name_plural = "Monthly Statistics"

    def __str__(self):
        return f"{self.year}-{self.month:02d}: {self.total_requests} requests"
    
    @property
    def year_month(self):
        """Format year and month for display"""
        return f"{self.year}-{self.month:02d}"
    
    @classmethod
    def update_monthly_statistics(cls):
        """Update or create monthly statistics"""
        now = timezone.now()
        year = now.year
        month = now.month
        
        # Get date range for current month
        first_day = timezone.datetime(year, month, 1)
        if month == 12:
            last_day = timezone.datetime(year + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            last_day = timezone.datetime(year, month + 1, 1) - timezone.timedelta(days=1)
        
        # Get requests for current month
        monthly_requests = ServiceRequest.objects.filter(
            date_requested__gte=first_day,
            date_requested__lte=last_day
        )
        
        # Calculate statistics
        total_requests = monthly_requests.count()
        approved_requests = monthly_requests.filter(status='approved').count()
        completed_requests = monthly_requests.filter(status='completed').count()
        pending_requests = monthly_requests.filter(status='pending').count()
        
        # Calculate revenue
        completed_requests_qs = monthly_requests.filter(status__in=['approved', 'completed', 'ready'])
        total_revenue = sum(
            float(request.service_type.processing_fee) 
            for request in completed_requests_qs
        )
        
        # Update or create the monthly record
        stats, created = cls.objects.update_or_create(
            year=year,
            month=month,
            defaults={
                'total_requests': total_requests,
                'approved_requests': approved_requests,
                'completed_requests': completed_requests,
                'pending_requests': pending_requests,
                'total_revenue': total_revenue,
            }
        )
        
        return stats


# Optional Models (if needed later)
class BarangayStaff(models.Model):
    """Barangay staff members with specific positions"""
    
    POSITION_CHOICES = [
        ('captain', 'Barangay Captain'),
        ('secretary', 'Barangay Secretary'),
        ('treasurer', 'Barangay Treasurer'),
        ('clerk', 'Barangay Clerk'),
        ('staff', 'Barangay Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    position = models.CharField(max_length=100, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Barangay Staff"
        verbose_name_plural = "Barangay Staff"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_position_display()}"


class Event(BaseModel):
    """Community events organized by the barangay"""
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ['-date']
    
    def __str__(self):
        return self.title


# ==================== SIGNALS ====================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create resident profile when a new user is created"""
    if created:
        ResidentProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save resident profile when user is saved"""
    if hasattr(instance, 'residentprofile'):
        instance.residentprofile.save()


@receiver(post_save, sender=ServiceRequest)
def update_monthly_statistics_on_request_change(sender, instance, **kwargs):
    """Update monthly statistics when a service request changes"""
    try:
        MonthlyStatistics.update_monthly_statistics()
    except Exception as e:
        # Log error but don't crash the application
        print(f"Error updating monthly statistics: {e}")
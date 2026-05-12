"""
Django Admin configuration for ORCEP models
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from .models import ResidentProfile, ServiceType, ServiceRequest, MonthlyStatistics

@admin.register(ResidentProfile)
class ResidentProfileAdmin(admin.ModelAdmin):
    """Admin interface for ResidentProfile model"""
    
    list_display = ('user', 'get_email', 'age', 'gender', 'verification_status', 
                    'date_registered', 'verification_actions')
    list_filter = ('gender', 'date_registered', 'verification_status')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'address')
    readonly_fields = ('id_photo_preview', 'date_registered')
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'age', 'gender', 'address')
        }),
        ('ID Verification', {
            'fields': ('id_photo', 'id_photo_preview', 'verification_status',
                      'verification_notes', 'verified_by', 'verified_at')
        }),
    )
    actions = ['approve_verification', 'reject_verification']
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
    
    def id_photo_preview(self, obj):
        if obj.id_photo:
            return format_html(
                '<img src="{}" width="300" height="200" style="border-radius: 8px; border: 2px solid #ddd;" />',
                obj.id_photo.url
            )
        return "No ID photo uploaded"
    id_photo_preview.short_description = 'ID Photo Preview'
    
    def verification_actions(self, obj):
        if obj.verification_status == 'pending':
            return format_html(
                '<a class="button" href="{}">Approve</a> &nbsp; '
                '<a class="button" href="{}" style="background: #e53e3e;">Reject</a>',
                reverse('verify_resident', args=[obj.id, 'approve']),
                reverse('verify_resident', args=[obj.id, 'reject'])
            )
        elif obj.verification_status == 'approved':
            return "✅ Verified"
        else:
            return "❌ Rejected"
    verification_actions.short_description = "Actions"
    
    def approve_verification(self, request, queryset):
        updated = queryset.update(
            verification_status='approved',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} resident(s) approved.')
    approve_verification.short_description = "Approve selected residents"
    
    def reject_verification(self, request, queryset):
        updated = queryset.update(verification_status='rejected')
        self.message_user(request, f'{updated} resident(s) rejected.')
    reject_verification.short_description = "Reject selected residents"


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    """Admin interface for ServiceType model"""
    
    list_display = ('name', 'processing_fee', 'processing_days', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'requirements')
        }),
        ('Processing Details', {
            'fields': ('processing_fee', 'processing_days', 'is_active')
        }),
    )


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    """Admin interface for ServiceRequest model"""
    
    list_display = ('resident', 'service_type', 'status', 'date_requested', 'clearance_action')
    list_filter = ('status', 'date_requested', 'service_type')
    search_fields = ('resident__first_name', 'resident__last_name', 'purpose')
    readonly_fields = ('date_requested',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('resident', 'service_type', 'purpose', 'status')
        }),
        ('Resident Details', {
            'fields': ('resident_age', 'resident_address', 'years_in_residence', 'months_in_residence')
        }),
        ('CTC Information', {
            'fields': ('community_tax_cert_no', 'ctc_issued_on', 'ctc_issued_at', 'or_number')
        }),
        ('Payment Information', {
            'fields': ('payment_proof', 'payment_verified', 'payment_verified_by', 'payment_verified_at')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',)
        }),
    )
    actions = ['mark_as_approved', 'mark_as_ready', 'mark_as_completed', 'mark_as_rejected']
    
    def clearance_action(self, obj):
        if obj.status == 'approved':
            url = reverse('generate_clearance', args=[obj.id])
            return format_html('<a class="button" href="{}">Generate Clearance</a>', url)
        return "-"
    clearance_action.short_description = "Actions"
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} service request(s) marked as approved.')
    mark_as_approved.short_description = "Mark selected as approved"
    
    def mark_as_ready(self, request, queryset):
        updated = queryset.update(status='ready')
        self.message_user(request, f'{updated} service request(s) marked as ready for pickup.')
    mark_as_ready.short_description = "Mark selected as ready for pickup"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} service request(s) marked as completed.')
    mark_as_completed.short_description = "Mark selected as completed"
    
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} service request(s) marked as rejected.')
    mark_as_rejected.short_description = "Mark selected as rejected"


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    """Admin interface for MonthlyStatistics model"""
    
    list_display = ('year_month', 'total_requests', 'approved_requests', 
                    'completed_requests', 'pending_requests', 'total_revenue', 'updated_at')
    list_filter = ('year', 'month')
    readonly_fields = ('year', 'month', 'total_requests', 'approved_requests', 
                      'completed_requests', 'pending_requests', 'total_revenue', 'updated_at')
    ordering = ('-year', '-month')
    
    def year_month(self, obj):
        return obj.year_month
    year_month.short_description = 'Month'
    year_month.admin_order_field = ('-year', '-month')
    
    def has_add_permission(self, request):
        """Prevent manual addition - statistics are auto-generated"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of statistics"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of statistics"""
        return False
    

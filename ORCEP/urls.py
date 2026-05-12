"""
URL configuration for ORCEP application
"""
from django.views.generic import RedirectView
from django.urls import path
from .views import (
    # Authentication
    login_view, register_view, logout_view, 
    
    # Public Views
    home_view, verify_document, download_document,
    
    # User Views
    service_request_form, services_dashboard,
    user_dashboard, user_qr_code, generate_clearance,
    user_request_detail,
    
    # Admin Views
    admin_statistics, admin_requests,
    admin_request_detail, admin_request_create,
    admin_request_update, admin_request_delete,
    admin_generate_clearance, generate_qr_code,
    email_qr_code, admin_resident_list,
    admin_resident_detail, admin_resident_verify,
    admin_service_type_list, admin_service_type_create,
    admin_service_type_update, admin_service_type_delete,
    verify_payment, admin_resident_delete, admin_statistics_pdf,
    admin_monthly_report_pdf, admin_monthly_requests_view, 
    admin_delete_statistics,
    
    # Test/Utility Views
    #test_media, test_upload,
    test_pdf
)

#app_name = 'ORCEP'

urlpatterns = [
    # ==================== PUBLIC URLS ====================
    path('barangay-admin/', RedirectView.as_view(url='/barangay-admin/requests/', permanent=True)),
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
    # ==================== USER URLS ====================
    path('services/', services_dashboard, name='services_dashboard'),
    path('services/request/<int:service_id>/', service_request_form, name='service_request_form'),
    path('dashboard/', user_dashboard, name='user_dashboard'),
    path('dashboard/qr-code/<int:request_id>/', user_qr_code, name='user_qr_code'),
    path('admin/clearance/<int:request_id>/', generate_clearance, name='generate_clearance'),
    path('dashboard/request/<int:request_id>/', user_request_detail, name='user_request_detail'),
    
    # ==================== ADMIN DASHBOARD ====================
    path('barangay-admin/statistics/', admin_statistics, name='admin_statistics'),
    path('barangay-admin/statistics/pdf/', admin_statistics_pdf, name='admin_statistics_pdf'),
    path('barangay-admin/statistics/<int:year>/<int:month>/', admin_monthly_requests_view, name='admin_monthly_requests_view'),
    path('barangay-admin/statistics/<int:year>/<int:month>/delete/', admin_delete_statistics, name='admin_delete_statistics'),
    path('barangay-admin/statistics/pdf/<int:year>/<int:month>/', admin_monthly_report_pdf, name='admin_monthly_report_pdf'),
    
    # ==================== ADMIN - SERVICE REQUESTS ====================
    path('barangay-admin/requests/', admin_requests, name='admin_requests'),
    path('barangay-admin/requests/create/', admin_request_create, name='admin_request_create'),
    path('barangay-admin/requests/<int:request_id>/', admin_request_detail, name='admin_request_detail'),
    path('barangay-admin/requests/<int:request_id>/update/', admin_request_update, name='admin_request_update'),
    path('barangay-admin/requests/<int:request_id>/delete/', admin_request_delete, name='admin_request_delete'),
    path('barangay-admin/generate-clearance/<int:request_id>/', admin_generate_clearance, name='admin_generate_clearance'),
    
    # ==================== ADMIN - RESIDENTS ====================
    path('barangay-admin/residents/', admin_resident_list, name='admin_resident_list'),
    path('barangay-admin/residents/<int:user_id>/delete/', admin_resident_delete, name='admin_resident_delete'),  # This must come BEFORE the detail URL
    path('barangay-admin/residents/<int:user_id>/', admin_resident_detail, name='admin_resident_detail'),
    path('barangay-admin/residents/<int:user_id>/<str:action>/', admin_resident_verify, name='admin_resident_verify'),
    
    # ==================== ADMIN - SERVICE TYPES ====================
    path('barangay-admin/service-types/', admin_service_type_list, name='admin_service_type_list'),
    path('barangay-admin/service-types/create/', admin_service_type_create, name='admin_service_type_create'),
    path('barangay-admin/service-types/<int:type_id>/update/', admin_service_type_update, name='admin_service_type_update'),
    path('barangay-admin/service-types/<int:type_id>/delete/', admin_service_type_delete, name='admin_service_type_delete'),
    
    # ==================== QR CODE SYSTEM ====================
    path('admin/generate-qr/<int:request_id>/', generate_qr_code, name='generate_qr_code'),
    path('admin/email-qr/<int:request_id>/', email_qr_code, name='email_qr_code'),
    path('verify-document/<str:token>/', verify_document, name='verify_document'),
    path('download-document/<str:token>/', download_document, name='download_document'),
    
    # ==================== PAYMENT VERIFICATION ====================
    path('barangay-admin/verify-payment/<int:request_id>/', verify_payment, name='verify_payment'),
    
    # ==================== TEST URLS (REMOVE IN PRODUCTION) ====================
    #path('test-media/', test_media, name='test_media'),
    #path('test-upload/', test_upload, name='test_upload'),
    path('barangay-admin/statistics/test/', test_pdf, name='test_pdf'),
]
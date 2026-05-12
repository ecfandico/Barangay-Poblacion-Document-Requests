"""
URL configuration for my_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""
URL configuration for my_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ORCEP import views

urlpatterns = [
    # PUT CUSTOM ADMIN URLS BEFORE the admin include
    path('admin/verify-resident/<int:profile_id>/<str:action>/', views.verify_resident, name='verify_resident'),
    path('admin/generate-qr/<int:request_id>/', views.generate_qr_code, name='generate_qr_code'),
    path('admin/email-qr/<int:request_id>/', views.email_qr_code, name='email_qr_code'),
    path('admin/clearance/<int:request_id>/', views.generate_clearance, name='generate_clearance'),  
    
    # THEN include the admin URLs
    path('admin/', admin.site.urls),
    path('', include('ORCEP.urls')),
]

# ADD MEDIA SERVING FOR DEVELOPMENT
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
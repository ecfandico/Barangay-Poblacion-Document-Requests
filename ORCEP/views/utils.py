"""
Utility views and helper functions
"""
from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings


def test_upload(request):
    """Test file upload functionality (remove in production)"""
    if request.method == 'POST':
        print("=" * 50)
        print("TEST UPLOAD DEBUG INFO:")
        print(f"Method: {request.method}")
        print(f"POST data: {dict(request.POST)}")
        print(f"FILES data keys: {list(request.FILES.keys())}")
        
        payment_proof = request.FILES.get('payment_proof')
        print(f"Payment proof: {payment_proof}")
        
        if payment_proof:
            print(f"File name: {payment_proof.name}")
            print(f"File size: {payment_proof.size}")
            
            # Save to test location
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'test_uploads'), exist_ok=True)
            
            file_path = os.path.join(settings.MEDIA_ROOT, 'test_uploads', payment_proof.name)
            with open(file_path, 'wb+') as destination:
                for chunk in payment_proof.chunks():
                    destination.write(chunk)
            
            print(f"File saved to: {file_path}")
        
        print("=" * 50)
        
        return HttpResponse("Test complete - check Django console")
    
    return render(request, 'ORCEP/test_upload.html')
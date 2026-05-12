// Payment proof image preview
document.getElementById('payment_proof').addEventListener('change', function(e) {
    const preview = document.getElementById('paymentPreview');
    const previewImage = document.getElementById('previewPaymentImage');
    const removeBtn = document.getElementById('removePaymentImage');
    
    if (this.files && this.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            preview.style.display = 'block';
        }
        
        reader.readAsDataURL(this.files[0]);
    }
});

// Remove image
document.getElementById('removePaymentImage').addEventListener('click', function() {
    const fileInput = document.getElementById('payment_proof');
    const preview = document.getElementById('paymentPreview');
    
    fileInput.value = '';
    preview.style.display = 'none';
});
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('id_photo');
    const imagePreview = document.getElementById('imagePreview');
    const previewImage = document.getElementById('previewImage');
    const removeImage = document.getElementById('removeImage');

    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            
            reader.addEventListener('load', function() {
                previewImage.src = reader.result;
                imagePreview.style.display = 'block';
            });
            
            reader.readAsDataURL(file);
        }
    });

    removeImage.addEventListener('click', function() {
        fileInput.value = '';
        imagePreview.style.display = 'none';
        previewImage.src = '#';
    });

    // Form validation for file type
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
            if (!validTypes.includes(file.type)) {
                alert('Please upload only JPG, JPEG, or PNG files.');
                this.value = '';
                imagePreview.style.display = 'none';
            }
            
            // Check file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('File size must be less than 5MB.');
                this.value = '';
                imagePreview.style.display = 'none';
            }
        }
    });
});
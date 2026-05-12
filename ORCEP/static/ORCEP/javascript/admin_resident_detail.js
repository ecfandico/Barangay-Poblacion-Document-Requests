// Show rejection reason textarea when reject button is clicked
document.addEventListener('DOMContentLoaded', function() {
        const rejectBtn = document.querySelector('button[value="reject"]');
        const rejectionReasonDiv = document.getElementById('rejectionReason');
        
        if (rejectBtn) {
            rejectBtn.addEventListener('click', function(e) {
                if (!this.disabled) {
                    rejectionReasonDiv.style.display = 'block';
                }
            });
        }
            
        // Hide rejection reason if clicking other buttons
        document.querySelectorAll('button[type="submit"]').forEach(btn => {
            if (btn.value !== 'reject') {
                btn.addEventListener('click', function() {
                    rejectionReasonDiv.style.display = 'none';
                });
            }
        });
    });
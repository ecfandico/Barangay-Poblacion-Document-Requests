// Payment verification
document.querySelectorAll('.verify-payment-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const requestId = this.dataset.requestId;
        
        if (confirm('Mark this payment as verified?')) {
            fetch(`/barangay-admin/verify-payment/${requestId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': '{{ csrf_token }}',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({verified: true})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error verifying payment');
                }
            });
        }
    });
});

// Payment verification
document.querySelectorAll('.verify-payment-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const requestId = this.dataset.requestId;
        const button = this;
        
        if (confirm('Mark this payment as verified?')) {
            // Show loading state
            button.textContent = 'Verifying...';
            button.disabled = true;
            
            fetch(`/barangay-admin/verify-payment/${requestId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({verified: true})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload the page to show updated status
                    location.reload();
                } else {
                    alert('Error verifying payment: ' + (data.error || 'Unknown error'));
                    button.textContent = '✅ Verify Payment';
                    button.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while verifying payment');
                button.textContent = '✅ Verify Payment';
                button.disabled = false;
            });
        }
    });
});

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
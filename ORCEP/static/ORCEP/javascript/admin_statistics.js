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
        
    // Delete statistics record
    document.querySelectorAll('.delete-stat-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const year = this.dataset.year;
            const month = this.dataset.month;
            const yearmonth = this.dataset.yearmonth;
                
            if (confirm(`Are you sure you want to delete statistics for ${yearmonth}?\n\nThis will only remove the statistics record. The actual service requests will remain.`)) {
                const button = this;
                button.textContent = 'Deleting...';
                button.disabled = true;
                
                fetch(`/barangay-admin/statistics/${year}/${month}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({delete: true})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload the page
                        location.reload();
                    } else {
                        alert('Error deleting statistics: ' + (data.error || 'Unknown error'));
                        button.textContent = 'Delete';
                        button.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting');
                    button.textContent = 'Delete';
                    button.disabled = false;
                });
            }
        });
    });
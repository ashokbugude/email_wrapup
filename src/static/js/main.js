window.onload = function() {
    // Check for link status message
    const linkStatus = localStorage.getItem('linkStatus');
    if (linkStatus) {
        showStatus(document.getElementById('linkStatus'), linkStatus, 'success');
        localStorage.removeItem('linkStatus');
    }
}

async function sendEmail(event) {
    event.preventDefault();
    
    const statusDiv = document.getElementById('status');
    const data = {
        provider: document.getElementById('provider').value,
        to_address: document.getElementById('toAddress').value,
        subject: document.getElementById('subject').value,
        body: document.getElementById('body').value
    };
    
    try {
        const response = await fetch('/api/send-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus(statusDiv, result.message, 'success');
            document.getElementById('emailForm').reset();
        } else {
            showStatus(statusDiv, result.error, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, 'Failed to send email', 'error');
    }
}

async function linkAccount(provider) {
    try {
        const response = await fetch('/api/auth/link-account', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                provider: provider
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            window.location.href = data.auth_url;
        } else {
            throw new Error('Failed to initiate account linking');
        }
    } catch (error) {
        showStatus(document.getElementById('linkStatus'), 'Failed to link account', 'error');
    }
}

function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
} 
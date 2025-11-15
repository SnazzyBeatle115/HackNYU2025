/**
 * Main JavaScript file for Flask ML Web App
 */

console.log("WEHFIWEHIFHWEF"); // TEST

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Flask ML Web App loaded successfully');
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Attempt to start screen capture on page load.
    (async () => {
        try {
            await startScreenCapture();
            showNotification('Screen capture started', 'info');
        } catch (err) {
            console.warn('Screen capture start blocked or failed:', err);
            showNotification('Screen capture could not be started automatically. Please click to start.', 'error');
        }
    })();

});

async function startScreenCapture() {
    const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true
    });

    const videoEl = document.createElement("video");
    videoEl.srcObject = stream;
    await videoEl.play();

    // Periodic screenshot
    setInterval(() => captureScreenshot(videoEl), 2000);
}

function captureScreenshot(videoEl) {
    const canvas = document.createElement("canvas");
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0);

    const base64 = canvas.toDataURL("image/jpeg", 0.7); // compressed

    sendScreenshot(base64);
}


async function sendScreenshot(base64Image) {
    try {
        const responseJson = await apiCall('/api/screen', 'POST', {
            screen: base64Image
        });
        console.log('Prediction response:', responseJson);
        // showNotification(`Prediction: ${responseJson.prediction}`, 'info');
    } catch (error) {
        // showNotification('Failed to get prediction from server.', 'error');
        console.error('Error sending screenshot:', error);
    }
}


/**
 * Helper function to make API calls
 */
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? '#f8d7da' : '#d4edda'};
        border: 1px solid ${type === 'error' ? '#f5c6cb' : '#c3e6cb'};
        color: ${type === 'error' ? '#721c24' : '#155724'};
        border-radius: 4px;
        z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

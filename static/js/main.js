/**
 * Main JavaScript file for Flask ML Web App
 */


const TIME_INTERVAL_SCREEN_CAPTURE = 20000;
const TIME_INTERVAL_CAMERA_CAPTURE = 20000;

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

    // Attempt to start camera capture on page load.
    (async () => {
        try {
            await startCameraCapture();
            showNotification('Camera capture started', 'info');
        } catch (err) {
            console.warn('Camera capture start blocked or failed:', err);
            showNotification('Camera capture could not be started automatically. Please allow camera access.', 'error');
        }
    })();

    // handle record button press
    document.querySelector(".character-img").addEventListener("click", () => {
        E
    });

});

async function startScreenCapture() {
    const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true
    });

    const videoEl = document.createElement("video");
    videoEl.srcObject = stream;
    await videoEl.play();

    // Periodic screenshot
    setInterval(() => captureScreenshot(videoEl), TIME_INTERVAL_SCREEN_CAPTURE);
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

async function startCameraCapture() {
    const stream = await navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: 'user' // Use front-facing camera by default
        }
    });

    const videoEl = document.createElement("video");
    videoEl.srcObject = stream;
    videoEl.autoplay = true;
    videoEl.playsInline = true;
    await videoEl.play();

    // Optional: Add video element to page for preview (you can remove this if not needed)
    videoEl.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        width: 200px;
        height: 150px;
        border: 2px solid #333;
        border-radius: 8px;
        z-index: 1000;
        object-fit: cover;
    `;
    document.body.appendChild(videoEl);

    // Capture picture every 2 seconds
    setInterval(() => captureCameraPicture(videoEl), TIME_INTERVAL_CAMERA_CAPTURE);
}

function captureCameraPicture(videoEl) {
    if (videoEl.readyState !== videoEl.HAVE_ENOUGH_DATA) {
        console.warn('Video not ready for capture');
        return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0);

    const base64 = canvas.toDataURL("image/jpeg", 0.7); // compressed

    sendCameraPicture(base64);
}

async function sendCameraPicture(base64Image) {
    try {
        const responseJson = await apiCall('/api/camera', 'POST', {
            camera: base64Image
        });
        console.log('Camera picture response:', responseJson);
        // showNotification(`Camera picture captured`, 'info');
    } catch (error) {
        // showNotification('Failed to send camera picture to server.', 'error');
        console.error('Error sending camera picture:', error);
    }
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
        
        // Check if response is ok
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch {
                errorData = { message: errorText || `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(errorData.message || errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Try to parse as JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const result = await response.json();
            return result;
        } else {
            // If not JSON, return text
            const text = await response.text();
            return { response: text };
        }
    } catch (error) {
        console.error('API call failed:', error);
        // Provide more detailed error information
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            console.error('Network error - check if server is running and CORS is configured');
            throw new Error('Network error: Could not connect to server. Make sure the Flask server is running.');
        }
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

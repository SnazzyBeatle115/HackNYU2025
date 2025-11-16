/**
 * Main JavaScript file for Flask ML Web App
 */

// Capture intervals are set from environment variables via template
// These will be defined in the template script block before this file loads
// Fallback values if not defined
const TIME_INTERVAL_SCREEN_CAPTURE = window.TIME_INTERVAL_SCREEN_CAPTURE || 2000;
const TIME_INTERVAL_CAMERA_CAPTURE = window.TIME_INTERVAL_CAMERA_CAPTURE || 2000;

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

    // Set up chat input handler
    setupChatInput();

    // Initialize dialogue element visibility
    // Note: The dialogue will be shown when typing starts and hidden when cleared
    // handle record button press
    document.querySelector(".character-img").addEventListener("click", () => {
        console.log("Record button pressed");
    });

    // Initialize coin display and sync with farm
    initializeCoinDisplay();

});

/**
 * Initialize and sync coin display with farm page
 */
function initializeCoinDisplay() {
    const coinElement = document.getElementById('mainCoins');
    if (!coinElement) return;
    
    // Load coins from localStorage (same storage as farm page)
    function updateCoinDisplay() {
        const saved = localStorage.getItem('farmState');
        if (saved) {
            try {
                const state = JSON.parse(saved);
                const coins = state.coins || 1000;
                coinElement.textContent = coins;
            } catch (e) {
                console.error('Error loading coins:', e);
                coinElement.textContent = 1000;
            }
        } else {
            coinElement.textContent = 1000;
        }
    }
    
    // Update on page load
    updateCoinDisplay();
    
    // Listen for storage changes (when farm page updates coins in other tabs/windows)
    window.addEventListener('storage', (e) => {
        if (e.key === 'farmState') {
            updateCoinDisplay();
        }
    });
    
    // Update when page becomes visible (user returns from farm page)
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            updateCoinDisplay();
        }
    });
    
    // Also check periodically to sync with farm page
    setInterval(() => {
        updateCoinDisplay();
    }, 1000); // Check every second
}

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
 * Set up chat input functionality
 */
function setupChatInput() {
    const inputField = document.querySelector('.input-text');
    const submitButton = document.querySelector('.submit-btn');
    const chatLog = document.querySelector('.log');
    
    if (!inputField || !submitButton) {
        console.warn('Chat input elements not found');
        return;
    }
    
    // Function to send message
    const sendMessage = async () => {
        const text = inputField.value.trim();
        
        if (!text) {
            return; // Don't send empty messages
        }
        
        // Add user message to chat log
        addMessageToChat(chatLog, `You: ${text}`, 'user');
        
        // Clear input field
        inputField.value = '';
        
        // Disable input while processing
        inputField.disabled = true;
        submitButton.disabled = true;
        
        try {
            // Send to backend
            const response = await apiCall('/api/text', 'POST', {
                text: text
            });
            
            // Add bot response to chat log
            const botMessage = response?.response || response?.message || JSON.stringify(response);
            addMessageToChat(chatLog, `Bot: ${botMessage}`, 'bot');
            
            // Show typing animation in dialogue element
            const dialogueElement = document.querySelector('.dialogue');
            if (dialogueElement) {
                typeText(dialogueElement, botMessage, response?.audio);
            }
            
            // Handle timer if present in response
            if (response?.time) {
                startTimer(response.time);
            }
            
            // Scroll to bottom of chat log
            chatLog.scrollTop = chatLog.scrollHeight;
            
        } catch (error) {
            console.error('Error sending message:', error);
            addMessageToChat(chatLog, `Bot: Error - ${error.message}`, 'error');
        } finally {
            // Re-enable input
            inputField.disabled = false;
            submitButton.disabled = false;
            inputField.focus();
        }
    };
    
    // Handle submit button click
    submitButton.addEventListener('click', sendMessage);
    
    // Handle Enter key press
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
}

/**
 * Add a message to the chat log
 */
function addMessageToChat(chatLog, message, type = 'user') {
    if (!chatLog) return;
    
    const messageElement = document.createElement('p');
    messageElement.textContent = message;
    
    // Add styling based on message type
    if (type === 'user') {
        messageElement.style.color = '#007bff';
        messageElement.style.fontWeight = '500';
    } else if (type === 'error') {
        messageElement.style.color = '#dc3545';
    } else {
        messageElement.style.color = '#28a745';
    }
    
    chatLog.appendChild(messageElement);
}

/**
 * Type text with animation in the dialogue element
 * @param {HTMLElement} element - The dialogue element to update
 * @param {string} text - The text to type
 * @param {Object} audioData - Optional audio data to play
 */
function typeText(element, text, audioData = null) {
    // Clear any existing typing animation
    if (element.typingAnimation) {
        clearInterval(element.typingAnimation);
        element.typingAnimation = null;
    }
    
    // Show the dialogue element
    element.style.display = 'block';
    element.style.opacity = '1';
    element.style.transition = '';
    
    // Clear the element
    element.textContent = '';
    
    let currentIndex = 0;
    const typingSpeed = 30; // milliseconds per character
    
    // Start audio immediately (at the same time as typing)
    let audio = null;
    if (audioData) {
        audio = playAudio(audioData);
        if (audio) {
            // Clear dialogue when audio finishes
            audio.onended = () => {
                console.log('Audio playback finished');
                // Fade out and clear dialogue
                fadeOutDialogue(element);
            };
        }
    }
    
    // Start typing animation
    element.typingAnimation = setInterval(() => {
        if (currentIndex < text.length) {
            element.textContent = text.substring(0, currentIndex + 1);
            currentIndex++;
        } else {
            // Typing complete
            clearInterval(element.typingAnimation);
            element.typingAnimation = null;
            
            // If no audio was available, clear after a delay
            if (!audio) {
                setTimeout(() => fadeOutDialogue(element), 2000);
            }
            // If audio is playing, it will handle clearing when it finishes
        }
    }, typingSpeed);
}

/**
 * Fade out and clear the dialogue element, then hide it
 */
function fadeOutDialogue(element) {
    if (!element) return;
    
    // Add fade out animation
    element.style.transition = 'opacity 0.5s ease-out';
    element.style.opacity = '0';
    
    // Clear text and hide element after fade
    setTimeout(() => {
        element.textContent = '';
        element.style.display = 'none'; // Hide the element
        element.style.opacity = '1'; // Reset for next time
        element.style.transition = '';
    }, 500);
}

/**
 * Play audio from response
 * Expects audio data in the format from api_server.py:
 * {
 *   "data": "base64_encoded_audio_string",
 *   "format": "mp3",
 *   "data_url": "data:audio/mpeg;base64,..."
 * }
 * @returns {HTMLAudioElement|null} The audio element if created, null otherwise
 */
function playAudio(audioData) {
    try {
        let audioUrl = null;
        
        // Prefer data_url if available (already formatted correctly)
        if (audioData.data_url) {
            audioUrl = audioData.data_url;
        } 
        // Otherwise, construct data URL from base64 data and format
        else if (audioData.data && audioData.format) {
            // Format: data:audio/{format};base64,{base64_data}
            const mimeType = audioData.format === 'mp3' ? 'mpeg' : audioData.format;
            audioUrl = `data:audio/${mimeType};base64,${audioData.data}`;
        }
        // Fallback: try to use data directly (might already be a data URL)
        else if (audioData.data) {
            audioUrl = audioData.data;
        }
        
        if (!audioUrl) {
            console.warn('No audio data found in response:', audioData);
            return null;
        }
        
        console.log('Playing audio with format:', audioData.format || 'unknown');
        
        // Create audio element
        const audio = new Audio(audioUrl);
        
        // Handle audio events
        audio.onloadstart = () => {
            console.log('Audio loading started');
        };
        
        audio.oncanplay = () => {
            console.log('Audio ready to play');
        };
        
        audio.onerror = (error) => {
            console.error('Error playing audio:', error);
        };
        
        // Play the audio
        audio.play().catch(error => {
            console.error('Failed to play audio:', error);
            // Some browsers require user interaction before playing audio
            // This is expected behavior for autoplay policies
        });
        
        return audio;
        
    } catch (error) {
        console.error('Error processing audio:', error);
        return null;
    }
}

/**
 * Start a countdown timer
 * @param {string} timeString - Time in MM:SS format (e.g., "05:00", "00:30")
 */
function startTimer(timeString) {
    // Clear any existing timer
    if (window.timerInterval) {
        clearInterval(window.timerInterval);
        window.timerInterval = null;
    }
    
    // Parse MM:SS format
    const parts = timeString.split(':');
    if (parts.length !== 2) {
        console.error('Invalid time format. Expected MM:SS, got:', timeString);
        return;
    }
    
    let totalSeconds = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    
    if (isNaN(totalSeconds) || totalSeconds <= 0) {
        console.error('Invalid time value:', timeString);
        return;
    }
    
    // Get timer display element
    const timerElement = document.querySelector('.timer p');
    if (!timerElement) {
        console.warn('Timer display element not found');
        return;
    }
    
    // Update timer display immediately
    const updateDisplay = () => {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        const displayTime = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        timerElement.textContent = displayTime;
    };
    
    updateDisplay();
    
    // Start countdown
    window.timerInterval = setInterval(() => {
        totalSeconds--;
        
        if (totalSeconds < 0) {
            // Timer completed
            clearInterval(window.timerInterval);
            window.timerInterval = null;
            timerElement.textContent = '00:00';
            
            // Show completion notification
            showNotification('Timer completed!', 'info');
            
            // Optional: Play a sound or trigger an event
            console.log('Timer completed!');
        } else {
            updateDisplay();
        }
    }, 1000); // Update every second
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

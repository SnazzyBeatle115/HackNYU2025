/**
 * Main JavaScript file for Flask ML Web App
 */

// Capture intervals are set from environment variables via template
// These will be defined in the template script block before this file loads
// Fallback values if not defined
const TIME_INTERVAL_SCREEN_CAPTURE = globalThis.TIME_INTERVAL_SCREEN_CAPTURE || 2000;
const TIME_INTERVAL_CAMERA_CAPTURE = globalThis.TIME_INTERVAL_CAMERA_CAPTURE || 2000;

// Audio recording state
let isListening = false;
let mediaRecorder = null;
let audioContext = null;
let analyserNode = null;
let mediaStreamSource = null;
let audioStream = null;

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
    
    // Handle record button press
    const recordButton = document.querySelector(".character-img");
    if (recordButton) {
        recordButton.addEventListener("click", toggleAudioRecording);
    }

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
 * Toggle audio recording on/off
 */
async function toggleAudioRecording() {
    if (isListening) {
        stopAudioRecording();
    } else {
        await startAudioRecording();
    }
}

/**
 * Start audio recording with speech detection
 */
async function startAudioRecording() {
    try {
        // Request microphone access
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Microphone access granted');
        
        // Create MediaRecorder for audio/webm format
        const options = { mimeType: 'audio/webm' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            // Fallback to default if webm not supported
            console.warn('audio/webm not supported, using default format');
            mediaRecorder = new MediaRecorder(audioStream);
        } else {
            mediaRecorder = new MediaRecorder(audioStream, options);
        }
        
        // Create AudioContext for audio analysis
        const AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext;
        audioContext = new AudioContextClass();
        mediaStreamSource = audioContext.createMediaStreamSource(audioStream);
        analyserNode = audioContext.createAnalyser();
        analyserNode.fftSize = 2048;
        mediaStreamSource.connect(analyserNode);
        
        // Set up chunk handling
        mediaRecorder.ondataavailable = async (event) => {
            if (event.data && event.data.size > 0) {
                await handleAudioChunk(event.data);
            }
        };
        
        // Start recording with 1000ms chunks
        mediaRecorder.start(1000);
        isListening = true;
        
        console.log('Audio recording started');
        showNotification('Recording started', 'info');
        
    } catch (error) {
        console.error('Error starting audio recording:', error);
        showNotification('Failed to start recording: ' + error.message, 'error');
    }
}

/**
 * Stop audio recording
 */
function stopAudioRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    
    if (audioStream) {
        for (const track of audioStream.getTracks()) {
            track.stop();
        }
        audioStream = null;
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    mediaRecorder = null;
    analyserNode = null;
    mediaStreamSource = null;
    isListening = false;
    
    console.log('Audio recording stopped');
    showNotification('Recording stopped', 'info');
}

/**
 * Calculate RMS (Root Mean Square) volume from audio buffer
 * @param {Float32Array} audioData - Audio buffer data
 * @returns {number} RMS volume value
 */
function calculateRMS(audioData) {
    let sum = 0;
    for (const sample of audioData) {
        sum += sample * sample;
    }
    return Math.sqrt(sum / audioData.length);
}

/**
 * Check if audio chunk contains speech based on RMS volume
 * @returns {boolean} True if speech is detected
 */
function hasSpeech() {
    if (!analyserNode) {
        return false;
    }
    
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);
    analyserNode.getFloatTimeDomainData(dataArray);
    
    const rms = calculateRMS(dataArray);
    // Threshold for speech detection (adjust as needed)
    // Typical speech RMS is above 0.01, silence is below 0.001
    const speechThreshold = 0.01;
    
    const detected = rms > speechThreshold;
    if (detected) {
        console.log(`Speech detected - RMS: ${rms.toFixed(4)}`);
    }
    
    return detected;
}

/**
 * Handle audio chunk - upload if conditions are met
 * @param {Blob} audioBlob - Audio chunk data
 */
async function handleAudioChunk(audioBlob) {
    // Only upload if listening is active
    if (!isListening) {
        console.log('Skipping chunk - not in listening mode');
        return;
    }
    
    // Check if chunk contains speech
    const containsSpeech = hasSpeech();
    
    if (!containsSpeech) {
        console.log('Skipping chunk - no speech detected');
        return;
    }
    
    console.log('Uploading audio chunk with speech (size:', audioBlob.size, 'bytes)');
    
    try {
        // Convert blob to base64 for sending
        const base64Audio = await blobToBase64(audioBlob);
        
        // Send to backend
        await sendAudioChunk(base64Audio, audioBlob.type);
        
    } catch (error) {
        console.error('Error handling audio chunk:', error);
    }
}

/**
 * Convert Blob to base64 string
 * @param {Blob} blob - Blob to convert
 * @returns {Promise<string>} Base64 string
 */
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64String = reader.result.split(',')[1]; // Remove data URL prefix
            resolve(base64String);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

/**
 * Send audio chunk to backend as base64
 * @param {string} base64Audio - Base64 encoded audio data
 * @param {string} mimeType - MIME type of the audio
 */
async function sendAudioChunk(base64Audio, mimeType) {
    try {
        // Send base64 audio as JSON to /audioin endpoint
        const response = await fetch('/audioin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                audio: base64Audio,
                format: mimeType
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Audio chunk sent successfully:', result);
        
    } catch (error) {
        console.error('Error sending audio chunk:', error);
    }
}

/**
 * Convert base64 string to Blob
 * @param {string} base64 - Base64 encoded string
 * @param {string} mimeType - MIME type
 * @returns {Blob} Blob object
 */
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
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

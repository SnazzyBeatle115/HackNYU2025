/**
 * Main JavaScript file for Flask ML Web App
 */

// Capture intervals are set from environment variables via template
// These will be defined in the template script block before this file loads
// Fallback values if not defined
const TIME_INTERVAL_SCREEN_CAPTURE = globalThis.TIME_INTERVAL_SCREEN_CAPTURE || 2000;
const TIME_INTERVAL_CAMERA_CAPTURE = globalThis.TIME_INTERVAL_CAMERA_CAPTURE || 2000;

// Global study reminder cooldown (applies to screen + camera)
const STUDY_REMINDER_COOLDOWN_MS = 60_000; // 1 minute
let lastStudyReminderTs = 0;

// Audio recording state (session-based model)
let isListening = false;
let currentMediaRecorder = null;
let currentAudioChunks = [];
let currentAudioStream = null;
let audioAnalyser = null;
let audioContext = null;
let audioMonitorInterval = null;
let recordingEnabled = false; // Master flag controlling recording behavior
let lastToggleTs = 0;       // Debounce toggle clicks

function isRecordingActive() {
    return !!(currentMediaRecorder && currentMediaRecorder.state && currentMediaRecorder.state !== 'inactive');
}

// Adaptive speech control configuration
const SPEECH_RMS_THRESHOLD = 0.01;        // Minimum RMS to treat as speech
const SILENCE_MS_BEFORE_STOP = 1200;       // Stop after this long below threshold
const MIN_RECORDING_MS = 500;              // Ignore recordings shorter than this
const MAX_RECORDING_MS = 30000;            // Safety cap (30s) to avoid endless capture
let lastAboveThresholdTime = 0;
let recordingStartTime = 0;

// Screen capture state
let screenCaptureActive = false;
let screenVideoElement = null;
let screenCaptureInterval = null;
let screenStream = null;

// Camera capture state
let cameraCaptureActive = false;
let cameraVideoElement = null;
let cameraCaptureInterval = null;
let cameraStream = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Flask ML Web App loaded successfully');
    // Log configured and effective capture intervals at startup
    console.log('[Config] Raw intervals from template:', {
        TIME_INTERVAL_SCREEN_CAPTURE_raw: globalThis.TIME_INTERVAL_SCREEN_CAPTURE,
        TIME_INTERVAL_CAMERA_CAPTURE_raw: globalThis.TIME_INTERVAL_CAMERA_CAPTURE
    });
    console.log('[Config] Effective intervals (ms):', {
        TIME_INTERVAL_SCREEN_CAPTURE,
        TIME_INTERVAL_CAMERA_CAPTURE
    });

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

    // Set up screen capture button
    const screenButton = document.querySelector(".screen-btn");
    if (screenButton) {
        console.log('Binding direct handler for .screen-btn');
        screenButton.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Screen capture button clicked (direct)');
            // Start/stop screen capture and camera capture
            toggleScreenCapture();
            toggleCameraCapture();
        });

    }

    // Delegated handler as a fallback in case element is re-rendered
    document.addEventListener('click', (e) => {
        const btn = e.target && e.target.closest && e.target.closest('.screen-btn');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Screen capture button clicked (delegated)');
            toggleScreenCapture();
            toggleCameraCapture();
        }
    });

    // // Set up camera capture button
    // const cameraButton = document.querySelector(".camera-btn");
    // if (cameraButton) {
    //     cameraButton.addEventListener("click", toggleCameraCapture);
    // }

    // Set up chat input handler
    setupChatInput();

    // Initialize dialogue element visibility
    // Note: The dialogue will be shown when typing starts and hidden when cleared

    // Handle record button press
    const recordButton = document.querySelector(".character-img");
    if (recordButton) {
        recordButton.addEventListener("click", () => {
            toggleAudioRecording();
            // toggleCameraCapture();
            // toggleScreenCapture();
        });
    }

});

/**
 * Toggle screen capture on/off
 */
async function toggleScreenCapture() {
    if (screenCaptureActive) {
        stopScreenCapture();
    } else {
        await startScreenCapture();
    }
}

/**
 * Start screen capture
 */
async function startScreenCapture() {
    try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: true
        });

        screenVideoElement = document.createElement("video");
        screenVideoElement.srcObject = screenStream;
        await screenVideoElement.play();

        // Wait until metadata is loaded so videoWidth/Height are available
        if (!screenVideoElement.videoWidth || !screenVideoElement.videoHeight) {
            await new Promise((resolve) => {
                const done = () => resolve();
                screenVideoElement.onloadedmetadata = done;
                // Fallback: resolve after a short timeout if event doesn't fire
                setTimeout(done, 500);
            });
        }

        // Clear any existing interval then start periodic screenshot
        if (screenCaptureInterval) clearInterval(screenCaptureInterval);
        const intervalMs = Number(globalThis.TIME_INTERVAL_SCREEN_CAPTURE) || TIME_INTERVAL_SCREEN_CAPTURE || 2000;
        screenCaptureInterval = setInterval(() => captureScreenshot(screenVideoElement), intervalMs);
        screenCaptureActive = true;

        console.log('Screen capture started');
        showNotification('Screen capture started', 'info');
    } catch (error) {
        console.error('Error starting screen capture:', error);
        showNotification('Failed to start screen capture: ' + error.message, 'error');
    }
}

/**
 * Stop screen capture
 */
function stopScreenCapture() {
    if (screenCaptureInterval) {
        clearInterval(screenCaptureInterval);
        screenCaptureInterval = null;
    }

    if (screenStream) {
        for (const track of screenStream.getTracks()) {
            track.stop();
        }
        screenStream = null;
    }

    if (screenVideoElement) {
        screenVideoElement.srcObject = null;
        screenVideoElement = null;
    }

    screenCaptureActive = false;
    console.log('Screen capture stopped');
    showNotification('Screen capture stopped', 'info');
}

function captureScreenshot(videoEl) {
    // Guard against unready video frames
    if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) {
        console.warn('Skipping capture: video not ready');
        return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0);

    const base64 = canvas.toDataURL("image/jpeg", 0.7); // compressed

    // Debug: log size of payload being sent
    try {
        const len = (base64 && base64.length) || 0;
        console.log('Sending screenshot (base64 length):', len);
    } catch { }

    sendScreenshot(base64);
}

/**
 * Toggle camera capture on/off
 */
async function toggleCameraCapture() {
    if (cameraCaptureActive) {
        stopCameraCapture();
    } else {
        await startCameraCapture();
    }
}

/**
 * Start camera capture
 */
async function startCameraCapture() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user' // Use front-facing camera by default
            }
        });

        cameraVideoElement = document.createElement("video");
        cameraVideoElement.srcObject = cameraStream;
        cameraVideoElement.autoplay = true;
        cameraVideoElement.playsInline = true;
        await cameraVideoElement.play();

        // Optional: Add video element to page for preview (you can remove this if not needed)
        cameraVideoElement.style.cssText = `
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
        document.body.appendChild(cameraVideoElement);

        // Capture picture every 2 seconds
        cameraCaptureInterval = setInterval(() => captureCameraPicture(cameraVideoElement), TIME_INTERVAL_CAMERA_CAPTURE);
        cameraCaptureActive = true;

        console.log('Camera capture started');
        showNotification('Camera capture started', 'info');
    } catch (error) {
        console.error('Error starting camera capture:', error);
        showNotification('Failed to start camera capture: ' + error.message, 'error');
    }
}

/**
 * Stop camera capture
 */
function stopCameraCapture() {
    if (cameraCaptureInterval) {
        clearInterval(cameraCaptureInterval);
        cameraCaptureInterval = null;
    }

    if (cameraStream) {
        for (const track of cameraStream.getTracks()) {
            track.stop();
        }
        cameraStream = null;
    }

    if (cameraVideoElement) {
        cameraVideoElement.remove();
        cameraVideoElement = null;
    }

    cameraCaptureActive = false;
    console.log('Camera capture stopped');
    showNotification('Camera capture stopped', 'info');
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

        // Check if user is not studying and send friendly reminder
        if (responseJson?.is_studying === false) {
            await sendStudyReminder('camera', responseJson?.activity_detected);
        }
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

        // Check if user is not studying and send friendly reminder
        if (responseJson?.is_studying === false) {
            await sendStudyReminder('screen', responseJson?.activity_detected);
        }
    } catch (error) {
        // showNotification('Failed to get prediction from server.', 'error');
        console.error('Error sending screenshot:', error);
    }
}

/**
 * Send friendly reminder to get back on task when is_studying is false
 * @param {string} source - Source of the detection ('screen' or 'camera')
 * @param {string} activityDetected - Description of what the user is doing instead of studying
 */
async function sendStudyReminder(source, activityDetected) {
    try {
        // Throttle reminders globally across screen + camera
        const now = Date.now();
        const elapsed = now - lastStudyReminderTs;
        if (elapsed < STUDY_REMINDER_COOLDOWN_MS) {
            const remaining = Math.ceil((STUDY_REMINDER_COOLDOWN_MS - elapsed) / 1000);
            console.log(`Skipping reminder (cooldown active, ${remaining}s left)`);
            return;
        }
        // Set timestamp early to avoid burst duplicates
        lastStudyReminderTs = now;

        const chatLog = document.querySelector('.log');
        if (!chatLog) {
            console.warn('Chat log element not found');
            return;
        }

        console.log(`User not studying detected from ${source}, sending reminder`);
        console.log(`Activity detected: ${activityDetected}`);

        // Build message with activity context
        let messageText = "I noticed I'm not studying.";
        if (activityDetected) {
            messageText += ` I'm currently: ${activityDetected}.`;
        }
        messageText += " Give me a friendly reminder to get back on task.";

        // Send reminder message to chat endpoint
        const response = await apiCall('/api/text', 'POST', {
            text: messageText
        });

        // Add bot response to chat log
        const botMessage = response?.response || response?.message || JSON.stringify(response);
        console.log('Study reminder response:', botMessage);
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
        console.error('Error sending study reminder:', error);
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
            console.log('Bot text response:', botMessage);
            console.log('Full response object:', response);
            console.log('Timer field (response.time):', response?.time);
            console.log('Timer field exists?', 'time' in response);
            addMessageToChat(chatLog, `Bot: ${botMessage}`, 'bot');

            // Show typing animation in dialogue element
            const dialogueElement = document.querySelector('.dialogue');
            if (dialogueElement) {
                typeText(dialogueElement, botMessage, response?.audio);
            }

            // Handle timer if present in response
            if (response?.time) {
                console.log('Starting timer with time:', response.time);
                startTimer(response.time);
            } else {
                console.log('No timer field found in response');
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
        // Stop recording while audio is playing
        const wasListening = isListening;
        if (wasListening) {
            stopListeningWindow();
            console.log('Paused recording for audio playback');
        }

        audio = playAudio(audioData);
        if (audio) {
            // Clear dialogue and resume recording when audio finishes
            audio.onended = () => {
                console.log('Audio playback finished');
                // Fade out and clear dialogue
                fadeOutDialogue(element);

                // Resume recording only if master flag is enabled
                if (recordingEnabled) {
                    setTimeout(() => {
                        startAdaptiveRecording();
                        console.log('Resumed recording after audio playback');
                    }, 500); // Small delay after audio ends
                } else {
                    console.log('Not resuming recording (recordingEnabled:', recordingEnabled, ')');
                }
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

        // Stop recording before playing audio
        audio.onplay = () => {
            console.log('Audio playback started');
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
 * Extract timer duration from response text
 * @param {string} text - Response text that may contain timer info
 * @returns {string|null} Time in MM:SS format or null
 */
function extractTimerFromResponse(text) {
    if (!text) return null;

    // Pattern to match time mentions like "10 minute", "5 minutes", "30 seconds"
    const patterns = [
        /(\d+)\s*(?:minute|min)s?/i,
        /(\d+)\s*(?:second|sec)s?/i,
        /(\d+)\s*(?:hour|hr)s?/i
    ];

    let totalSeconds = 0;

    // Check for minutes
    const minMatch = text.match(/(\d+)\s*(?:minute|min)s?/i);
    if (minMatch) {
        totalSeconds += parseInt(minMatch[1]) * 60;
    }

    // Check for hours
    const hourMatch = text.match(/(\d+)\s*(?:hour|hr)s?/i);
    if (hourMatch) {
        totalSeconds += parseInt(hourMatch[1]) * 3600;
    }

    // Check for seconds (only if no minutes/hours found)
    if (totalSeconds === 0) {
        const secMatch = text.match(/(\d+)\s*(?:second|sec)s?/i);
        if (secMatch) {
            totalSeconds = parseInt(secMatch[1]);
        }
    }

    if (totalSeconds === 0) return null;

    // Convert to MM:SS
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * Start a countdown timer
 * @param {string} timeString - Time in MM:SS or HH:MM:SS format (e.g., "05:00", "00:30", "01:30:00")
 */
function startTimer(timeString) {
    // Clear any existing timer
    if (window.timerInterval) {
        clearInterval(window.timerInterval);
        window.timerInterval = null;
    }

    // Parse MM:SS or HH:MM:SS format
    const parts = timeString.split(':');
    let totalSeconds = 0;

    if (parts.length === 3) {
        // HH:MM:SS format
        totalSeconds = parseInt(parts[0], 10) * 3600 + parseInt(parts[1], 10) * 60 + parseInt(parts[2], 10);
    } else if (parts.length === 2) {
        // MM:SS format
        totalSeconds = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    } else {
        console.error('Invalid time format. Expected MM:SS or HH:MM:SS, got:', timeString);
        return;
    }

    if (isNaN(totalSeconds) || totalSeconds <= 0) {
        console.error('Invalid time value:', timeString);
        return;
    }

    // Get timer container and display element
    const timerContainer = document.querySelector('.timer');
    const timerElement = document.querySelector('.timer p');
    if (!timerElement) {
        console.warn('Timer display element not found');
        return;
    }

    // Show timer when starting
    if (timerContainer) {
        timerContainer.style.display = 'block';
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
    window.timerInterval = setInterval(async () => {
        totalSeconds--;

        if (totalSeconds < 0) {
            // Timer completed
            clearInterval(window.timerInterval);
            window.timerInterval = null;
            timerElement.textContent = '00:00';

            // Show completion notification
            showNotification('Timer completed!', 'info');

            // Hide timer after completion
            if (timerContainer) {
                timerContainer.style.display = 'none';
            }

            // Optional: Play a sound or trigger an event
            console.log('Timer completed!');

            const chatLog = document.querySelector('.log');
            if (!chatLog) {
                console.warn('Chat log element not found');
                return;
            }

            // timer ran out
            const response = await apiCall('/api/text', 'POST', {
                text: "The timer has run out!"
            });

            // Add bot response to chat log
            const botMessage = response?.response || response?.message || JSON.stringify(response);
            console.log('Bot text response:', botMessage);
            console.log('Full response object:', response);
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


        } else {
            updateDisplay();
        }
    }, 1000); // Update every second
}

/**
 * Toggle audio recording on/off
 * Now uses session-based recording (one complete WebM file per window)
 */
async function toggleAudioRecording() {
    // Debounce rapid double clicks
    const now = Date.now();
    if (now - lastToggleTs < 300) {
        console.log('Toggle ignored (debounced)');
        return;
    }
    lastToggleTs = now;

    // Flip master control
    recordingEnabled = !recordingEnabled;

    if (!recordingEnabled) {
        // Disable and stop any active recording
        if (isListening || isRecordingActive()) {
            isListening = false; // prevent re-entrancy
            stopAdaptiveRecording();
        }
        console.log('Recording disabled');
        return;
    }

    // Enabled: start if not already active
    if (!isRecordingActive() && !isListening) {
        await startAdaptiveRecording();
    } else {
        console.log('Recording already active (enabled)');
    }
}

/**
 * Start a listening window - records one complete audio session
 * @param {number} durationMs - Duration of the listening window in milliseconds (default 6000)
 */
async function startListeningWindow(durationMs = 6000) {
    try {
        console.log('Audio listening window started for', durationMs, 'ms');
        showNotification('Recording started', 'info');

        // Request microphone access
        currentAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        currentAudioChunks = [];

        // Create MediaRecorder for audio/webm format
        const options = { mimeType: 'audio/webm' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            console.warn('audio/webm not supported, using default format');
            currentMediaRecorder = new MediaRecorder(currentAudioStream);
        } else {
            currentMediaRecorder = new MediaRecorder(currentAudioStream, options);
        }

        // Accumulate all data chunks
        currentMediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                currentAudioChunks.push(event.data);
            }
        };

        // Handle recording stop - upload complete audio file
        currentMediaRecorder.onstop = async () => {
            try {
                const blob = new Blob(currentAudioChunks, { type: 'audio/webm' });
                console.log('Audio listening window stopped, blob size:', blob.size);

                // Basic guard: ignore extremely tiny blobs
                if (blob.size < 2000) {
                    console.log('Ignoring tiny audio blob');
                    return;
                }

                const base64 = await blobToBase64WithoutPrefix(blob);
                console.log('Uploading full audio clip to /api/voice, size:', blob.size);

                await sendAudioToBackend(base64, 'audio/webm');
            } catch (err) {
                console.error('Error handling recorded audio:', err);
                showNotification('Failed to process audio: ' + err.message, 'error');
            } finally {
                // Stop tracks so mic is released
                if (currentAudioStream) {
                    currentAudioStream.getTracks().forEach((track) => track.stop());
                    currentAudioStream = null;
                }
                isListening = false;
                showNotification('Recording stopped', 'info');
            }
        };

        // Start recording (no timeslice - record continuously)
        currentMediaRecorder.start();
        isListening = true;

        // Automatically stop after duration
        setTimeout(() => {
            if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
                currentMediaRecorder.stop();
            }
        }, durationMs);

    } catch (error) {
        console.error('Error starting listening window:', error);
        showNotification('Failed to start recording: ' + error.message, 'error');
        isListening = false;
    }
}

/**
 * Stop the current listening window
 */
function stopListeningWindow() {
    if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
        currentMediaRecorder.stop();
        console.log('Manually stopping listening window');
    }
}

/**
 * Start adaptive recording: captures while RMS above threshold, stops after silence.
 */
async function startAdaptiveRecording() {
    try {
        // Respect master control flag
        if (!recordingEnabled) {
            console.log('Recording disabled; start ignored');
            return;
        }
        // Prevent starting if already active
        if (isListening || isRecordingActive()) {
            console.log('Recording already active; start ignored');
            return;
        }

        console.log('Adaptive audio recording started');
        showNotification('Listening...', 'info');
        currentAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        currentAudioChunks = [];
        const options = { mimeType: 'audio/webm' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            console.warn('audio/webm not supported, using default');
            currentMediaRecorder = new MediaRecorder(currentAudioStream);
        } else {
            currentMediaRecorder = new MediaRecorder(currentAudioStream, options);
        }

        // Setup audio context & analyser for RMS
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const srcNode = audioContext.createMediaStreamSource(currentAudioStream);
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 2048;
        srcNode.connect(audioAnalyser);

        lastAboveThresholdTime = Date.now();
        recordingStartTime = Date.now();

        currentMediaRecorder.ondataavailable = e => {
            if (e.data && e.data.size > 0) {
                currentAudioChunks.push(e.data);
            }
        };

        currentMediaRecorder.onstop = async () => {
            cleanupAudioMonitoring();
            try {
                const elapsed = Date.now() - recordingStartTime;
                const blob = new Blob(currentAudioChunks, { type: 'audio/webm' });
                console.log('Adaptive recording stopped; duration:', elapsed, 'ms; blob size:', blob.size);
                if (elapsed < MIN_RECORDING_MS || blob.size < 2000) {
                    console.log('Ignoring too-short / tiny recording');
                    return;
                }
                const base64 = await blobToBase64WithoutPrefix(blob);
                console.log('Uploading full adaptive audio clip to /api/voice, size:', blob.size);
                await sendAudioToBackend(base64, 'audio/webm');
            } catch (err) {
                console.error('Error handling adaptive audio:', err);
                showNotification('Audio error: ' + err.message, 'error');
            } finally {
                if (currentAudioStream) {
                    currentAudioStream.getTracks().forEach(t => t.stop());
                    currentAudioStream = null;
                }
                isListening = false;
                showNotification('Stopped listening', 'info');
            }
        };

        currentMediaRecorder.start();
        isListening = true;
        // Ensure any previous monitor is cleared
        if (audioMonitorInterval) {
            clearInterval(audioMonitorInterval);
            audioMonitorInterval = null;
        }
        audioMonitorInterval = setInterval(monitorSpeechRMS, 150); // check ~6.6x per second

        // Safety cap timeout
        setTimeout(() => {
            if (isListening && currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
                console.log('Max recording duration reached, stopping.');
                currentMediaRecorder.stop();
            }
        }, MAX_RECORDING_MS);
    } catch (err) {
        console.error('Failed to start adaptive recording:', err);
        showNotification('Failed to start listening: ' + err.message, 'error');
    }
}

function monitorSpeechRMS() {
    if (!audioAnalyser || !isListening) return;
    // If master control disabled mid-stream, stop gracefully
    if (!recordingEnabled) {
        if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
            console.log('Recording disabled during monitor; stopping recorder');
            currentMediaRecorder.stop();
        }
        return;
    }
    const len = audioAnalyser.fftSize;
    const data = new Float32Array(len);
    audioAnalyser.getFloatTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < len; i++) sum += data[i] * data[i];
    const rms = Math.sqrt(sum / len);

    const now = Date.now();
    if (rms >= SPEECH_RMS_THRESHOLD) {
        lastAboveThresholdTime = now;
    }

    // Stop after sufficient silence
    if (now - lastAboveThresholdTime > SILENCE_MS_BEFORE_STOP && currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
        const activeMs = now - recordingStartTime;
        if (activeMs >= MIN_RECORDING_MS) {
            console.log('Silence detected for', (now - lastAboveThresholdTime), 'ms; stopping recording. Last RMS:', rms.toFixed(4));
            currentMediaRecorder.stop();
        }
    }
}

function cleanupAudioMonitoring() {
    if (audioMonitorInterval) {
        clearInterval(audioMonitorInterval);
        audioMonitorInterval = null;
    }
    if (audioContext) {
        audioContext.close().catch(() => { });
        audioContext = null;
    }
    audioAnalyser = null;
}

function stopAdaptiveRecording() {
    if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
        console.log('Manual stop requested for adaptive recording');
        currentMediaRecorder.stop();
    }
}

/**
 * Convert Blob to base64 string without data URL prefix
 * @param {Blob} blob - Blob to convert
 * @returns {Promise<string>} Base64 string without prefix
 */
function blobToBase64WithoutPrefix(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const dataUrl = String(reader.result || '');
            const parts = dataUrl.split(',');
            const base64 = parts.length > 1 ? parts[1] : '';
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

/**
 * Send complete audio recording to backend
 * @param {string} base64Audio - Base64 encoded audio data (without prefix)
 * @param {string} format - Audio format (e.g., 'audio/webm')
 */
async function sendAudioToBackend(base64Audio, format) {
    try {
        // Send base64 audio as JSON to /api/voice endpoint (Flask server forwards to ML server)
        const response = await fetch('http://localhost:5000/api/voice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                audio: base64Audio,
                format: format
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log('Audio clip sent successfully:', result);
        console.log('Voice response - Bot message:', result?.response);
        console.log('Voice response - Timer time:', result?.time);
        console.log('Full voice response object:', result);

        // Get chat log element
        const chatLog = document.querySelector('.log');
        if (!chatLog) {
            console.warn('Chat log element not found');
            return;
        }

        // Add transcribed user message to chat log
        const transcription = result?.transcription || 'Voice input';
        if (transcription) {
            addMessageToChat(chatLog, `You: ${transcription}`, 'user');
        }

        // Add bot response to chat log
        const botMessage = result?.response || result?.message || JSON.stringify(result);
        addMessageToChat(chatLog, `Bot: ${botMessage}`, 'bot');

        // Show typing animation in dialogue element and play audio
        const dialogueElement = document.querySelector('.dialogue');
        if (dialogueElement) {
            typeText(dialogueElement, botMessage, result?.audio);
        }

        // Handle timer if present in response
        let timerTime = result?.time;

        // If no explicit time field, try to extract from response text
        if (!timerTime && result?.response) {
            const extracted = extractTimerFromResponse(result.response);
            if (extracted) {
                timerTime = extracted;
                console.log('Extracted timer from response text:', timerTime);
            }
        }

        if (timerTime) {
            console.log('Starting timer from voice input with time:', timerTime);
            startTimer(timerTime);
        } else {
            console.log('No timer time found in voice response');
        }

        // Scroll to bottom of chat log
        chatLog.scrollTop = chatLog.scrollHeight;

    } catch (error) {
        console.error('Error sending audio to backend:', error);
        // Show error in chat if possible
        const chatLog = document.querySelector('.log');
        if (chatLog) {
            addMessageToChat(chatLog, `Bot: Error - ${error.message}`, 'error');
        }
        throw error;
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

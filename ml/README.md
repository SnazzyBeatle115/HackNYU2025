# Virtual AI Assistant with OpenRouter

A virtual AI assistant that tracks your screen and camera, powered by OpenRouter for LLM text generation.

## Features

- AI-powered conversations using OpenRouter
- Welcome message and interactive assistance
- Task handling (timers, reminders, etc.)
- Text-to-speech using ElevenLabs
- Screen analysis and activity detection (OCR and study detection)
- Camera-based person presence and distraction detection
- Natural language interaction
- Backup model support for reliability

## Setup

### 1. Install Dependencies

Make sure you're in the virtual environment, then install the requirements:

```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get OpenRouter API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up or log in
3. Navigate to [API Keys](https://openrouter.ai/keys)
4. Create a new API key

### 3. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here
   ```

3. (Optional) Specify different models:
   ```
   OPENROUTER_MODEL=anthropic/claude-3-haiku
   OPENROUTER_BACKUP_MODELS=openai/gpt-3.5-turbo,google/gemini-pro
   OPENROUTER_VISION_MODEL=openai/gpt-4-turbo
   OPENROUTER_OCR_MODEL=openai/gpt-4-turbo
   ```
   
   Note: The OCR model is used specifically for text extraction from images, while the vision model is used for activity detection. This separation allows for better accuracy and cost optimization.

4. (Optional) Configure ElevenLabs for text-to-speech:
   ```
   ELEVENLABS_API_KEY=your-elevenlabs-api-key
   ELEVENLABS_VOICE_ID=your-voice-id
   ```

## Usage

### HTTP API Server (Default)

Run the Flask API server for frontend integration:

```bash
python api_server.py
```

The server will start on `http://localhost:5000` and provide REST API endpoints.

You can also specify a custom port:
```bash
python api_server.py --port 8080
```

#### API Endpoints

**POST `/chat`** - Send a message and get a response with audio
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Set a timer for 5 minutes"}'
```

Response:
```json
{
  "response": "Timer set for 5 minutes!",
  "status": "success",
  "audio": {
    "data": "base64_encoded_audio_string",
    "format": "mp3",
    "data_url": "data:audio/mpeg;base64,..."
  },
  "time": "05:00"
}
```

Note: 
- The `audio` field is optional and only included if ElevenLabs is configured.
- The `time` field is optional and only included if the message is about a timer (e.g., "set a timer for 5 minutes"). Format is "MM:SS".

**POST `/reset`** - Reset the conversation history
```bash
curl -X POST http://localhost:5000/reset
```

**GET `/status`** - Get assistant status
```bash
curl http://localhost:5000/status
```

**GET `/health`** - Health check
```bash
curl http://localhost:5000/health
```

**POST `/detectscreen`** - Analyze screenshot for text extraction and activity detection
```bash
curl -X POST http://localhost:5000/detectscreen \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_string"}'
```

Response:
```json
{
  "text_extracted": "Extracted text from the image...",
  "activity_detected": "User is reading a document",
  "is_studying": true,
  "analysis": "Full AI analysis...",
  "ocr_model_used": "openai/gpt-4-turbo",
  "vision_model_used": "openai/gpt-4-turbo",
  "status": "success"
}
```

Note: This endpoint uses a two-model approach:
1. **OCR Model** (default: `openai/gpt-4-turbo`) - Specialized for accurate text extraction
2. **Vision Model** (default: `openai/gpt-4-turbo`) - Used for activity detection and context understanding

You can configure different models for each task. For example, use a faster/cheaper model for OCR and a more powerful model for activity detection.

**POST `/detectcamera`** - Analyze camera image for person presence and study activity
```bash
curl -X POST http://localhost:5000/detectcamera \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_string"}'
```

Response:
```json
{
  "person_present": true,
  "activity_detected": "Person is using phone",
  "is_studying": false,
  "analysis": "Full AI analysis...",
  "vision_model_used": "openai/gpt-4-turbo",
  "status": "success"
}
```

Note: This endpoint detects:
- **Person presence**: Whether a person is visible in the camera
- **Distractions**: Phone usage, looking away, eating, etc.
- **Study status**: If no person is present or person is distracted = NOT studying

**GET `/welcome`** - Get welcome message with audio
```bash
curl http://localhost:5000/welcome
```

Response includes the welcome message text and base64-encoded audio.

#### API Formats

This section provides detailed request and response formats for all API endpoints.

##### POST `/chat`

Send a message to the AI assistant and receive a response with optional audio.

**Request:**
```http
POST /chat
Content-Type: application/json

{
  "message": "Set a timer for 5 minutes"
}
```

**Request Body Fields:**
- `message` (string, required): The user's message/query

**Success Response (200 OK):**
```json
{
  "response": "I'd be happy to help you set a timer for 5 minutes! Let me do that for you right away.",
  "status": "success",
  "audio": {
    "data": "base64_encoded_audio_string",
    "format": "mp3",
    "data_url": "data:audio/mpeg;base64,..."
  },
  "time": "05:00"
}
```

**Response Fields:**
- `response` (string): The assistant's text response
- `status` (string): Response status ("success" or "error")
- `audio` (object, optional): Audio data for text-to-speech (only included if ElevenLabs is configured)
  - `data` (string): Base64-encoded audio data
  - `format` (string): Audio format (typically "mp3")
  - `data_url` (string): Data URL format for direct use in HTML audio elements
- `time` (string, optional): Timer duration in "MM:SS" format (only included if the message is about a timer)
  - Examples: "05:00" (5 minutes), "00:30" (30 seconds), "60:00" (1 hour)

**Error Responses:**
- `400 Bad Request`: Missing or empty message field
- `500 Internal Server Error`: Assistant initialization or processing error

**Timer Detection:**
The `time` field is automatically detected and included when the message contains timer-related keywords (timer, countdown, alarm) and a time duration. Examples of messages that will include the `time` field:
- "Set a timer for 5 minutes" → `"time": "05:00"`
- "I want a timer of 3 minutes" → `"time": "03:00"`
- "Timer 30 seconds" → `"time": "00:30"`
- "1 hour timer" → `"time": "60:00"`
- "Timer for 2 hours and 15 minutes" → `"time": "135:00"`

---

##### GET `/welcome`

Get the welcome message with optional audio.

**Request:**
```http
GET /welcome
```

**Success Response (200 OK):**
```json
{
  "message": "Hello! I'm Pika, your cute and caring virtual AI assistant! I'm here to help you with various tasks like setting timers, answering questions, or assisting with your computer. What would you like me to do?",
  "status": "success",
  "audio": {
    "data": "base64_encoded_audio_string",
    "format": "mp3",
    "data_url": "data:audio/mpeg;base64,..."
  }
}
```

**Response Fields:**
- `message` (string): The welcome message text
- `status` (string): Response status
- `audio` (object, optional): Audio data (only if ElevenLabs is configured)

**Error Responses:**
- `500 Internal Server Error`: Assistant initialization error

---

##### POST `/detectscreen`

Analyze a screenshot to extract text and detect user activity (studying vs. distractions).

**Request:**
```http
POST /detectscreen
Content-Type: application/json

{
  "image": "base64_encoded_image_string"
}
```

**Request Body Fields:**
- `image` (string, required): Base64-encoded image. Can be:
  - Raw base64 string: `"iVBORw0KGgoAAAANSUhEUgAA..."`
  - Data URL format: `"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."`

**Success Response (200 OK):**
```json
{
  "text_extracted": "Discord - HackNYU Fall 25\n# announcements\nWelcome to HackNYU...",
  "activity_detected": "User is viewing announcements on Discord",
  "is_studying": false,
  "analysis": "ACTIVITY: The user is viewing announcements on a Discord server...\nIS_STUDYING: No\nDETAILS: Discord is a messaging platform...",
  "ocr_model_used": "openai/gpt-4-turbo",
  "vision_model_used": "openai/gpt-4-turbo",
  "details": "Discord is a messaging platform and viewing announcements is a passive activity, not active studying.",
  "status": "success"
}
```

**Response Fields:**
- `text_extracted` (string): All text extracted from the image via OCR
- `activity_detected` (string): Description of what the user is doing
- `is_studying` (boolean): `true` if user is actively studying, `false` if distracted
- `analysis` (string): Full AI analysis text
- `ocr_model_used` (string): Model used for text extraction
- `vision_model_used` (string): Model used for activity detection
- `details` (string, optional): Additional context about the activity
- `status` (string): Response status

**Error Responses:**
- `400 Bad Request`: Missing or empty image field
- `500 Internal Server Error`: Image processing or model error

**Notes:**
- Uses two separate models: one for OCR (text extraction) and one for activity detection
- `is_studying` is `false` for messaging apps (Discord, Slack), social media, browsing, etc., even if educational content is visible
- Only active engagement (coding, writing, deep reading) counts as studying

**Response Schema:**
```typescript
{
  text_extracted: string;        // All text extracted from the image via OCR
  activity_detected: string;    // Description of what the user is doing
  is_studying: boolean;         // true if actively studying, false if distracted
  analysis: string;             // Full AI analysis text with structured format
  ocr_model_used: string;      // Model identifier used for text extraction
  vision_model_used: string;   // Model identifier used for activity detection
  details?: string;            // Optional: Additional context about the activity
  audio?: {                    // Optional: Warning audio (only if is_studying is false and ElevenLabs is configured)
    data: string;              // Base64-encoded audio data
    format: string;            // Audio format (typically "mp3")
    data_url: string;         // Data URL format for direct use in HTML audio elements
  };
  warning_message?: string;    // Optional: Text of the warning message
  status: "success" | "error";  // Response status
}
```

**Note:** If `is_studying` is `false` and ElevenLabs is configured, the response will include an `audio` field with a warning message: "Hey! Looks like you are doing [activity_detected], you should be focusing!"

**Example Response (with warning audio):**
```json
{
  "text_extracted": "Official - HackNYU Fall 25\n#announcements\n\nAshley [HackNYU Leadership] 1:17 PM\nThere's still pizza left!!! @everyone...",
  "activity_detected": "The user is viewing announcements on a Discord server for an event called HackNYU Fall 25.",
  "is_studying": false,
  "analysis": "ACTIVITY: The user is viewing announcements on a Discord server...\nIS_STUDYING: No\nDETAILS: The user is not actively engaged...",
  "ocr_model_used": "openai/gpt-4-turbo",
  "vision_model_used": "openai/gpt-4-turbo",
  "details": "The user is not actively engaged in studying or academic work. They are browsing a channel named #announcements on Discord...",
  "audio": {
    "data": "base64_encoded_audio_string",
    "format": "mp3",
    "data_url": "data:audio/mpeg;base64,..."
  },
  "warning_message": "Hey! Looks like you are doing The user is viewing announcements on a Discord server for an event called HackNYU Fall 25., you should be focusing!",
  "status": "success"
}
```

---

##### POST `/detectcamera`

Analyze a camera image to detect person presence and study activity.

**Request:**
```http
POST /detectcamera
Content-Type: application/json

{
  "image": "base64_encoded_image_string"
}
```

**Request Body Fields:**
- `image` (string, required): Base64-encoded camera image. Can be:
  - Raw base64 string: `"iVBORw0KGgoAAAANSUhEUgAA..."`
  - Data URL format: `"data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAA..."`

**Success Response (200 OK):**
```json
{
  "person_present": true,
  "activity_detected": "Person is using phone",
  "is_studying": false,
  "analysis": "PERSON_PRESENT: Yes\nACTIVITY: Person is using phone\nIS_STUDYING: No\nDETAILS: Person is holding and looking at a mobile phone...",
  "vision_model_used": "openai/gpt-4-turbo",
  "details": "Person is holding and looking at a mobile phone, which is a distraction from studying.",
  "status": "success"
}
```

**Response Fields:**
- `person_present` (boolean): `true` if a person is visible in the camera, `false` if absent
- `activity_detected` (string): Description of what the person is doing (e.g., "using phone", "looking at screen", "absent from camera")
- `is_studying` (boolean): `true` if person is actively studying, `false` if distracted or absent
- `analysis` (string): Full AI analysis text
- `vision_model_used` (string): Model used for camera image analysis
- `details` (string, optional): Additional context about the activity
- `status` (string): Response status

**Error Responses:**
- `400 Bad Request`: Missing or empty image field
- `500 Internal Server Error`: Image processing or model error

**Notes:**
- **Critical Rules:**
  - If `person_present` is `false` → `is_studying` is always `false` (person is absent)
  - If person is using a phone/tablet → `is_studying` is `false` (distraction)
  - If person is looking away, eating, sleeping, or distracted → `is_studying` is `false`
- Person is only considered studying if:
  - Person is present AND facing the screen/desk
  - Person appears engaged with computer/work materials
  - Person is actively reading, writing, or working
- Frontend should send camera images periodically (e.g., every 5-10 seconds) for continuous monitoring

**Response Schema:**
```typescript
{
  person_present: boolean;      // true if person visible in camera, false if absent
  activity_detected: string;    // Description of activity (e.g., "using phone", "looking at screen", "absent from camera")
  is_studying: boolean;         // true if actively studying, false if distracted or absent
  analysis: string;             // Full AI analysis text with structured format
  vision_model_used: string;   // Model identifier used for camera image analysis
  details?: string;            // Optional: Additional context about the activity
  audio?: {                    // Optional: Warning audio (only if is_studying is false and ElevenLabs is configured)
    data: string;              // Base64-encoded audio data
    format: string;            // Audio format (typically "mp3")
    data_url: string;         // Data URL format for direct use in HTML audio elements
  };
  warning_message?: string;    // Optional: Text of the warning message
  status: "success" | "error";  // Response status
}
```

**Note:** If `is_studying` is `false` and ElevenLabs is configured, the response will include an `audio` field with a warning message: "Hey! Looks like you are doing [activity_detected], you should be focusing!"

**Example Response (with warning audio):**
```json
{
  "person_present": true,
  "activity_detected": "using phone",
  "is_studying": false,
  "analysis": "PERSON_PRESENT: yes\nACTIVITY: using phone\nIS_STUDYING: no\nDETAILS: The person is holding and looking at a mobile phone...",
  "vision_model_used": "openai/gpt-4-turbo",
  "details": "The person is holding and looking at a mobile phone, which indicates they are distracted from studying according to the given rules.",
  "audio": {
    "data": "base64_encoded_audio_string",
    "format": "mp3",
    "data_url": "data:audio/mpeg;base64,..."
  },
  "warning_message": "Hey! Looks like you are doing using phone, you should be focusing!",
  "status": "success"
}
```

---

##### POST `/reset`

Reset the conversation history and get a fresh welcome message.

**Request:**
```http
POST /reset
```

**Success Response (200 OK):**
```json
{
  "message": "Conversation reset successfully",
  "status": "success"
}
```

**Response Fields:**
- `message` (string): Confirmation message
- `status` (string): Response status

**Error Responses:**
- `400 Bad Request`: Assistant not initialized

---

##### GET `/status`

Get the current status and configuration of the assistant.

**Request:**
```http
GET /status
```

**Success Response (200 OK):**
```json
{
  "is_active": true,
  "model": "openai/gpt-3.5-turbo",
  "backup_models": ["anthropic/claude-3-haiku", "google/gemini-pro"],
  "status": "success"
}
```

**Response Fields:**
- `is_active` (boolean): Whether the assistant is currently active
- `model` (string): Primary model being used
- `backup_models` (array): List of backup models configured
- `status` (string): Response status

**Note:** If assistant is not initialized, `is_active` will be `false` and `model`/`backup_models` will be `null`/`[]`.

---

##### GET `/health`

Health check endpoint to verify the API server is running.

**Request:**
```http
GET /health
```

**Success Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "Virtual AI Assistant API"
}
```

**Response Fields:**
- `status` (string): Always "healthy" if server is running
- `service` (string): Service name

---

### Command Line Interface (Optional - for testing)

For quick testing or debugging, you can run the assistant in interactive CLI mode:

```bash
python api_server.py --cli
```

or use the short form:

```bash
python api_server.py -c
```

The assistant will:
1. Welcome you with a greeting
2. Ask what you'd like help with
3. Respond to your requests interactively

### Example Interaction

```
Assistant: Hello! I'm your virtual AI assistant. I can help you with various tasks like setting timers, answering questions, or assisting with your computer. What would you like me to do?

You: Set a timer for 5 minutes
Assistant: I'd be happy to help you set a timer for 5 minutes! Let me do that for you right away.

You: What's the weather like?
Assistant: I don't have access to real-time weather data, but I can help you find that information...
```

## Project Structure

```
ml/
├── openrouter_client.py    # OpenRouter API client
├── ai_assistant.py         # Main AI assistant class
├── tools.py                # Tool definitions (timer, etc.)
├── api_server.py           # Unified entry point (API server + CLI)
├── elevenlabs_client.py   # ElevenLabs TTS client
├── image_to_base64.py      # Image to base64 conversion utility
├── test_endpoints.py       # Testing utility for API endpoints
├── requirements.txt        # Python dependencies
├── config_example.txt      # Example environment variables
└── README.md              # This file
```

## How OpenRouter Works

1. **API Client** (`openrouter_client.py`):
   - Handles authentication with OpenRouter
   - Sends requests to OpenRouter API
   - Returns generated text from LLM models

2. **AI Assistant** (`ai_assistant.py`):
   - Manages conversation history
   - Generates welcome messages
   - Processes user input and generates responses
   - Handles tasks like timers

3. **API Server** (`api_server.py`):
   - Unified entry point for both HTTP API and CLI modes
   - Flask HTTP API server with REST endpoints
   - CLI interactive mode for testing
   - Handles CORS for frontend integration
   - Supports conversation reset and status checks

4. **Tools** (`tools.py`):
   - Timer tool with function calling support
   - Sends timer data to frontend at `localhost:4000/setTimer`
   - Parses time in various formats (hh:mm:ss, natural language)

## Available Models

You can use various models through OpenRouter. Some popular options:

- `openai/gpt-3.5-turbo` (default) - Fast and cost-effective
- `openai/gpt-4` - More capable but slower
- `anthropic/claude-3-haiku` - Fast and efficient
- `anthropic/claude-3-sonnet` - Balanced performance
- `google/gemini-pro` - Google's model

To see all available models, you can use:
```python
from openrouter_client import OpenRouterClient
client = OpenRouterClient(api_key="your-key")
models = client.get_available_models()
print(models)
```

## Utilities

### `image_to_base64.py`
Simple utility for converting images to base64 format. Useful for preparing images before sending to API endpoints.

### `test_endpoints.py`
Testing utility for validating API endpoints. Supports testing both `/detectscreen` and `/detectcamera` endpoints with formatted output.

## Next Steps

The screen and camera tracking functionality is now implemented:

1. **Screen Tracking**: Frontend sends screenshots to `/detectscreen` endpoint
2. **Camera Tracking**: Frontend sends camera images to `/detectcamera` endpoint
3. **Integration**: Both endpoints analyze images and return study status

For frontend integration:
- Capture screenshots periodically (e.g., every 5-10 seconds) and send to `/detectscreen`
- Capture camera frames periodically and send to `/detectcamera`
- Combine results from both endpoints for comprehensive study monitoring

## Testing

### Testing API Endpoints

Use the `test_endpoints.py` utility to test the `/detectscreen` and `/detectcamera` endpoints:

**Test camera detection:**
```bash
python test_endpoints.py test_camera.jpg --camera
```

**Test screen detection:**
```bash
python test_endpoints.py test.png --screen
```

**Custom endpoint URL:**
```bash
python test_endpoints.py image.jpg --camera --url http://localhost:8080/detectcamera
```

The test utility will:
- Convert the image to base64
- Send it to the specified endpoint
- Display formatted results including person presence, activity detection, and study status

### Image to Base64 Conversion

Use `image_to_base64.py` to convert images to base64 format:

```bash
# Convert to raw base64
python image_to_base64.py image.png

# Convert to data URL format
python image_to_base64.py image.jpg --data-url

# Save to file
python image_to_base64.py image.png --output base64.txt

# Preview first 100 characters
python image_to_base64.py image.png --preview
```

## Troubleshooting

- **API Key Error**: Make sure your `.env` file exists and contains a valid `OPENROUTER_API_KEY`
- **Import Errors**: Ensure you've installed all dependencies with `pip install -r requirements.txt`
- **Model Not Found**: Check that the model name is correct. Use `client.get_available_models()` to see available models
- **Endpoint Testing Fails**: Make sure the API server is running (`python api_server.py`) before testing endpoints


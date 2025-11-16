"""
Virtual AI Assistant - Unified Entry Point
Supports both HTTP API server and CLI interactive modes
"""
import os
import sys
import argparse
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from ai_assistant import AIAssistant
from elevenlabs_client import ElevenLabsClient

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Global assistant instance
assistant = None
elevenlabs_client = None
welcome_audio_cache = None  # Cache welcome message audio


def init_assistant():
    """Initialize the AI assistant with backup model support"""
    global assistant, elevenlabs_client
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    # Get backup models from environment (comma-separated)
    backup_models_str = os.getenv("OPENROUTER_BACKUP_MODELS", "")
    backup_models = None
    if backup_models_str:
        backup_models = [m.strip() for m in backup_models_str.split(",") if m.strip()]
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    # Validate API key format (basic check)
    if not api_key.startswith("sk-or-v1-"):
        print(f"[WARN] API key format may be incorrect. Expected format: sk-or-v1-...")
        print(f"[WARN] Current key starts with: {api_key[:10]}...")
    
    assistant = AIAssistant(api_key=api_key, model=model, backup_models=backup_models)
    assistant.start()
    
    # Initialize ElevenLabs client (optional - won't fail if not configured)
    try:
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if elevenlabs_api_key:
            elevenlabs_client = ElevenLabsClient(api_key=elevenlabs_api_key)
            print("ElevenLabs client initialized")
        else:
            print("ElevenLabs API key not found - audio generation will be disabled")
            elevenlabs_client = None
    except Exception as e:
        print(f"Failed to initialize ElevenLabs: {str(e)}")
        elevenlabs_client = None
    
    return assistant


def run_cli_mode():
    """Run the assistant in CLI interactive mode"""
    print("=" * 50)
    print("Virtual AI Assistant - CLI Mode")
    print("=" * 50)
    
    # Get API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    # Get backup models from environment (comma-separated)
    backup_models_str = os.getenv("OPENROUTER_BACKUP_MODELS", "")
    backup_models = None
    if backup_models_str:
        backup_models = [m.strip() for m in backup_models_str.split(",") if m.strip()]
        print(f"Backup models configured: {', '.join(backup_models)}")
    
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment variables.")
        print("Please create a .env file with your OpenRouter API key.")
        print("See config_example.txt for reference.")
        return
    
    try:
        # Initialize assistant with backup models
        assistant = AIAssistant(api_key=api_key, model=model, backup_models=backup_models)
        
        # Start the assistant (this will welcome the user)
        assistant.start()
        
        # Main interaction loop
        print("\n" + "=" * 50)
        print("Type 'quit' or 'exit' to stop the assistant")
        print("=" * 50 + "\n")
        
        while assistant.is_active:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    assistant.stop()
                    break
                
                # Process user input and get response
                response = assistant.process_user_input(user_input)
                print(f"Assistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user.")
                assistant.stop()
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    
    except Exception as e:
        print(f"Failed to initialize assistant: {str(e)}")


# Flask API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Virtual AI Assistant API"
    }), 200


@app.route('/welcome', methods=['GET'])
def welcome():
    """
    Get the welcome message with audio
    
    Returns:
    {
        "message": "welcome message text",
        "audio": {
            "data": "base64_encoded_audio",
            "format": "mp3",
            "data_url": "data:audio/mpeg;base64,..."
        },
        "status": "success"
    }
    """
    global assistant, elevenlabs_client, welcome_audio_cache
    
    # Initialize assistant if not already done
    if assistant is None:
        try:
            init_assistant()
        except Exception as e:
            return jsonify({
                "error": f"Failed to initialize assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Check if assistant is active
    if not assistant.is_active:
        try:
            assistant.start()
        except Exception as e:
            return jsonify({
                "error": f"Failed to start assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Get welcome message (regenerate if needed)
    welcome_message = assistant._generate_welcome()
    
    # Generate audio for welcome message
    audio_data = None
    if elevenlabs_client and welcome_message:
        # Check cache first
        if welcome_audio_cache and welcome_audio_cache.get("message") == welcome_message:
            audio_data = welcome_audio_cache.get("audio")
        else:
            try:
                # Generate audio from welcome message
                audio_result = elevenlabs_client.text_to_speech(
                    text=welcome_message,
                    stability=0.5,  # Cute, stable voice
                    similarity_boost=0.75,
                    style=0.2,  # Slight expressiveness for Pika's personality
                    use_speaker_boost=True
                )
                audio_data = {
                    "data": audio_result["audio_base64"],
                    "format": audio_result["format"],
                    "data_url": f"data:audio/{audio_result['format']};base64,{audio_result['audio_base64']}"
                }
                # Cache the welcome audio
                welcome_audio_cache = {
                    "message": welcome_message,
                    "audio": audio_data
                }
                # Save audio file for debugging (backend only)
                try:
                    saved_path = elevenlabs_client.save_audio(
                        audio_data=audio_result.get("audio_data"),
                        text=welcome_message,
                        output_dir="audio_output"
                    )
                    print(f"Saved welcome audio: {saved_path}")
                except Exception as save_error:
                    print(f"Failed to save welcome audio: {str(save_error)}")
            except Exception as e:
                # If audio generation fails, still return text response
                print(f"Failed to generate welcome audio: {str(e)}")
                audio_data = None
    
    # Return welcome message with optional audio
    result = {
        "message": welcome_message,
        "status": "success"
    }
    
    if audio_data:
        result["audio"] = audio_data
    
    return jsonify(result), 200


def parse_timer_request(message):
    """
    Detect if the message is about a timer and extract the time duration.
    Returns time in MM:SS format if timer is detected, None otherwise.
    
    Examples:
    - "i want a timer of 3 minutes" -> "03:00"
    - "set timer for 5 min" -> "05:00"
    - "timer 30 seconds" -> "00:30"
    - "1 hour timer" -> "60:00"
    """
    message_lower = message.lower()
    
    # Check if message contains timer-related keywords
    timer_keywords = ['timer', 'countdown', 'alarm']
    if not any(keyword in message_lower for keyword in timer_keywords):
        return None
    
    # Patterns to match time durations (order matters - more specific patterns first)
    # Match patterns like: "3 minutes", "5 min", "30 seconds", "1 hour", etc.
    patterns = [
        (r'(\d+)\s*(?:hour|hr|h)\s+(?:and\s+)?(\d+)\s*(?:minute|min|m)', 'hours_minutes'),
        (r'(\d+)\s*(?:minute|min|m)\s+(?:and\s+)?(\d+)\s*(?:second|sec|s)', 'minutes_seconds'),
        (r'(\d+)\s*(?:hour|hr|h)', 'hours_only'),
        (r'(\d+)\s*(?:minute|min|m)', 'minutes_only'),
        (r'(\d+)\s*(?:second|sec|s)', 'seconds_only'),
    ]
    
    total_seconds = 0
    
    for pattern, pattern_type in patterns:
        match = re.search(pattern, message_lower)
        if match:
            if pattern_type == 'hours_minutes':
                hours = int(match.group(1))
                minutes = int(match.group(2)) if match.group(2) else 0
                total_seconds = hours * 3600 + minutes * 60
                break
            elif pattern_type == 'minutes_seconds':
                minutes = int(match.group(1))
                seconds = int(match.group(2)) if match.group(2) else 0
                total_seconds = minutes * 60 + seconds
                break
            elif pattern_type == 'hours_only':
                hours = int(match.group(1))
                total_seconds = hours * 3600
                break
            elif pattern_type == 'minutes_only':
                minutes = int(match.group(1))
                total_seconds = minutes * 60
                break
            elif pattern_type == 'seconds_only':
                total_seconds = int(match.group(1))
                break
    
    if total_seconds == 0:
        return None
    
    # Convert to MM:SS format
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    return f"{minutes:02d}:{seconds:02d}"


@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint - receives user input and returns assistant response with audio
    
    Expected JSON payload:
    {
        "message": "user input text"
    }
    
    Returns:
    {
        "response": "assistant response",
        "status": "success",
        "audio": {
            "data": "base64_encoded_audio",
            "format": "mp3",
            "data_url": "data:audio/mpeg;base64,..."
        },  // Optional - only included if ElevenLabs is configured
        "time": "MM:SS"  // Optional - only included if message is about a timer (e.g., "i want a timer of 3 minutes")
    }
    """
    global assistant, elevenlabs_client
    
    # Initialize assistant if not already done
    if assistant is None:
        try:
            init_assistant()
        except Exception as e:
            return jsonify({
                "error": f"Failed to initialize assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Check if assistant is active
    if not assistant.is_active:
        try:
            assistant.start()
        except Exception as e:
            return jsonify({
                "error": f"Failed to start assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Get user input from request
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
        
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                "error": "Message field is required and cannot be empty",
                "status": "error"
            }), 400
        
        # Process user input through assistant
        response = assistant.process_user_input(user_message)
        
        # Check if the message is about a timer
        timer_time = parse_timer_request(user_message)
        
        # Generate audio using ElevenLabs if available
        audio_data = None
        if elevenlabs_client and response:
            try:
                # Generate audio from Pika's response
                audio_result = elevenlabs_client.text_to_speech(
                    text=response,
                    stability=0.5,  # Cute, stable voice
                    similarity_boost=0.75,
                    style=0.2,  # Slight expressiveness for Pika's personality
                    use_speaker_boost=True
                )
                audio_data = {
                    "data": audio_result["audio_base64"],
                    "format": audio_result["format"],
                    "data_url": f"data:audio/{audio_result['format']};base64,{audio_result['audio_base64']}"
                }
                # Save audio file for debugging (backend only)
                try:
                    saved_path = elevenlabs_client.save_audio(
                        audio_data=audio_result.get("audio_data"),
                        text=response,
                        output_dir="audio_output"
                    )
                    print(f"Saved audio: {saved_path}")
                except Exception as save_error:
                    print(f"Failed to save audio: {str(save_error)}")
            except Exception as e:
                # If audio generation fails, still return text response
                print(f"Failed to generate audio: {str(e)}")
                audio_data = None
        
        # Return response with optional audio and timer time
        result = {
            "response": response,
            "status": "success"
        }
        
        if audio_data:
            result["audio"] = audio_data
        
        if timer_time:
            result["time"] = timer_time
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Error processing request: {str(e)}",
            "status": "error"
        }), 500


@app.route('/voice', methods=['POST'])
def voice():
    """
    Voice input endpoint - receives audio, transcribes it, and processes through chat
    
    Expected JSON payload:
    {
        "audio": "base64_encoded_audio_string",
        "format": "audio/webm"  // Optional
    }
    
    Returns:
    {
        "response": "assistant response",
        "status": "success",
        "transcription": "transcribed user speech",
        "audio": {
            "data": "base64_encoded_audio",
            "format": "mp3",
            "data_url": "data:audio/mpeg;base64,..."
        }
    }
    """
    global assistant, elevenlabs_client
    
    # Initialize assistant if not already done
    if assistant is None:
        try:
            init_assistant()
        except Exception as e:
            return jsonify({
                "error": f"Failed to initialize assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Check if assistant is active
    if not assistant.is_active:
        try:
            assistant.start()
        except Exception as e:
            return jsonify({
                "error": f"Failed to start assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Get audio from request
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
        
        audio_base64 = data.get('audio', '').strip()
        audio_format = data.get('format', 'audio/webm')
        
        if not audio_base64:
            return jsonify({
                "error": "Audio field is required and cannot be empty",
                "status": "error"
            }), 400
        
        # Transcribe audio using ElevenLabs
        transcribed_text = None
        if elevenlabs_client:
            try:
                print(f"Transcribing audio: format={audio_format}, base64_length={len(audio_base64)}")
                transcribed_text = elevenlabs_client.speech_to_text(audio_base64, audio_format)
                print(f"Transcription: {transcribed_text}")
            except Exception as e:
                print(f"Failed to transcribe audio: {str(e)}")
                return jsonify({
                    "error": f"Failed to transcribe audio: {str(e)}",
                    "status": "error"
                }), 500
        else:
            return jsonify({
                "error": "ElevenLabs client not initialized. Speech-to-text requires ElevenLabs API key.",
                "status": "error"
            }), 500
        
        if not transcribed_text or not transcribed_text.strip():
            return jsonify({
                "error": "Transcription resulted in empty text",
                "status": "error"
            }), 400
        
        # Process transcribed text through chat
        # Call the chat function directly instead of making HTTP request
        user_message = transcribed_text.strip()
        response = assistant.process_user_input(user_message)
        
        # Check if the message is about a timer
        timer_time = parse_timer_request(user_message)
        
        # Generate audio using ElevenLabs if available
        audio_data = None
        if elevenlabs_client and response:
            try:
                # Generate audio from assistant's response
                audio_result = elevenlabs_client.text_to_speech(
                    text=response,
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.2,
                    use_speaker_boost=True
                )
                audio_data = {
                    "data": audio_result["audio_base64"],
                    "format": audio_result["format"],
                    "data_url": f"data:audio/{audio_result['format']};base64,{audio_result['audio_base64']}"
                }
                # Save audio file for debugging (backend only)
                try:
                    saved_path = elevenlabs_client.save_audio(
                        audio_data=audio_result.get("audio_data"),
                        text=response,
                        output_dir="audio_output"
                    )
                    print(f"Saved audio: {saved_path}")
                except Exception as save_error:
                    print(f"Failed to save audio: {str(save_error)}")
            except Exception as e:
                # If audio generation fails, still return text response
                print(f"Failed to generate audio: {str(e)}")
                audio_data = None
        
        # Return response with transcription, text response, and optional audio
        result = {
            "response": response,
            "transcription": transcribed_text,
            "status": "success"
        }
        
        if audio_data:
            result["audio"] = audio_data
        
        if timer_time:
            result["time"] = timer_time
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Error processing voice input: {str(e)}",
            "status": "error"
        }), 500


@app.route('/reset', methods=['POST'])
def reset():
    """
    Reset the conversation history
    
    Returns:
    {
        "message": "Conversation reset",
        "status": "success"
    }
    """
    global assistant
    
    if assistant is None:
        return jsonify({
            "error": "Assistant not initialized",
            "status": "error"
        }), 400
    
    # Reset conversation history
    assistant.conversation_history = []
    assistant.start()  # Restart to get new welcome message
    
    # Clear welcome audio cache so new welcome message gets new audio
    global welcome_audio_cache
    welcome_audio_cache = None
    
    return jsonify({
        "message": "Conversation reset successfully",
        "status": "success"
    }), 200


@app.route('/detectscreen', methods=['POST'])
def detect_screen():
    """
    Analyze a screenshot to extract text and detect non-study activities
    
    Expected JSON payload:
    {
        "image": "base64_encoded_image_string" or "data:image/jpeg;base64,..."
    }
    
    Returns:
    {
        "text_extracted": "extracted text from image",
        "activity_detected": "description of what user is doing",
        "is_studying": true/false,
        "analysis": "full AI analysis",
        "status": "success"
    }
    """
    global assistant, elevenlabs_client
    
    # Initialize assistant if not already done
    if assistant is None:
        try:
            init_assistant()
        except Exception as e:
            return jsonify({
                "error": f"Failed to initialize assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Get image from request
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
        
        image_base64 = data.get('image', '').strip()
        
        if not image_base64:
            return jsonify({
                "error": "Image field is required and cannot be empty",
                "status": "error"
            }), 400
        
        # Step 1: Extract text using OCR model (specialized for text extraction)
        # Note: Using gpt-4-turbo as default OCR model since it's reliable for text extraction
        # Alternative: google/gemini-1.5-pro or google/gemini-1.5-flash (if available)
        ocr_model = os.getenv("OPENROUTER_OCR_MODEL", "openai/gpt-4-turbo")
        
        # Validate OCR model name (prevent common mistakes)
        if "gemini-pro-vision" in ocr_model.lower():
            print(f"[WARN] Invalid OCR model '{ocr_model}' detected. Using default 'openai/gpt-4-turbo' instead.")
            ocr_model = "openai/gpt-4-turbo"
        ocr_prompt = """Extract all visible text from this image. Include everything you can read:
- Window titles, tab names, browser tabs
- Text in documents, web pages, or applications
- UI elements, buttons, menus, labels
- Any other readable text on the screen

Provide ONLY the extracted text, nothing else. Be thorough and accurate."""
        
        print(f"[INFO] Extracting text using OCR model: {ocr_model}")
        ocr_result = assistant.llm_client.analyze_image(
            image_base64=image_base64,
            prompt=ocr_prompt,
            model=ocr_model,
            temperature=0.1,  # Very low temperature for accurate OCR
            max_tokens=2000,
            use_backup=False  # OCR should be precise, don't use backup
        )
        text_extracted = ocr_result.get("content", "").strip()
        ocr_model_used = ocr_result.get("model_used", ocr_model)
        
        # Step 2: Analyze activity using vision model (for context understanding)
        vision_model = os.getenv("OPENROUTER_VISION_MODEL", "openai/gpt-4-turbo")
        activity_prompt = f"""Analyze this screenshot to determine what the user is doing.

EXTRACTED TEXT FROM SCREEN:
{text_extracted}

Based on the image and the extracted text above, identify:
1. What activity is the user engaged in?
2. Is this a study-related activity or a distraction?

IMPORTANT: Only count as "studying" if the user is ACTIVELY ENGAGED in learning or academic work.

Study activities (ACTIVE engagement required):
- Reading and actively studying documents, textbooks, academic articles, research papers
- Writing code, programming, software development, debugging
- Writing essays, papers, notes, assignments
- Solving problems, working through exercises, practicing skills
- Actively researching and taking notes
- Working on academic assignments or professional work tasks
- Using educational software for active learning (not just browsing)

Non-study activities (distractions - even if educational content is visible):
- Using messaging apps (Discord, Slack, WhatsApp, iMessage, etc.) - even if discussing educational topics
- Scrolling social media (Reddit, Twitter, Facebook, Instagram, TikTok, etc.) - even if reading educational posts
- Browsing websites, forums, or announcements - even if educational
- Watching videos (YouTube, Netflix, etc.) - even if educational content
- Playing games
- Shopping or browsing e-commerce sites
- Reading news, blogs, or general browsing
- Viewing notifications, announcements, or feeds
- Any passive consumption of content, even if educational

CRITICAL RULES:
- If the user is on Discord, Slack, or any messaging/chat platform = NOT studying
- If the user is scrolling or browsing (not actively working) = NOT studying
- If the user is viewing announcements, feeds, or notifications = NOT studying
- Only count as studying if actively creating, writing, coding, or deeply reading educational material

Format your response as:
ACTIVITY: [description of what user is doing]
IS_STUDYING: [yes or no]
DETAILS: [additional context about the activity, application/website name, etc.]"""
        
        print(f"[INFO] Analyzing activity using vision model: {vision_model}")
        analysis_result = assistant.llm_client.analyze_image(
            image_base64=image_base64,
            prompt=activity_prompt,
            model=vision_model,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1000
        )
        
        analysis_text = analysis_result.get("content", "")
        
        # Parse the activity analysis to extract structured information
        # Note: text_extracted is already set from OCR step above
        activity_detected = ""
        is_studying = True
        details = ""
        
        # Try to parse the structured response from activity analysis
        lines = analysis_text.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("ACTIVITY:"):
                activity_detected = line.replace("ACTIVITY:", "").strip()
                current_section = "activity"
            elif line.startswith("IS_STUDYING:"):
                is_studying_str = line.replace("IS_STUDYING:", "").strip().lower()
                is_studying = "yes" in is_studying_str or "true" in is_studying_str
                current_section = "studying"
            elif line.startswith("DETAILS:"):
                details = line.replace("DETAILS:", "").strip()
                current_section = "details"
            elif line and current_section:
                # Continue appending to current section
                if current_section == "activity":
                    activity_detected += " " + line
                elif current_section == "details":
                    details += " " + line
        
        # If parsing didn't work well, use fallback detection
        if not activity_detected:
            activity_detected = "Unable to parse activity"
            # Try to detect keywords from analysis
            analysis_lower = analysis_text.lower()
            non_study_keywords = ["reddit", "twitter", "facebook", "instagram", "messaging", "texting", "game", "video", "entertainment", "social media"]
            study_keywords = ["study", "reading", "coding", "writing", "research", "document", "textbook", "learning"]
            
            if any(keyword in analysis_lower for keyword in non_study_keywords):
                is_studying = False
                activity_detected = "Non-study activity detected"
            elif any(keyword in analysis_lower for keyword in study_keywords):
                is_studying = True
                activity_detected = "Study activity detected"
        
        # Return structured response
        result = {
            "text_extracted": text_extracted,
            "activity_detected": activity_detected,
            "is_studying": is_studying,
            "analysis": analysis_text,
            "ocr_model_used": ocr_model_used,
            "vision_model_used": analysis_result.get("model_used", vision_model),
            "status": "success"
        }
        
        if details:
            result["details"] = details
        
        # Generate warning audio if user is not studying
        if not is_studying and elevenlabs_client and activity_detected:
            try:
                # Create warning message
                warning_message = f"Hey! Looks like you are doing {activity_detected}, you should be focusing!"
                
                # Generate audio from warning message
                audio_result = elevenlabs_client.text_to_speech(
                    text=warning_message,
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.2,
                    use_speaker_boost=True
                )
                
                audio_data = {
                    "data": audio_result["audio_base64"],
                    "format": audio_result["format"],
                    "data_url": f"data:audio/{audio_result['format']};base64,{audio_result['audio_base64']}"
                }
                result["audio"] = audio_data
                result["warning_message"] = warning_message
                
                # Save audio file for debugging (backend only)
                try:
                    saved_path = elevenlabs_client.save_audio(
                        audio_data=audio_result.get("audio_data"),
                        text=warning_message,
                        output_dir="audio_output"
                    )
                    print(f"Saved warning audio: {saved_path}")
                except Exception as save_error:
                    print(f"Failed to save warning audio: {str(save_error)}")
            except Exception as e:
                # If audio generation fails, still return text response
                print(f"Failed to generate warning audio: {str(e)}")
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Error processing screen detection: {str(e)}",
            "status": "error"
        }), 500


@app.route('/detectcamera', methods=['POST'])
def detect_camera():
    """
    Analyze a camera image to detect person presence and study activity
    
    Expected JSON payload:
    {
        "image": "base64_encoded_image_string" or "data:image/jpeg;base64,..."
    }
    
    Returns:
    {
        "person_present": true/false,
        "activity_detected": "description of what user is doing",
        "is_studying": true/false,
        "analysis": "full AI analysis",
        "status": "success"
    }
    """
    global assistant
    
    # Initialize assistant if not already done
    if assistant is None:
        try:
            init_assistant()
        except Exception as e:
            return jsonify({
                "error": f"Failed to initialize assistant: {str(e)}",
                "status": "error"
            }), 500
    
    # Get image from request
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
        
        image_base64 = data.get('image', '').strip()
        
        if not image_base64:
            return jsonify({
                "error": "Image field is required and cannot be empty",
                "status": "error"
            }), 400
        
        # Analyze camera image using vision model
        vision_model = os.getenv("OPENROUTER_VISION_MODEL", "openai/gpt-4-turbo")
        camera_prompt = """Analyze this camera image to determine:
1. Is there a person visible in the camera frame?
2. What is the person doing?
3. Is the person actively studying or distracted?

CRITICAL RULES:
- If NO person is visible in the camera = NOT studying (person is absent)
- If person is using a phone, tablet, or mobile device = NOT studying (distraction)
- If person appears to be sleeping or not engaged = NOT studying
- If person is eating a full meal (not just a quick snack) = NOT studying

IMPORTANT: Looking at the screen/camera IS studying
- When a person is looking at the screen (or camera, which is typically on/near the screen), they are likely engaged with their computer work
- "Looking at the camera" or "looking at the screen" should be considered as studying, as the person is facing their work area
- The camera is typically positioned on or near the computer screen, so looking at the camera means they are facing their screen

IMPORTANT: Brief breaks are part of studying
- Drinking water is a normal, healthy break that should be considered as studying (person is still in their study environment)
- Stretching or taking a brief break while at the desk is part of studying (person is maintaining focus and taking care of themselves)
- These brief activities indicate the person is actively managing their study session and should be counted as studying

Person is PRESENT and studying if:
- Person is visible and facing the screen/desk/camera
- Person is looking at the screen or camera (this indicates they are facing their work)
- Person appears engaged with computer/work materials
- Person is actively reading, writing, or working
- Person is focused on their study materials
- Person is taking a brief break (drinking water, stretching) while at their study location
- Person is in their study environment and taking short, healthy breaks

Person is PRESENT but NOT studying if:
- Person is using a phone, tablet, or mobile device (not the computer screen)
- Person is looking away from their work/screen (turned away, looking at something else, completely disengaged)
- Person is eating a full meal (not just a quick snack or drink)
- Person appears completely distracted or not focused on their work environment
- Person is talking on phone or video calling (not study-related)
- Person is sleeping or appears completely unengaged

Format your response as:
PERSON_PRESENT: [yes or no]
ACTIVITY: [description of what person is doing - e.g., "using phone", "looking at screen", "looking at camera", "drinking water", "stretching or taking a break", "absent from camera"]
IS_STUDYING: [yes or no]
DETAILS: [additional context - what device they're using, their posture, engagement level, etc.]"""
        
        print(f"[INFO] Analyzing camera image using vision model: {vision_model}")
        analysis_result = assistant.llm_client.analyze_image(
            image_base64=image_base64,
            prompt=camera_prompt,
            model=vision_model,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1000
        )
        
        analysis_text = analysis_result.get("content", "")
        
        # Parse the analysis to extract structured information
        person_present = False
        activity_detected = ""
        is_studying = False
        details = ""
        
        # Try to parse the structured response
        lines = analysis_text.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("PERSON_PRESENT:"):
                person_present_str = line.replace("PERSON_PRESENT:", "").strip().lower()
                person_present = "yes" in person_present_str or "true" in person_present_str
                current_section = "presence"
            elif line.startswith("ACTIVITY:"):
                activity_detected = line.replace("ACTIVITY:", "").strip()
                current_section = "activity"
            elif line.startswith("IS_STUDYING:"):
                is_studying_str = line.replace("IS_STUDYING:", "").strip().lower()
                is_studying = "yes" in is_studying_str or "true" in is_studying_str
                current_section = "studying"
            elif line.startswith("DETAILS:"):
                details = line.replace("DETAILS:", "").strip()
                current_section = "details"
            elif line and current_section:
                # Continue appending to current section
                if current_section == "activity":
                    activity_detected += " " + line
                elif current_section == "details":
                    details += " " + line
        
        # If parsing didn't work well, use fallback detection
        if not activity_detected:
            activity_detected = "Unable to parse activity"
            # Try to detect keywords from analysis
            analysis_lower = analysis_text.lower()
            
            # Check for person presence keywords
            if any(keyword in analysis_lower for keyword in ["no person", "absent", "not visible", "empty", "no one"]):
                person_present = False
                is_studying = False
                activity_detected = "No person detected in camera"
            elif any(keyword in analysis_lower for keyword in ["person", "visible", "present", "seen"]):
                person_present = True
                # Check for distractions
                distraction_keywords = ["phone", "mobile", "tablet", "device", "looking away", "distracted", "eating", "drinking", "sleeping"]
                if any(keyword in analysis_lower for keyword in distraction_keywords):
                    is_studying = False
                    activity_detected = "Person present but distracted"
                else:
                    is_studying = True
                    activity_detected = "Person present and studying"
        
        # Enforce critical rules: if no person present, definitely not studying
        if not person_present:
            is_studying = False
            if not activity_detected or activity_detected == "Unable to parse activity":
                activity_detected = "No person detected in camera"
        
        # Return structured response
        result = {
            "person_present": person_present,
            "activity_detected": activity_detected,
            "is_studying": is_studying,
            "analysis": analysis_text,
            "vision_model_used": analysis_result.get("model_used", vision_model),
            "status": "success"
        }
        
        if details:
            result["details"] = details
        
        # Generate warning audio if user is not studying
        if not is_studying and elevenlabs_client and activity_detected:
            try:
                # Create warning message
                warning_message = f"Hey! Looks like you are doing {activity_detected}, you should be focusing!"
                
                # Generate audio from warning message
                audio_result = elevenlabs_client.text_to_speech(
                    text=warning_message,
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.2,
                    use_speaker_boost=True
                )
                
                audio_data = {
                    "data": audio_result["audio_base64"],
                    "format": audio_result["format"],
                    "data_url": f"data:audio/{audio_result['format']};base64,{audio_result['audio_base64']}"
                }
                result["audio"] = audio_data
                result["warning_message"] = warning_message
                
                # Save audio file for debugging (backend only)
                try:
                    saved_path = elevenlabs_client.save_audio(
                        audio_data=audio_result.get("audio_data"),
                        text=warning_message,
                        output_dir="audio_output"
                    )
                    print(f"Saved warning audio: {saved_path}")
                except Exception as save_error:
                    print(f"Failed to save warning audio: {str(save_error)}")
            except Exception as e:
                # If audio generation fails, still return text response
                print(f"Failed to generate warning audio: {str(e)}")
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Error processing camera detection: {str(e)}",
            "status": "error"
        }), 500


@app.route('/status', methods=['GET'])
def status():
    """
    Get the current status of the assistant
    
    Returns:
    {
        "is_active": true/false,
        "model": "primary model name",
        "backup_models": ["backup1", "backup2"],
        "status": "success"
    }
    """
    global assistant
    
    if assistant is None:
        return jsonify({
            "is_active": False,
            "model": None,
            "backup_models": [],
            "status": "not_initialized"
        }), 200
    
    return jsonify({
        "is_active": assistant.is_active,
        "model": assistant.llm_client.model,
        "backup_models": assistant.llm_client.backup_models,
        "status": "success"
    }), 200


def run_api_server(port=5000, host='0.0.0.0'):
    """Run the Flask API server"""
    # Initialize assistant on startup
    try:
        print("=" * 50)
        print("Virtual AI Assistant API Server - Starting...")
        print("=" * 50)
        init_assistant()
        print("Assistant initialized successfully")
        if elevenlabs_client:
            print("ElevenLabs audio generation enabled")
        print("=" * 50)
        print("API Endpoints:")
        print("  GET  /welcome - Get welcome message with audio")
        print("  POST /chat - Send user message and get response (with audio)")
        print("  POST /detectscreen - Analyze screenshot for text extraction and activity detection")
        print("  POST /reset - Reset conversation history")
        print("  GET  /status - Get assistant status")
        print("  GET  /health - Health check")
        print("=" * 50)
        print(f"Server starting on http://{host}:{port}")
        print("=" * 50)
    except Exception as e:
        print(f"Failed to initialize assistant: {str(e)}")
        print("Server will start but assistant may not be available")
    
    # Run Flask server
    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Virtual AI Assistant - HTTP API Server or CLI Mode'
    )
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run in CLI interactive mode (default: API server mode)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port for API server (default: 5000)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host for API server (default: 0.0.0.0)'
    )
    
    args = parser.parse_args()
    
    if args.cli:
        # Run in CLI mode
        run_cli_mode()
    else:
        # Run API server (default)
        run_api_server(port=args.port, host=args.host)

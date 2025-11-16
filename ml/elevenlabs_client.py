"""
ElevenLabs API Client for Text-to-Speech
"""
import requests
import os
import base64
from typing import Optional, Dict
from datetime import datetime
import hashlib


class ElevenLabsClient:
    """Client for interacting with ElevenLabs Text-to-Speech API"""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        """
        Initialize ElevenLabs client
        
        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            voice_id: Voice ID to use (defaults to ELEVENLABS_VOICE_ID env var or default voice)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel voice
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Dict:
        """
        Convert text to speech using ElevenLabs API
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (overrides default)
            stability: Stability setting (0.0-1.0)
            similarity_boost: Similarity boost (0.0-1.0)
            style: Style setting (0.0-1.0)
            use_speaker_boost: Whether to use speaker boost
        
        Returns:
            Dict with "audio_base64" (base64 encoded audio) and "format" (audio format)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Use provided voice_id or default
        voice = voice_id or self.voice_id
        
        # Prepare request
        url = f"{self.base_url}/text-to-speech/{voice}"
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost
            }
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            # Get audio data
            audio_data = response.content
            
            # Convert to base64 for JSON response
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "audio_base64": audio_base64,
                "audio_data": audio_data,  # Raw binary data for saving
                "format": "mp3",
                "size_bytes": len(audio_data)
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"ElevenLabs API error: {str(e)}")
    
    def get_voices(self) -> list:
        """
        Get list of available voices
        
        Returns:
            List of voice dictionaries
        """
        try:
            response = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("voices", [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching voices: {str(e)}")
    
    def change_voice(self, voice_id: str):
        """Change the default voice being used"""
        self.voice_id = voice_id
    
    def speech_to_text(self, audio_base64: str, audio_format: str = "audio/webm", model_id: str = "scribe_v1") -> str:
        """
        Convert speech to text using ElevenLabs Audio Transcriptions API
        
        Args:
            audio_base64: Base64 encoded audio data
            audio_format: MIME type of the audio (e.g., "audio/webm", "audio/mpeg")
        
        Returns:
            Transcribed text string
        """
        if not audio_base64:
            raise ValueError("Audio data cannot be empty")
        
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_base64)
        
        # ElevenLabs Speech-to-Text endpoint
        url = f"{self.base_url}/speech-to-text"
        
        # Prepare multipart form data
        files = {
            'file': ('audio.webm', audio_bytes, audio_format)
        }
        # Transcription model per ElevenLabs API
        data = {
            'model_id': model_id
        }
        
        headers = {
            "xi-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=60  # Transcription can take longer
            )
            # Try to parse JSON even when an error occurs to capture message
            result = None
            try:
                result = response.json()
            except Exception:
                result = None

            if response.status_code >= 400:
                body = result if isinstance(result, dict) else response.text
                # Log full body for debugging
                try:
                    print(f"[ElevenLabs STT] HTTP {response.status_code} error body: {body}")
                except Exception:
                    pass
                raise Exception(f"HTTP {response.status_code} error from ElevenLabs STT: {body}")

            # Successful response
            # Ensure result is JSON
            if result is None:
                response.raise_for_status()
                result = response.json()
            # The response should contain the transcribed text
            # Adjust based on actual ElevenLabs API response format
            transcribed_text = result.get("text", "") or result.get("transcription", "")
            
            if not transcribed_text:
                raise Exception("No transcription text in response")
            
            return transcribed_text.strip()
        
        except requests.exceptions.RequestException as e:
            # Surface error status/body when available
            resp = getattr(e, 'response', None)
            status = getattr(resp, 'status_code', None)
            body = ''
            try:
                if resp is not None:
                    body = resp.text
            except Exception:
                body = ''
            try:
                print(f"[ElevenLabs STT] RequestException status={status} body={body}")
            except Exception:
                pass
            detail = f" | body: {body}" if body else ""
            raise Exception(f"ElevenLabs transcription API error: {str(e)}{detail}")
    
    def save_audio(self, audio_data: bytes, text: str, output_dir: str = "audio_output") -> str:
        """
        Save audio data to a file for debugging/verification
        
        Args:
            audio_data: Raw binary audio data
            text: The text that was converted to speech (for filename)
            output_dir: Directory to save audio files (relative to ml folder)
        
        Returns:
            Path to the saved audio file
        """
        # Get the directory where this file is located (ml folder)
        ml_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(ml_dir, output_dir)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Generate filename: timestamp + text hash (first 8 chars) + .mp3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        # Sanitize text for filename (first 30 chars, remove special chars)
        text_snippet = "".join(c for c in text[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        text_snippet = text_snippet.replace(' ', '_')
        
        filename = f"{timestamp}_{text_hash}_{text_snippet}.mp3"
        filepath = os.path.join(output_path, filename)
        
        # Save audio file
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        return filepath


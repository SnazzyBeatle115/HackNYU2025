"""
OpenRouter API Client for LLM text generation with backup model support
"""
import requests
import os
from typing import Optional, Dict, List


class OpenRouterClient:
    """Client for interacting with OpenRouter API with backup model support"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "openai/gpt-3.5-turbo",
        backup_models: Optional[List[str]] = None
    ):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Primary model identifier (e.g., "openai/gpt-3.5-turbo", "anthropic/claude-3-haiku")
            backup_models: List of backup models to try if primary fails (e.g., ["anthropic/claude-3-haiku", "google/gemini-pro"])
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or pass api_key parameter.")
        
        self.model = model
        self.backup_models = backup_models or []
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/HackNYU2025",  # Optional: for tracking
            "X-Title": "Virtual AI Assistant"  # Optional: for tracking
        }
    
    def _make_request(
        self,
        model: str,
        payload: Dict,
        use_backup: bool = False
    ) -> Dict:
        """
        Make a request to OpenRouter API with a specific model
        
        Args:
            model: Model to use
            payload: Request payload
            use_backup: Whether this is a backup attempt
        
        Returns:
            Response dict with content and tool_calls
        """
        payload_copy = payload.copy()
        payload_copy["model"] = model
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload_copy,
            timeout=60  # Increased timeout for vision models
        )
        
        # Better error handling to show actual error message
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", response.text)
                error_type = error_data.get("error", {}).get("type", "unknown")
                
                # Provide helpful diagnostics for common errors
                if response.status_code == 401:
                    diagnostic = "\n[DIAGNOSTIC] 401 Unauthorized usually means:\n"
                    diagnostic += "  - API key is invalid or expired\n"
                    diagnostic += "  - API key doesn't have access to the requested model\n"
                    diagnostic += "  - Check your OpenRouter account at https://openrouter.ai/keys\n"
                    error_message = f"{error_message}{diagnostic}"
                
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason}: {error_message}"
                )
            except (ValueError, KeyError):
                # If we can't parse JSON, use standard error
                response.raise_for_status()
        
        result = response.json()
        message = result["choices"][0]["message"]
        
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
            "model_used": model,
            "was_backup": use_backup
        }
    
    def generate_text(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 500,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        use_backup: bool = True,
        **kwargs
    ) -> Dict:
        """
        Generate text using OpenRouter API with optional tool calling and backup model support
        
        Args:
            messages: List of message dicts with "role" and "content" keys
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool definitions for function calling
            tool_choice: Tool choice mode ("auto", "none", or specific tool name)
            use_backup: If True, try backup models if primary fails
            **kwargs: Additional parameters to pass to API
        
        Returns:
            Dict with "content" (text response), "tool_calls" (if any), "model_used", and "was_backup"
        """
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
            else:
                payload["tool_choice"] = "auto"
        
        # Try primary model first
        models_to_try = [self.model]
        if use_backup and self.backup_models:
            models_to_try.extend(self.backup_models)
        
        last_error = None
        for i, model in enumerate(models_to_try):
            try:
                result = self._make_request(
                    model=model,
                    payload=payload,
                    use_backup=(i > 0)
                )
                if i > 0:
                    print(f"[INFO] Using backup model: {model} (primary model unavailable)")
                return result
            except requests.exceptions.RequestException as e:
                last_error = e
                if i < len(models_to_try) - 1:
                    print(f"[WARN] Model {model} failed: {str(e)}. Trying backup...")
                    continue
                else:
                    # All models failed
                    raise Exception(f"All models failed. Last error: {str(e)}")
        
        # Should never reach here, but just in case
        raise Exception(f"OpenRouter API error: {str(last_error)}")
    
    def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of model dictionaries
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching models: {str(e)}")
    
    def change_model(self, model: str):
        """Change the primary model being used"""
        self.model = model
    
    def set_backup_models(self, backup_models: List[str]):
        """Set backup models to use if primary fails"""
        self.backup_models = backup_models
    
    def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_backup: bool = True
    ) -> Dict:
        """
        Analyze an image using a multimodal model
        
        Args:
            image_base64: Base64 encoded image string (with or without data URL prefix)
            prompt: Text prompt describing what to analyze
            model: Vision model to use (defaults to gpt-4-turbo if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_backup: If True, try backup models if primary fails
        
        Returns:
            Dict with "content" (analysis text), "model_used", and "was_backup"
        """
        # Use vision model if not specified
        vision_model = model or "openai/gpt-4-turbo"
        
        # Clean up base64 string (remove data URL prefix if present)
        if image_base64.startswith("data:image"):
            # Extract base64 part after comma
            image_base64 = image_base64.split(",")[1]
        
        # Determine image format from base64 or default to jpeg
        # For OpenRouter, we'll use the standard format
        image_url = f"data:image/jpeg;base64,{image_base64}"
        
        # Format messages for multimodal API
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Try primary vision model first, then backups
        models_to_try = [vision_model]
        if use_backup and self.backup_models:
            # Filter backup models to only vision-capable ones
            vision_backups = [
                m for m in self.backup_models 
                if any(vision_keyword in m.lower() for vision_keyword in ["gpt-4", "claude-3", "gemini", "vision"])
            ]
            models_to_try.extend(vision_backups)
        
        last_error = None
        for i, model_name in enumerate(models_to_try):
            try:
                result = self._make_request(
                    model=model_name,
                    payload=payload,
                    use_backup=(i > 0)
                )
                if i > 0:
                    print(f"[INFO] Using backup vision model: {model_name} (primary model unavailable)")
                return result
            except requests.exceptions.RequestException as e:
                last_error = e
                if i < len(models_to_try) - 1:
                    print(f"[WARN] Vision model {model_name} failed: {str(e)}. Trying backup...")
                    continue
                else:
                    raise Exception(f"All vision models failed. Last error: {str(e)}")
        
        raise Exception(f"OpenRouter vision API error: {str(last_error)}")


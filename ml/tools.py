"""
Tools/functions that can be called by the AI assistant
"""
import re
import requests
import time
import threading
from typing import Dict, Optional


def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """
    Parse time string in hh:mm:ss format to total seconds
    
    Args:
        time_str: Time string in format hh:mm:ss, mm:ss, or ss
    
    Returns:
        Total seconds or None if invalid format
    """
    # Remove whitespace
    time_str = time_str.strip()
    
    # Pattern to match hh:mm:ss, mm:ss, or just seconds
    pattern = r'^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$'
    match = re.match(pattern, time_str)
    
    if match:
        parts = match.groups()
        if parts[2] is not None:
            # hh:mm:ss format
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            if minutes >= 60 or seconds >= 60:
                return None
            return hours * 3600 + minutes * 60 + seconds
        else:
            # mm:ss format
            minutes, seconds = int(parts[0]), int(parts[1])
            if seconds >= 60:
                return None
            return minutes * 60 + seconds
    
    # Try to match just a number (seconds)
    if time_str.isdigit():
        return int(time_str)
    
    return None


def extract_time_from_text(text: str) -> Optional[str]:
    """
    Extract time in hh:mm:ss format from text
    
    Args:
        text: User input text
    
    Returns:
        Time string in hh:mm:ss format or None
    """
    # Pattern to find time in various formats
    patterns = [
        r'(\d{1,2}):(\d{2}):(\d{2})',  # hh:mm:ss
        r'(\d{1,2}):(\d{2})',           # mm:ss
        r'(\d+)\s*(?:seconds?|sec)',    # "30 seconds"
        r'(\d+)\s*(?:minutes?|min)',    # "5 minutes"
        r'(\d+)\s*(?:hours?|hr)',       # "2 hours"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            if ':' in match.group(0):
                # Already in time format
                time_str = match.group(0)
                # Normalize to hh:mm:ss
                parts = time_str.split(':')
                if len(parts) == 2:
                    # mm:ss -> 00:mm:ss
                    return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                elif len(parts) == 3:
                    # hh:mm:ss
                    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
            else:
                # Extract number and unit
                num = int(match.group(1))
                unit = match.group(0).lower()
                
                if 'hour' in unit or 'hr' in unit:
                    return f"{num:02d}:00:00"
                elif 'minute' in unit or 'min' in unit:
                    return f"00:{num:02d}:00"
                elif 'second' in unit or 'sec' in unit:
                    return f"00:00:{num:02d}"
    
    return None


def _timer_worker(seconds: int, formatted_time: str):
    """
    Background worker that waits for the timer and sends to frontend
    
    Args:
        seconds: Total seconds for the timer
        formatted_time: Formatted time string (hh:mm:ss)
    """
    # Wait for the timer duration
    time.sleep(seconds)
    
    # Send to frontend when timer completes
    payload = {
        "time": formatted_time,
        "seconds": seconds
    }
    
    try:
        response = requests.post(
            "http://localhost:4000/setTimer",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
    except:
        # Frontend not available, but timer still worked
        pass


def set_timer(time_str: str) -> Dict:
    """
    Set a timer (runs in background, returns immediately)
    
    Args:
        time_str: Time in hh:mm:ss format
    
    Returns:
        Dict with success status and message
    """
    # Parse time to ensure it's valid
    seconds = parse_time_to_seconds(time_str)
    
    if seconds is None:
        return {
            "success": False,
            "error": f"Invalid time format: {time_str}. Expected hh:mm:ss, mm:ss, or seconds."
        }
    
    # Convert back to hh:mm:ss format for consistency
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    formatted_time = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    # Start timer in background thread (non-blocking)
    timer_thread = threading.Thread(
        target=_timer_worker,
        args=(seconds, formatted_time),
        daemon=True
    )
    timer_thread.start()
    
    return {
        "success": True,
        "message": f"Timer set for {formatted_time}",
        "time": formatted_time,
        "seconds": seconds
    }


# Tool definition for OpenRouter function calling
TIMER_TOOL = {
    "type": "function",
    "function": {
        "name": "set_timer",
        "description": "Set a timer for a specified duration. Parse time from user input in hh:mm:ss format, mm:ss format, or natural language (e.g., '5 minutes', '30 seconds', '1 hour'). Always use this function when the user wants to set a timer.",
        "parameters": {
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "description": "Time duration in hh:mm:ss format (e.g., '00:05:00' for 5 minutes, '01:30:00' for 1 hour 30 minutes, '00:00:30' for 30 seconds). Convert natural language times to this format."
                }
            },
            "required": ["time"]
        }
    }
}


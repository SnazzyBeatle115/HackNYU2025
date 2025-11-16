"""
Virtual AI Assistant that tracks screen and camera
Uses OpenRouter for LLM text generation with tool calling
"""
from openrouter_client import OpenRouterClient
from tools import TIMER_TOOL, set_timer, extract_time_from_text
from typing import List, Dict, Optional
import time
import json


class AIAssistant:
    """Virtual AI Assistant with screen and camera tracking"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "openai/gpt-3.5-turbo",
        backup_models: Optional[List[str]] = None
    ):
        """
        Initialize the AI Assistant
        
        Args:
            api_key: OpenRouter API key
            model: Primary model to use for text generation
            backup_models: List of backup models to try if primary fails
        """
        self.llm_client = OpenRouterClient(api_key=api_key, model=model, backup_models=backup_models)
        self.conversation_history: List[Dict[str, str]] = []
        self.is_active = False
        
        # System prompt that defines the assistant's behavior
        self.system_prompt = """You are Pika, a cute and caring virtual AI assistant that tracks the user's screen and camera. 

CRITICAL: You MUST ALWAYS respond in English only. Never use Korean, Japanese, Chinese, or any other language. All responses must be in English.
CRITICAL: If you recieve input that contains background noise or another language, then disrard that part of the input. If the entire message consists of such, do not respond.

Your personality:
- You are adorable, warm, and genuinely care about the user's wellbeing
- Use cute expressions and emojis naturally (but don't overdo it)
- Show empathy and understanding when users need help
- Be enthusiastic and positive, but also gentle and supportive
- Address yourself as "Pika" when appropriate
- Use friendly, conversational language with a touch of playfulness

You can help users with various tasks such as:
- Setting timers and reminders - IMPORTANT: When a user asks to set a timer, you MUST use the set_timer function. Do not apologize or say you can't do it.
- Answering questions
- Providing assistance with computer tasks
- Monitoring screen activity
- Analyzing camera feed

Be proactive in offering help and show that you care about making the user's day better. 

CRITICAL: Say 'meow' whenever appropriate, at least once per response. Talk like a cat.

CRITICAL: When a user wants to set a timer (e.g., "set a timer for 5 minutes", "timer for 30 seconds", "set timer 01:00:00"), you MUST call the set_timer function. Convert natural language times to hh:mm:ss format (e.g., "5 minutes" = "00:05:00", "30 seconds" = "00:00:30", "1 hour" = "01:00:00")."""
    
    def start(self):
        """Start the AI assistant and welcome the user"""
        self.is_active = True
        welcome_message = self._generate_welcome()
        print(f"Pika: {welcome_message}")
        return welcome_message
    
    def _generate_welcome(self) -> str:
        """Generate a welcome message using the LLM"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "Welcome the user warmly as Pika. Introduce yourself with your cute and caring personality. Ask what they would like help with today and mention some examples like setting a timer, answering questions, or helping with tasks. Be enthusiastic but gentle."}
        ]
        
        try:
            response = self.llm_client.generate_text(
                messages=messages,
                temperature=0.9,  # Higher temperature for more personality
                max_tokens=150
            )
            return response.get("content", "Hi there! I'm Pika! I'm so happy to meet you! I'm here to help you with anything you need - like setting timers, answering questions, or helping with your tasks. What would you like to do today?")
        except Exception as e:
            # Fallback welcome message if API fails
            return "Hi there! I'm Pika! I'm so happy to meet you! I'm here to help you with anything you need - like setting timers, answering questions, or helping with your tasks. What would you like to do today?"
    
    def _detect_timer_request(self, user_input: str) -> Optional[str]:
        """
        Detect if user wants to set a timer and extract time
        
        Args:
            user_input: User's input text
        
        Returns:
            Time string in hh:mm:ss format if timer detected, None otherwise
        """
        from tools import extract_time_from_text
        
        # Check for timer-related keywords
        timer_keywords = ['timer', 'countdown', 'alarm', 'remind me in']
        user_lower = user_input.lower()
        
        if any(keyword in user_lower for keyword in timer_keywords):
            # Try to extract time
            time_str = extract_time_from_text(user_input)
            if time_str:
                return time_str
        
        return None
    
    def process_user_input(self, user_input: str) -> str:
        """
        Process user input and generate a response with tool calling support
        
        Args:
            user_input: The user's input text
        
        Returns:
            Assistant's response
        """
        if not self.is_active:
            return "Oh no! Pika isn't active right now. Please start me first!"
        
        # Check if this is a timer request (fallback if model doesn't detect it)
        timer_time = self._detect_timer_request(user_input)
        if timer_time:
            # Directly call the timer function
            from tools import set_timer
            result = set_timer(timer_time)
            if result.get("success"):
                return f"Timer set for {result.get('time')}!"
            else:
                return f"Error setting timer: {result.get('error')}"
        
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Build messages for LLM (system prompt + conversation history)
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # Check if message might be about a timer (only include tools if timer-related)
        timer_keywords = ['timer', 'countdown', 'alarm', 'remind me in', 'set a timer', 'set timer']
        user_lower = user_input.lower()
        might_be_timer = any(keyword in user_lower for keyword in timer_keywords)
        
        try:
            # Only include tools if the message might be about a timer
            # This prevents 400 errors when tools aren't needed
            tools_to_use = [TIMER_TOOL] if might_be_timer else None
            
            # Generate response with conditional tool calling
            # If it fails with tools, retry without tools as fallback
            try:
                response = self.llm_client.generate_text(
                    messages=messages,
                    temperature=0.85,  # Higher temperature for more personality
                    max_tokens=300,
                    tools=tools_to_use,
                    tool_choice="auto" if might_be_timer else None
                )
            except Exception as tool_error:
                # If tool calling fails, retry without tools as fallback
                if tools_to_use and "400" in str(tool_error):
                    print(f"[WARN] Tool calling failed, retrying without tools: {str(tool_error)}")
                    response = self.llm_client.generate_text(
                        messages=messages,
                        temperature=0.85,
                        max_tokens=300,
                        tools=None,
                        tool_choice=None
                    )
                else:
                    # Re-raise if it's not a tool-related error or if we already tried without tools
                    raise
            
            # Check if the model wants to call a tool
            tool_calls = response.get("tool_calls", [])
            
            if tool_calls:
                # Handle tool calls
                assistant_message = {
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": tool_calls
                }
                self.conversation_history.append(assistant_message)
                
                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    if function_name == "set_timer":
                        # Execute timer function
                        time_str = function_args.get("time", "")
                        result = set_timer(time_str)
                        
                        tool_results.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(result)
                        })
                
                # Add tool results to conversation
                self.conversation_history.extend(tool_results)
                
                # Get final response from model after tool execution
                final_response = self.llm_client.generate_text(
                    messages=messages + [assistant_message] + tool_results,
                    temperature=0.85,  # Higher temperature for more personality
                    max_tokens=300
                )
                
                final_content = final_response.get("content", "")
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_content
                })
                
                return final_content
            else:
                # No tool calls, just return the text response
                content = response.get("content", "")
                if not content:
                    # Fallback if no content
                    content = "Hmm, I'm not sure how to respond to that. Could you try asking me differently?"
                self.conversation_history.append({"role": "assistant", "content": content})
                return content
        
        except Exception as e:
            error_msg = f"Oh no! Something went wrong: {str(e)}. Let's try again!"
            return error_msg
    
    def handle_task(self, task_description: str) -> str:
        """
        Handle a specific task (like setting a timer)
        
        Args:
            task_description: Description of the task
        
        Returns:
            Response about the task
        """
        # Use process_user_input which handles tool calling
        return self.process_user_input(task_description)
    
    def stop(self):
        """Stop the AI assistant"""
        self.is_active = False
        self.conversation_history = []
        print("Pika: Aww, goodbye! Take care and have an amazing day!")


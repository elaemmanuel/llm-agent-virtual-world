# backend/services/llm.py
"""
LLM Service - Claude API Integration.

This service handles:
1. Calling Claude with observations and tools
2. Parsing tool use responses
3. Error handling for LLM failures
4. Token management

Why separate this from agent.py?
- Testability: Mock LLM responses easily
- Reusability: Use LLM service elsewhere in app
- Clarity: Clear separation of concerns

Design choice: Tool Use
We use Claude's tool_use feature because:
- More reliable than asking Claude to generate JSON
- Claude formats arguments consistently
- Easy to validate and parse
- Extensible (add new tools without rewriting prompts)
"""

import anthropic
from typing import Dict, List, Tuple, Optional, Any
import json

from config import settings
from schemas.observation import Observation
from schemas.action import AGENT_TOOLS


class LLMService:
    """
    Service for calling Claude.
    
    Usage:
    ```python
    llm = LLMService()
    
    action_type, action_args = await llm.reason_and_act(
        prompt="Your prompt here",
        tools=AGENT_TOOLS,
        observation=observation
    )
    ```
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = None
    ):
        """
        Initialize LLM service.
        
        Args:
            api_key: Anthropic API key (defaults to config)
            model: Model name (defaults to config)
            temperature: LLM temperature 0-1 (defaults to config)
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.temperature = temperature or settings.AGENT_TEMPERATURE
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    async def reason_and_act(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        observation: Observation,
        max_retries: int = 3
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Ask Claude to reason about the situation and decide on an action.
        
        Args:
            prompt: The prompt describing the situation
            tools: Available tools (actions) Claude can use
            observation: Current observation (for context)
            max_retries: How many times to retry on failure
        
        Returns:
            Tuple of (action_type, action_args) or (None, None) if failure
        
        Flow:
        1. Send prompt + tools to Claude
        2. Claude returns tool use request
        3. Parse and validate the request
        4. Return action type and arguments
        
        Example response from Claude:
        ```
        {
            "type": "tool_use",
            "name": "move",
            "input": {
                "direction": "forward"
            }
        }
        ```
        """
        for attempt in range(max_retries):
            try:
                # Call Claude with tool use
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,  # Enough for reasoning + tool call
                    temperature=self.temperature,
                    tools=tools,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                # Parse response
                action_type, action_args = self._parse_response(response)
                
                if action_type and action_args is not None:
                    return action_type, action_args
                
                # If parsing failed, retry
                print(f"Failed to parse LLM response, retrying ({attempt + 1}/{max_retries})")
                continue
            
            except anthropic.APIError as e:
                print(f"API error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                continue
            
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                continue
        
        # All retries failed
        print(f"Failed to get valid action after {max_retries} attempts")
        return None, None
    
    def _parse_response(self, response) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Parse Claude's response.
        
        Claude returns a message with multiple content blocks:
        - text blocks (reasoning)
        - tool_use blocks (action requests)
        
        We extract the tool_use block and return action details.
        
        Args:
            response: Response from Claude API
        
        Returns:
            Tuple of (action_type, action_args)
        
        Example:
        Claude sends:
        ```
        [
            {"type": "text", "text": "I see a red cube. I'll move towards it."},
            {"type": "tool_use", "id": "...", "name": "move", "input": {"direction": "forward"}}
        ]
        ```
        
        We extract: ("move", {"direction": "forward"})
        """
        # Look for tool use in response
        for block in response.content:
            if block.type == "tool_use":
                action_type = block.name
                action_args = block.input
                
                # Validate action
                if self._validate_action(action_type, action_args):
                    return action_type, action_args
                else:
                    print(f"Invalid action validation: {action_type} {action_args}")
                    return None, None
        
        # No tool use found in response
        print("No tool use in Claude response")
        return None, None
    
    def _validate_action(self, action_type: str, action_args: Dict) -> bool:
        """
        Validate that the action is one of our allowed tools.
        
        Args:
            action_type: Name of the tool/action
            action_args: Arguments to the tool
        
        Returns:
            True if valid, False otherwise
        
        Validation:
        - Action name must exist in AGENT_TOOLS
        - Arguments must match the schema
        """
        # Check if action exists
        valid_actions = {tool["name"] for tool in AGENT_TOOLS}
        if action_type not in valid_actions:
            print(f"Unknown action: {action_type}")
            return False
        
        # For now, trust Claude's formatting
        # (Claude should format correctly given our tool definitions)
        # In production, you might add stricter validation
        
        return True
    
    def get_available_tools(self) -> List[Dict]:
        """
        Get list of available tools.
        
        Returns:
            Tool definitions for Claude
        """
        return AGENT_TOOLS
    
    def format_tool_result(
        self,
        tool_use_id: str,
        success: bool,
        message: str,
        observation: Optional[Dict] = None
    ) -> Dict:
        """
        Format a tool result to send back to Claude.
        
        If Claude's action succeeds, we send back:
        - What happened
        - Updated observation
        
        This allows Claude to reason about the effects of its action
        and plan the next step.
        
        Usage in multi-turn conversation:
        ```python
        # Claude requests tool
        response1 = client.messages.create(
            messages=[{"role": "user", "content": "..."}],
            tools=AGENT_TOOLS
        )
        
        # We execute the tool
        action_type, args = parse_response(response1)
        result = env.execute_action(action_type, args)
        
        # Send result back to Claude
        response2 = client.messages.create(
            messages=[
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": response1.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": format_tool_result(...)
                        }
                    ]
                }
            ]
        )
        ```
        """
        return {
            "tool_use_id": tool_use_id,
            "success": success,
            "message": message,
            "observation": observation
        }
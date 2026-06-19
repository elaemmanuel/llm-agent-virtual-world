# backend/schemas/action.py
"""
Action schemas - what the agent can do in the world.

When the LLM wants to interact with the environment, it uses "tools".
Each tool is an action the agent can take.

We use Anthropic's tool_use feature, which means:
1. The LLM receives a list of available tools
2. The LLM decides which tool to use with what arguments
3. We validate the arguments with Pydantic
4. The environment executes the action

Minimal actions for Phase 1:
- move(direction): Walk forward/backward/left/right/up/down
- rotate(direction): Turn to face a direction
- pickup(object_id): Grab an object
- use(object_id): Interact with an object (open door, etc.)
- observe(): Get current environment state
- think(reasoning): Let agent explain its reasoning

These are "minimal" but sufficient to complete tasks.
We'll extend with more actions in Phase 3.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ===== ENUMS =====

class MovementDirection(str, Enum):
    """Directions the agent can move."""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class RotationDirection(str, Enum):
    """Directions to rotate."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"


# ===== TOOL DEFINITIONS =====
# These define what the LLM can request via tool_use

class MoveAction(BaseModel):
    """
    Move in a direction.
    
    Example: agent wants to walk forward 1 step
    Tool call: {"name": "move", "input": {"direction": "forward"}}
    """
    direction: MovementDirection = Field(
        ...,
        description="Direction to move: forward, backward, left, right, up, or down"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"direction": "forward"}
        }


class RotateAction(BaseModel):
    """
    Rotate to face a direction.
    
    Example: agent wants to turn to face north
    Tool call: {"name": "rotate", "input": {"direction": "north"}}
    """
    direction: RotationDirection = Field(
        ...,
        description="Direction to face"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"direction": "north"}
        }


class PickupAction(BaseModel):
    """
    Pick up an object.
    
    Example: agent sees red cube (id=1) and wants to grab it
    Tool call: {"name": "pickup", "input": {"object_id": 1}}
    
    The object_id comes from the observation (visible_objects[].id)
    """
    object_id: int = Field(
        ...,
        description="ID of the object to pick up (from observation.visible_objects)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"object_id": 1}
        }


class UseAction(BaseModel):
    """
    Interact with an object.
    
    Example: agent sees a door (id=2) and wants to open it
    Tool call: {"name": "use", "input": {"object_id": 2}}
    
    The environment handles what happens based on object type
    (e.g., opening doors, collecting items)
    """
    object_id: int = Field(
        ...,
        description="ID of the object to interact with"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"object_id": 2}
        }


class ObserveAction(BaseModel):
    """
    Get current observation.
    
    Example: agent wants to look around and see what's nearby
    Tool call: {"name": "observe", "input": {}}
    
    This is useful when the agent is unsure of its surroundings
    or wants to refresh its perception.
    
    Note: This action doesn't require any input fields.
    When Claude uses this tool, it will send: {"name": "observe", "input": {}}
    """
    
    class Config:
        json_schema_extra = {
            "example": {}
        }


class ThinkAction(BaseModel):
    """
    Agent explains its reasoning.
    
    Example: agent wants to document its thought process
    Tool call: {"name": "think", "input": {"reasoning": "I see a door. I need a key. Let me look for a key first."}}
    
    This doesn't change the environment but helps us understand
    the agent's decision-making process (useful for debugging and analysis).
    """
    reasoning: str = Field(
        ...,
        description="Agent's internal reasoning or thought process"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"reasoning": "The blue door is locked. I'll look for a key elsewhere."}
        }


# ===== TOOL DEFINITIONS FOR LLM =====
"""
These are the tool definitions sent to Claude so it knows
what it can do. Format matches Anthropic's tool_use API.
"""

AGENT_TOOLS = [
    {
        "name": "move",
        "description": "Move the agent in a specified direction within the world",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["forward", "backward", "left", "right", "up", "down"],
                    "description": "Direction to move"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "rotate",
        "description": "Rotate the agent to face a specified direction",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["north", "south", "east", "west", "up", "down"],
                    "description": "Direction to face"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "pickup",
        "description": "Pick up an object visible in the environment",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_id": {
                    "type": "integer",
                    "description": "ID of the visible object to pick up"
                }
            },
            "required": ["object_id"]
        }
    },
    {
        "name": "use",
        "description": "Interact with an object (open door, activate switch, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_id": {
                    "type": "integer",
                    "description": "ID of the object to interact with"
                }
            },
            "required": ["object_id"]
        }
    },
    {
        "name": "observe",
        "description": "Get the current observation of the environment",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "think",
        "description": "Record the agent's reasoning or thought process",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Agent's internal reasoning"
                }
            },
            "required": ["reasoning"]
        }
    }
]


# ===== ACTION EXECUTION RESULTS =====

class ActionResult(BaseModel):
    """
    Result of executing an action.
    
    The environment executes an action and returns a result
    describing what happened.
    
    Example:
    ```json
    {
        "success": true,
        "action": "move",
        "message": "Moved forward 1 unit to position [4, 0, 5]",
        "new_position": [4, 0, 5],
        "observation": {...}
    }
    ```
    """
    success: bool = Field(..., description="Whether the action succeeded")
    action: str = Field(..., description="Action name that was executed")
    message: str = Field(..., description="Human-readable description of what happened")
    new_position: Optional[List[float]] = Field(None, description="Agent's new position if moved")
    observation: Optional[Dict[str, Any]] = Field(None, description="Updated environment observation")
    error: Optional[str] = Field(None, description="Error message if action failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "action": "move",
                "message": "Moved forward successfully",
                "new_position": [4, 0, 5],
                "observation": None,  # Full observation would go here
                "error": None
            }
        }
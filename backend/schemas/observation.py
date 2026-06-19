# backend/schemas/observation.py
"""
Observation schemas - how the agent perceives the world.

An observation is a JSON snapshot of the agent's current state
and what it can see. The LLM receives this as context.

Design principle:
- Simple semantic information (not raw pixels)
- Include only what the agent needs to know
- Extensible for adding features later

Example observation:
```json
{
  "agent_position": [3, 0, 5],
  "agent_direction": "north",
  "visible_objects": [
    {
      "id": 1,
      "type": "cube",
      "color": "red",
      "position": [5, 0, 5],
      "distance": 2.0
    }
  ],
  "inventory": ["key"],
  "current_task": "Navigate to the red cube"
}
```
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ===== ENUMS (FIXED OPTIONS) =====

class DirectionEnum(str, Enum):
    """Cardinal directions the agent can face."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    UP = "up"
    DOWN = "down"


class ObjectTypeEnum(str, Enum):
    """Types of objects in the world."""
    CUBE = "cube"
    SPHERE = "sphere"
    DOOR = "door"
    WALL = "wall"
    PLATFORM = "platform"
    NPC = "npc"  # Non-player character (other agents)
    KEY = "key"  # Keys and items


class DoorStateEnum(str, Enum):
    """Possible states of a door."""
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


# ===== MODELS =====

class Vector3(BaseModel):
    """
    3D coordinate (x, y, z).
    
    Used for positions, velocities, etc.
    """
    x: float
    y: float
    z: float
    
    def __init__(self, x: float = 0, y: float = 0, z: float = 0, **data):
        """Allow both dict and positional arguments."""
        if 'x' not in data:
            data['x'] = x
        if 'y' not in data:
            data['y'] = y
        if 'z' not in data:
            data['z'] = z
        super().__init__(**data)
    
    def to_list(self) -> List[float]:
        """Convert to [x, y, z] list for JSON serialization."""
        return [self.x, self.y, self.z]


class VisibleObject(BaseModel):
    """
    An object the agent can perceive.
    
    Fields:
    - id: Unique identifier (for referencing in actions)
    - type: What kind of object (cube, door, etc.)
    - color: Visual appearance (red, blue, etc.)
    - position: 3D location [x, y, z]
    - distance: How far from agent (in units)
    - state: Current state if applicable (door open/closed)
    - properties: Extra attributes (e.g., {"unlocked": False})
    """
    id: int = Field(..., description="Unique object ID for reference in actions")
    type: ObjectTypeEnum = Field(..., description="Type of object")
    color: Optional[str] = Field(None, description="Visual color")
    position: Vector3 = Field(..., description="3D position in world")
    distance: float = Field(..., description="Distance from agent")
    state: Optional[str] = Field(None, description="Current state if applicable")
    properties: Optional[dict] = Field(default_factory=dict, description="Extra attributes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "cube",
                "color": "red",
                "position": {"x": 5, "y": 0, "z": 5},
                "distance": 2.0,
                "state": None,
                "properties": {}
            }
        }


class AgentState(BaseModel):
    """
    Information about the agent itself.
    
    Fields:
    - position: Agent's current location
    - direction: Which way it's facing (for reference)
    - health/stamina: Optional for future use
    """
    position: Vector3 = Field(..., description="Agent's current position")
    direction: DirectionEnum = Field(..., description="Direction agent is facing")
    health: Optional[int] = Field(100, description="Health points (future use)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "position": {"x": 3, "y": 0, "z": 5},
                "direction": "north",
                "health": 100
            }
        }


class EnvironmentContext(BaseModel):
    """
    Information about the current task and world.
    
    Fields:
    - current_task: What the agent is trying to accomplish
    - time_elapsed: How many steps taken so far
    - world_size: Boundaries of the world
    """
    current_task: str = Field(..., description="Current goal or task description")
    time_elapsed: int = Field(default=0, description="Number of steps taken")
    step_limit: int = Field(default=100, description="Max steps allowed")
    world_size: Vector3 = Field(..., description="Dimensions of the world")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_task": "Navigate to the red cube and report its contents",
                "time_elapsed": 3,
                "step_limit": 100,
                "world_size": {"x": 20, "y": 10, "z": 20}
            }
        }


class Observation(BaseModel):
    """
    Complete observation of the environment.
    
    This is what gets sent to the LLM agent each step.
    The agent reads this to understand:
    1. Its own state (where it is, what it's holding)
    2. What it sees (nearby objects)
    3. What it's trying to do (current task)
    
    Example usage in LLM prompt:
    ```
    "You are an agent in a 3D world. Here's what you observe:
    
    Your state: Position [3, 0, 5], facing north
    Objects you see:
    - Red cube at [5, 0, 5] (2m away)
    - Blue door at [8, 0, 5] (5m away, locked)
    Inventory: [key]
    Task: Navigate to the red cube
    
    What do you do next?"
    ```
    """
    agent_state: AgentState = Field(..., description="Information about the agent")
    visible_objects: List[VisibleObject] = Field(
        default_factory=list,
        description="Objects the agent can perceive"
    )
    inventory: List[str] = Field(
        default_factory=list,
        description="Items the agent is holding"
    )
    environment_context: EnvironmentContext = Field(..., description="Task and world info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_state": {
                    "position": {"x": 3, "y": 0, "z": 5},
                    "direction": "north",
                    "health": 100
                },
                "visible_objects": [
                    {
                        "id": 1,
                        "type": "cube",
                        "color": "red",
                        "position": {"x": 5, "y": 0, "z": 5},
                        "distance": 2.0,
                        "state": None,
                        "properties": {}
                    },
                    {
                        "id": 2,
                        "type": "door",
                        "color": "blue",
                        "position": {"x": 8, "y": 0, "z": 5},
                        "distance": 5.0,
                        "state": "locked",
                        "properties": {}
                    }
                ],
                "inventory": ["key"],
                "environment_context": {
                    "current_task": "Navigate to the red cube and report its contents",
                    "time_elapsed": 0,
                    "step_limit": 100,
                    "world_size": {"x": 20, "y": 10, "z": 20}
                }
            }
        }
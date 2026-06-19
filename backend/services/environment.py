# backend/services/environment.py
"""
Environment Service - The Game Engine.

This service manages:
1. World state (object positions, agent position)
2. Action execution (move, rotate, pickup, use)
3. Observation generation (what agent perceives)
4. Physics/collision (can agent move there?)

Think of this as the "game engine" that handles all world updates.
The agent doesn't directly manipulate the world—it requests actions,
and this service executes them and returns results.

Architecture principle: The environment is the SOURCE OF TRUTH.
Everything the agent knows comes from observations from the environment.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import math
from enum import Enum

from schemas.observation import (
    Observation, AgentState, VisibleObject, EnvironmentContext,
    Vector3, DirectionEnum
)
from schemas.action import ActionResult


# ===== DATA STRUCTURES =====

@dataclass
class Agent:
    """
    Agent state in the world.
    
    Attributes:
    - position: [x, y, z] in the world
    - direction: Which way facing (for reference)
    - inventory: Items agent is holding
    - health: Health points (for future use)
    """
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # [x, y, z]
    direction: DirectionEnum = DirectionEnum.NORTH
    inventory: List[str] = field(default_factory=list)  # Item names/IDs
    health: int = 100
    
    def move(self, direction: str, step_size: float = 1.0) -> List[float]:
        """
        Calculate new position after moving in a direction.
        
        Args:
            direction: "forward", "backward", "left", "right", "up", "down"
            step_size: How far to move (default 1 unit)
        
        Returns:
            New position [x, y, z]
        
        Movement is relative to which way the agent is facing:
        - forward: Positive Z
        - backward: Negative Z
        - left: Negative X
        - right: Positive X
        - up: Positive Y
        - down: Negative Y
        """
        x, y, z = self.position
        
        if direction == "forward":
            z += step_size
        elif direction == "backward":
            z -= step_size
        elif direction == "left":
            x -= step_size
        elif direction == "right":
            x += step_size
        elif direction == "up":
            y += step_size
        elif direction == "down":
            y -= step_size
        
        return [x, y, z]
    
    def distance_to(self, target_position: List[float]) -> float:
        """
        Calculate distance to another position (Euclidean distance).
        
        Formula: sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)
        """
        dx = target_position[0] - self.position[0]
        dy = target_position[1] - self.position[1]
        dz = target_position[2] - self.position[2]
        return math.sqrt(dx**2 + dy**2 + dz**2)


@dataclass
class WorldObject:
    """
    An object in the world.
    
    Attributes:
    - id: Unique identifier
    - name: Display name
    - object_type: Type ("cube", "door", etc.)
    - position: [x, y, z]
    - color: Visual appearance
    - state: Current state (e.g., "locked", "open")
    - pickupable: Can agent pick this up?
    - interactable: Can agent use this? (open, activate, etc.)
    - properties: Extra data
    """
    id: int
    name: str
    object_type: str  # "cube", "door", "wall", etc.
    position: List[float]  # [x, y, z]
    color: Optional[str] = None
    state: Optional[str] = None  # "locked", "open", "collected", etc.
    pickupable: bool = False
    interactable: bool = False
    properties: Dict = field(default_factory=dict)  # Extra attributes
    
    def to_visible_object(self, agent_position: List[float]) -> VisibleObject:
        """
        Convert this world object to what the agent can see.
        
        Includes distance calculation so agent knows how far away it is.
        """
        distance = self._distance_to(agent_position)
        
        return VisibleObject(
            id=self.id,
            type=self.object_type,
            color=self.color,
            position=Vector3(x=self.position[0], y=self.position[1], z=self.position[2]),
            distance=distance,
            state=self.state,
            properties=self.properties
        )
    
    def _distance_to(self, position: List[float]) -> float:
        """Calculate distance to this object."""
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        dz = self.position[2] - position[2]
        return math.sqrt(dx**2 + dy**2 + dz**2)


# ===== MAIN ENVIRONMENT CLASS =====

class VirtualEnvironment:
    """
    The Virtual Environment - manages the entire world.
    
    This is the core of Phase 1. It:
    1. Stores world state (agent + objects)
    2. Executes actions
    3. Generates observations
    4. Validates actions (collision detection, etc.)
    
    Usage:
    ```python
    env = VirtualEnvironment()
    env.add_object(WorldObject(id=1, name="Red Cube", ...))
    
    # Agent observes
    obs = env.get_observation("Navigate to the red cube")
    
    # Agent acts
    result = env.execute_action("move", {"direction": "forward"})
    
    # New observation
    obs = env.get_observation(current_obs.environment_context.current_task)
    ```
    """
    
    def __init__(
        self,
        world_size_x: int = 20,
        world_size_y: int = 10,
        world_size_z: int = 20,
    ):
        """
        Initialize the environment.
        
        Args:
            world_size_x: Width of world
            world_size_y: Height of world
            world_size_z: Depth of world
        """
        self.world_size = Vector3(x=world_size_x, y=world_size_y, z=world_size_z)
        
        # Agent state
        self.agent = Agent(
            position=[world_size_x / 2, 0.0, world_size_z / 2],  # Start in middle
            direction=DirectionEnum.NORTH,
        )
        
        # World objects
        self.objects: Dict[int, WorldObject] = {}
        self.next_object_id = 1
        
        # Step counter
        self.step_count = 0
        self.max_steps = 100
    
    # ===== OBJECT MANAGEMENT =====
    
    def add_object(self, obj: WorldObject) -> int:
        """
        Add an object to the world.
        
        Args:
            obj: WorldObject to add
        
        Returns:
            Object ID
        
        Example:
        ```python
        cube = WorldObject(
            id=1,
            name="Red Cube",
            object_type="cube",
            position=[5, 0, 5],
            color="red",
            pickupable=True
        )
        env.add_object(cube)
        ```
        """
        obj_id = obj.id if obj.id else self.next_object_id
        self.objects[obj_id] = obj
        self.next_object_id = max(self.next_object_id, obj_id + 1)
        return obj_id
    
    def get_object(self, object_id: int) -> Optional[WorldObject]:
        """Get an object by ID."""
        return self.objects.get(object_id)
    
    def remove_object(self, object_id: int) -> bool:
        """Remove an object from the world."""
        if object_id in self.objects:
            del self.objects[object_id]
            return True
        return False
    
    def get_nearby_objects(self, max_distance: float = 10.0) -> List[WorldObject]:
        """
        Get objects within a certain distance of the agent.
        
        Simulates "field of view" - agent can only see nearby objects.
        
        Args:
            max_distance: Max distance to see objects (in world units)
        
        Returns:
            List of nearby objects, sorted by distance
        """
        nearby = []
        for obj in self.objects.values():
            distance = self.agent.distance_to(obj.position)
            if distance <= max_distance:
                nearby.append(obj)
        
        # Sort by distance (closest first)
        nearby.sort(key=lambda o: self.agent.distance_to(o.position))
        return nearby
    
    # ===== ACTION EXECUTION =====
    
    def execute_action(self, action_type: str, action_args: Dict) -> ActionResult:
        """
        Execute an action requested by the agent.
        
        Args:
            action_type: Type of action ("move", "rotate", "pickup", etc.)
            action_args: Arguments for the action
        
        Returns:
            ActionResult with success/failure and updated state
        
        This is the main method called by the agent service.
        """
        self.step_count += 1
        
        # Store old position for tracking
        old_position = self.agent.position.copy()
        
        # Execute action based on type
        if action_type == "move":
            result = self._execute_move(action_args)
        elif action_type == "rotate":
            result = self._execute_rotate(action_args)
        elif action_type == "pickup":
            result = self._execute_pickup(action_args)
        elif action_type == "use":
            result = self._execute_use(action_args)
        elif action_type == "observe":
            result = self._execute_observe(action_args)
        elif action_type == "think":
            result = self._execute_think(action_args)
        else:
            result = ActionResult(
                success=False,
                action=action_type,
                message=f"Unknown action: {action_type}",
                error=f"Action '{action_type}' is not recognized"
            )
        
        return result
    
    def _execute_move(self, args: Dict) -> ActionResult:
        """
        Execute a move action.
        
        Validates:
        - Direction is valid
        - New position is within world bounds
        - No collision with obstacles
        """
        direction = args.get("direction", "").lower()
        
        # Validate direction
        valid_directions = ["forward", "backward", "left", "right", "up", "down"]
        if direction not in valid_directions:
            return ActionResult(
                success=False,
                action="move",
                message=f"Invalid direction: {direction}",
                error=f"Direction must be one of: {valid_directions}"
            )
        
        # Calculate new position
        new_position = self.agent.move(direction, step_size=1.0)
        
        # Check bounds
        if not self._is_within_bounds(new_position):
            return ActionResult(
                success=False,
                action="move",
                message=f"Cannot move {direction} - would go out of bounds",
                error="Out of bounds",
                new_position=self.agent.position
            )
        
        # Check collision with objects
        collision_obj = self._check_collision(new_position)
        if collision_obj:
            return ActionResult(
                success=False,
                action="move",
                message=f"Cannot move {direction} - would collide with {collision_obj.name}",
                error=f"Collision with {collision_obj.name}",
                new_position=self.agent.position
            )
        
        # Move succeeded
        old_position = self.agent.position.copy()
        self.agent.position = new_position
        
        return ActionResult(
            success=True,
            action="move",
            message=f"Moved {direction} to position {new_position}",
            new_position=new_position
        )
    
    def _execute_rotate(self, args: Dict) -> ActionResult:
        """
        Execute a rotate action.
        
        Changes which direction the agent is facing.
        """
        direction = args.get("direction", "").lower()
        
        # Validate direction
        valid_directions = ["north", "south", "east", "west", "up", "down"]
        if direction not in valid_directions:
            return ActionResult(
                success=False,
                action="rotate",
                message=f"Invalid direction: {direction}",
                error=f"Direction must be one of: {valid_directions}"
            )
        
        # Set new direction
        try:
            self.agent.direction = DirectionEnum(direction)
            return ActionResult(
                success=True,
                action="rotate",
                message=f"Rotated to face {direction}",
                new_position=self.agent.position
            )
        except ValueError:
            return ActionResult(
                success=False,
                action="rotate",
                message=f"Invalid direction: {direction}",
                error=f"Unknown direction: {direction}"
            )
    
    def _execute_pickup(self, args: Dict) -> ActionResult:
        """
        Execute a pickup action.
        
        Validates:
        - Object exists
        - Object is pickupable
        - Agent is close enough
        """
        object_id = args.get("object_id")
        
        if object_id is None:
            return ActionResult(
                success=False,
                action="pickup",
                message="No object_id provided",
                error="object_id is required"
            )
        
        obj = self.get_object(object_id)
        if not obj:
            return ActionResult(
                success=False,
                action="pickup",
                message=f"Object with id {object_id} not found",
                error="Object not found"
            )
        
        if not obj.pickupable:
            return ActionResult(
                success=False,
                action="pickup",
                message=f"Cannot pickup {obj.name} - not pickupable",
                error=f"{obj.name} is not pickupable"
            )
        
        # Check distance (must be close)
        distance = self.agent.distance_to(obj.position)
        if distance > 2.0:  # 2 units away
            return ActionResult(
                success=False,
                action="pickup",
                message=f"Cannot pickup {obj.name} - too far away ({distance:.1f} units)",
                error="Object is too far away"
            )
        
        # Add to inventory
        self.agent.inventory.append(obj.name)
        
        # Remove from world
        self.remove_object(object_id)
        
        return ActionResult(
            success=True,
            action="pickup",
            message=f"Picked up {obj.name}",
            new_position=self.agent.position
        )
    
    def _execute_use(self, args: Dict) -> ActionResult:
        """
        Execute a use action.
        
        Interact with objects:
        - Open doors
        - Activate switches
        - Use items
        
        For now, "use" on a locked door checks if agent has the key.
        """
        object_id = args.get("object_id")
        
        if object_id is None:
            return ActionResult(
                success=False,
                action="use",
                message="No object_id provided",
                error="object_id is required"
            )
        
        obj = self.get_object(object_id)
        if not obj:
            return ActionResult(
                success=False,
                action="use",
                message=f"Object with id {object_id} not found",
                error="Object not found"
            )
        
        if not obj.interactable:
            return ActionResult(
                success=False,
                action="use",
                message=f"Cannot use {obj.name} - not interactable",
                error=f"{obj.name} is not interactable"
            )
        
        # Check distance
        distance = self.agent.distance_to(obj.position)
        if distance > 2.0:
            return ActionResult(
                success=False,
                action="use",
                message=f"Cannot use {obj.name} - too far away",
                error="Object is too far away"
            )
        
        # Handle door interaction
        if obj.object_type == "door":
            return self._use_door(obj)
        
        # Default: unknown object type
        return ActionResult(
            success=False,
            action="use",
            message=f"Don't know how to use {obj.object_type}",
            error=f"Unknown object type: {obj.object_type}"
        )
    
    def _use_door(self, door: WorldObject) -> ActionResult:
        """
        Use a door (open/unlock/close).
        
        Logic:
        - If locked: check if agent has key
        - If unlocked: toggle open/closed
        """
        if door.state == "locked":
            # Check if agent has key
            if "key" not in self.agent.inventory:
                return ActionResult(
                    success=False,
                    action="use",
                    message="The door is locked. You need a key.",
                    error="Door is locked and you don't have a key"
                )
            
            # Unlock the door
            door.state = "open"
            self.agent.inventory.remove("key")
            
            return ActionResult(
                success=True,
                action="use",
                message="You unlocked the door with the key and opened it.",
                new_position=self.agent.position
            )
        
        elif door.state == "open":
            door.state = "closed"
            return ActionResult(
                success=True,
                action="use",
                message="You closed the door.",
                new_position=self.agent.position
            )
        
        elif door.state == "closed":
            door.state = "open"
            return ActionResult(
                success=True,
                action="use",
                message="You opened the door.",
                new_position=self.agent.position
            )
        
        return ActionResult(
            success=False,
            action="use",
            message="Unknown door state",
            error=f"Door has unknown state: {door.state}"
        )
    
    def _execute_observe(self, args: Dict) -> ActionResult:
        """
        Execute an observe action.
        
        This doesn't change state, but returns a full observation.
        """
        return ActionResult(
            success=True,
            action="observe",
            message="You look around.",
            new_position=self.agent.position,
            observation=self.get_observation("").dict()  # Full observation
        )
    
    def _execute_think(self, args: Dict) -> ActionResult:
        """
        Execute a think action.
        
        Agent records its reasoning. No state change.
        """
        reasoning = args.get("reasoning", "")
        
        return ActionResult(
            success=True,
            action="think",
            message=f"You think: '{reasoning}'",
            new_position=self.agent.position
        )
    
    # ===== VALIDATION =====
    
    def _is_within_bounds(self, position: List[float]) -> bool:
        """Check if position is within world bounds."""
        x, y, z = position
        return (
            0 <= x <= self.world_size.x and
            0 <= y <= self.world_size.y and
            0 <= z <= self.world_size.z
        )
    
    def _check_collision(self, position: List[float]) -> Optional[WorldObject]:
        """
        Check if moving to this position would collide with an object.
        
        For simplicity: collision if within 0.5 units of an obstacle.
        Returns: The object we would collide with, or None if clear.
        """
        collision_distance = 0.5
        
        for obj in self.objects.values():
            # Walls and non-pickupable objects block movement
            if obj.object_type in ["wall", "obstacle"] or not obj.pickupable:
                distance = math.sqrt(
                    (position[0] - obj.position[0])**2 +
                    (position[1] - obj.position[1])**2 +
                    (position[2] - obj.position[2])**2
                )
                if distance < collision_distance:
                    return obj
        
        return None
    
    # ===== OBSERVATION GENERATION =====
    
    def get_observation(self, current_task: str = "") -> Observation:
        """
        Generate the current observation.
        
        This is what the agent perceives. Called before each LLM request.
        
        Args:
            current_task: Description of current task
        
        Returns:
            Observation object (gets serialized to JSON for LLM)
        """
        # Get visible objects
        visible_objects = [
            obj.to_visible_object(self.agent.position)
            for obj in self.get_nearby_objects(max_distance=10.0)
        ]
        
        # Build observation
        observation = Observation(
            agent_state=AgentState(
                position=Vector3(
                    x=self.agent.position[0],
                    y=self.agent.position[1],
                    z=self.agent.position[2]
                ),
                direction=self.agent.direction,
                health=self.agent.health
            ),
            visible_objects=visible_objects,
            inventory=self.agent.inventory,
            environment_context=EnvironmentContext(
                current_task=current_task,
                time_elapsed=self.step_count,
                step_limit=self.max_steps,
                world_size=self.world_size
            )
        )
        
        return observation
    
    # ===== UTILITY =====
    
    def reset(self, x: float = None, y: float = None, z: float = None):
        """
        Reset agent to starting position.
        
        Useful for restarting a task.
        """
        if x is None:
            x = self.world_size.x / 2
        if y is None:
            y = 0.0
        if z is None:
            z = self.world_size.z / 2
        
        self.agent.position = [x, y, z]
        self.agent.inventory = []
        self.agent.health = 100
        self.step_count = 0
    
    def get_status(self) -> Dict:
        """Get current world status."""
        return {
            "agent_position": self.agent.position,
            "agent_direction": self.agent.direction.value,
            "agent_inventory": self.agent.inventory,
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "num_objects": len(self.objects),
            "world_size": {
                "x": self.world_size.x,
                "y": self.world_size.y,
                "z": self.world_size.z
            }
        }
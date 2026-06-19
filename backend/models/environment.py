# backend/models/environment.py
"""
SQLAlchemy ORM models for the virtual environment.

These represent persistent entities in the world:
- WorldObject: Items, doors, obstacles in the environment
- EnvironmentSession: Current agent run/episode
- AgentAction: Logged actions for analysis

ORM benefits:
- Type-safe queries
- Relationship handling
- Automatic migrations with Alembic
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from typing import Optional, List
import enum

from models.base import BaseModel


class WorldObject(BaseModel):
    """
    A persistent object in the virtual world.
    
    Examples: red cube, blue door, wall, platform, etc.
    
    Fields:
    - object_type: "cube", "door", "wall", etc.
    - position: [x, y, z] coordinates
    - color: Visual appearance
    - state: Current state (e.g., door locked/open)
    - properties: Extra metadata (JSON)
    
    Example:
    ```python
    door = WorldObject(
        name="Main Door",
        object_type="door",
        position_x=8, position_y=0, position_z=5,
        color="blue",
        state="locked",
        properties={"key_id": 1}
    )
    ```
    """
    __tablename__ = "world_objects"
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "cube", "door", etc.
    
    # Position (x, y, z)
    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)
    position_z: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Appearance
    color: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Current state
    state: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "locked", "open", "collected"
    
    # Extra metadata
    properties: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Is this object pickupable?
    pickupable: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Is this object interactable (e.g., can be opened)?
    interactable: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def get_position(self) -> List[float]:
        """Get position as [x, y, z] list."""
        return [self.position_x, self.position_y, self.position_z]
    
    def __repr__(self) -> str:
        return f"<WorldObject {self.name} ({self.object_type}) at {self.get_position()}>"


class EnvironmentSession(BaseModel):
    """
    A session/episode - one run of an agent on a task.
    
    When you start the agent on a task, you create a Session.
    All actions during that task are logged to this session.
    
    Fields:
    - task_description: What the agent is trying to do
    - agent_name: Which agent is running (for multi-agent support)
    - status: "running", "success", "failed", "timeout"
    - steps_taken: How many actions executed
    - max_steps: Limit (for terminating runaway loops)
    
    Example:
    ```python
    session = EnvironmentSession(
        task_description="Navigate to the red cube",
        agent_name="claude-opus-4-6",
        status="running",
        max_steps=100
    )
    ```
    """
    __tablename__ = "environment_sessions"
    
    # Session info
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Which LLM
    
    # Execution status
    status: Mapped[str] = mapped_column(String(50), default="running")  # running, success, failed, timeout
    steps_taken: Mapped[int] = mapped_column(Integer, default=0, index=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=100)
    
    # Initial state
    initial_position_x: Mapped[float] = mapped_column(Float, default=0)
    initial_position_y: Mapped[float] = mapped_column(Float, default=0)
    initial_position_z: Mapped[float] = mapped_column(Float, default=0)
    
    # Results
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Extra session data (JSON)
    # Note: "metadata" is reserved in SQLAlchemy, so we use "extra_data" instead
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    actions: Mapped[List["AgentAction"]] = relationship(
        "AgentAction",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    def get_duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.completion_time:
            return (self.completion_time - self.created_at).total_seconds()
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def __repr__(self) -> str:
        return f"<EnvironmentSession task={self.task_description[:30]} status={self.status}>"


class AgentAction(BaseModel):
    """
    A single action taken by the agent during a session.
    
    This is the detailed execution log.
    Used for analysis, debugging, and understanding agent behavior.
    
    Fields:
    - session_id: Which session this action belongs to
    - action_type: "move", "pickup", "rotate", etc.
    - action_args: Arguments sent to the action (JSON)
    - success: Did the action succeed?
    - result_message: What happened as a result
    - agent_position_before: Where agent was before action
    - agent_position_after: Where agent was after action
    
    Example:
    ```python
    action = AgentAction(
        session_id=1,
        action_type="move",
        action_args={"direction": "forward"},
        success=True,
        result_message="Moved forward successfully",
        agent_position_before=[3, 0, 5],
        agent_position_after=[4, 0, 5]
    )
    ```
    """
    __tablename__ = "agent_actions"
    
    # Relationship to session
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("environment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session: Mapped["EnvironmentSession"] = relationship(
        "EnvironmentSession",
        back_populates="actions"
    )
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action_args: Mapped[dict] = mapped_column(JSON, default={})
    
    # Execution result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result_message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Position tracking
    agent_position_before_x: Mapped[float] = mapped_column(Float)
    agent_position_before_y: Mapped[float] = mapped_column(Float)
    agent_position_before_z: Mapped[float] = mapped_column(Float)
    
    agent_position_after_x: Mapped[Optional[float]] = mapped_column(Float)
    agent_position_after_y: Mapped[Optional[float]] = mapped_column(Float)
    agent_position_after_z: Mapped[Optional[float]] = mapped_column(Float)
    
    # Step number in this session
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Observation after action (JSON)
    observation: Mapped[Optional[dict]] = mapped_column(JSON)
    
    def get_position_before(self) -> List[float]:
        """Get position before action."""
        return [self.agent_position_before_x, self.agent_position_before_y, self.agent_position_before_z]
    
    def get_position_after(self) -> List[float]:
        """Get position after action."""
        if self.agent_position_after_x is not None:
            return [self.agent_position_after_x, self.agent_position_after_y, self.agent_position_after_z]
        return None
    
    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"<AgentAction {status} {self.action_type} (step {self.step_number})>"
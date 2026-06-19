# backend/services/agent.py
"""
Agent Service - The Main Harness.

This is the core of the agent harness—the interface between
an intelligent LLM and the virtual environment.

Flow:
1. Get observation from environment
2. Format observation as prompt for LLM
3. Send to Claude with available tools
4. Parse Claude's tool use response
5. Execute the requested action
6. Repeat

Why separate from LLM service?
- LLM service: Low-level Claude API calls
- Agent service: High-level agent orchestration

This separation makes the code testable and extensible.
"""

from typing import Dict, Optional, List, Any
import asyncio
import json
from datetime import datetime

from services.llm import LLMService
from services.environment import VirtualEnvironment, WorldObject
from schemas.observation import Observation
from schemas.action import ActionResult, AGENT_TOOLS
from models.environment import EnvironmentSession, AgentAction
from database import async_session


class AgentService:
    """
    The Agent Harness.
    
    Orchestrates the interaction between:
    - Environment (world state)
    - LLM (Claude)
    - Logging/persistence (database)
    
    Usage:
    ```python
    agent_service = AgentService(environment=env, llm_service=llm)
    
    # Run one task
    session = await agent_service.run_task(
        task_description="Navigate to the red cube",
        max_steps=100
    )
    
    # Get results
    print(f"Success: {session.success}")
    print(f"Steps taken: {session.steps_taken}")
    ```
    """
    
    def __init__(
        self,
        environment: VirtualEnvironment,
        llm_service: "LLMService",
        agent_name: str = "claude-opus-4-6"
    ):
        """
        Initialize the agent service.
        
        Args:
            environment: The virtual environment
            llm_service: Service for calling Claude
            agent_name: Name of the LLM model
        """
        self.environment = environment
        self.llm_service = llm_service
        self.agent_name = agent_name
        
        # Current session (if running)
        self.current_session: Optional[EnvironmentSession] = None
        self.current_session_id: Optional[int] = None
    
    # ===== MAIN TASK EXECUTION =====
    
    async def run_task(
        self,
        task_description: str,
        max_steps: int = 100,
        initial_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Run an agent on a task until completion or max steps.
        
        Args:
            task_description: What the agent should do
            max_steps: Maximum actions allowed
            initial_position: Starting position [x, y, z] (optional)
        
        Returns:
            Dictionary with task results:
            {
                "success": bool,
                "steps_taken": int,
                "final_position": [x, y, z],
                "inventory": [...],
                "session_id": int,
                "error": str (if failed)
            }
        
        Example:
        ```python
        result = await agent_service.run_task(
            task_description="Navigate to the red cube and examine it",
            max_steps=50
        )
        
        if result["success"]:
            print(f"Completed in {result['steps_taken']} steps")
        else:
            print(f"Failed: {result.get('error')}")
        ```
        """
        # Initialize task
        self.environment.reset(*initial_position if initial_position else [])
        self.environment.max_steps = max_steps
        
        # Create database session for logging
        async with async_session() as db_session:
            try:
                # Create environment session record
                env_session = EnvironmentSession(
                    task_description=task_description,
                    agent_name=self.agent_name,
                    status="running",
                    max_steps=max_steps,
                    initial_position_x=self.environment.agent.position[0],
                    initial_position_y=self.environment.agent.position[1],
                    initial_position_z=self.environment.agent.position[2],
                )
                db_session.add(env_session)
                await db_session.flush()  # Get the ID
                self.current_session_id = env_session.id
                
                # Run the agent loop
                while self.environment.step_count < max_steps:
                    # Get observation
                    observation = self.environment.get_observation(task_description)
                    
                    # Ask Claude what to do
                    action_type, action_args = await self._think_and_act(
                        observation=observation,
                        task_description=task_description
                    )
                    
                    if action_type is None:
                        # LLM failed or returned invalid action
                        env_session.status = "failed"
                        env_session.success = False
                        break
                    
                    # Execute action in environment
                    action_result = self.environment.execute_action(action_type, action_args)
                    
                    # Log action to database
                    await self._log_action(
                        db_session=db_session,
                        session_id=env_session.id,
                        action_type=action_type,
                        action_args=action_args,
                        action_result=action_result,
                        step_number=self.environment.step_count
                    )
                    
                    # Check if task is complete
                    if self._is_task_complete(action_type, action_result, task_description):
                        env_session.status = "success"
                        env_session.success = True
                        break
                
                # Task ended (either success, failure, or max steps)
                if env_session.status == "running":
                    # Didn't explicitly succeed
                    if self.environment.step_count >= max_steps:
                        env_session.status = "timeout"
                    else:
                        env_session.status = "failed"
                    env_session.success = False
                
                # Update final state
                env_session.steps_taken = self.environment.step_count
                env_session.completion_time = datetime.utcnow()
                db_session.add(env_session)
                await db_session.commit()
                
                # Return results
                return {
                    "success": env_session.success,
                    "status": env_session.status,
                    "steps_taken": env_session.steps_taken,
                    "final_position": self.environment.agent.position,
                    "inventory": self.environment.agent.inventory,
                    "session_id": env_session.id,
                    "duration_seconds": env_session.get_duration_seconds()
                }
            
            except Exception as e:
                # Error during task execution
                return {
                    "success": False,
                    "steps_taken": self.environment.step_count,
                    "final_position": self.environment.agent.position,
                    "error": str(e),
                    "session_id": self.current_session_id
                }
    
    # ===== THINKING & ACTION SELECTION =====
    
    async def _think_and_act(
        self,
        observation: Observation,
        task_description: str
    ) -> tuple[Optional[str], Optional[Dict]]:
        """
        Ask Claude what action to take.
        
        Args:
            observation: Current world observation
            task_description: What the agent is trying to do
        
        Returns:
            Tuple of (action_type, action_args) or (None, None) if error
        
        This is where the LLM reasoning happens.
        """
        # Build prompt for Claude
        prompt = self._build_prompt(observation, task_description)
        
        try:
            # Call Claude with tool use
            action_type, action_args = await self.llm_service.reason_and_act(
                prompt=prompt,
                tools=AGENT_TOOLS,
                observation=observation
            )
            
            return action_type, action_args
        
        except Exception as e:
            print(f"Error getting action from LLM: {e}")
            return None, None
    
    def _build_prompt(
        self,
        observation: Observation,
        task_description: str
    ) -> str:
        """
        Build the prompt sent to Claude.
        
        This is critical—how you frame the prompt affects the agent's behavior.
        """
        prompt = f"""You are an intelligent agent in a 3D virtual world.

TASK: {task_description}

CURRENT OBSERVATION:
Your Position: {observation.agent_state.position.to_list()}
Facing: {observation.agent_state.direction.value}
Health: {observation.agent_state.health}

VISIBLE OBJECTS:
"""
        
        if observation.visible_objects:
            for obj in observation.visible_objects:
                prompt += f"\n- {obj.type} ({obj.color or 'default'}) at {obj.position.to_list()} ({obj.distance:.1f}m away)"
                if obj.state:
                    prompt += f" [state: {obj.state}]"
        else:
            prompt += "\n(No objects visible)"
        
        prompt += f"\n\nINVENTORY: {', '.join(observation.inventory) if observation.inventory else '(empty)'}"
        prompt += f"\nSteps remaining: {observation.environment_context.step_limit - observation.environment_context.time_elapsed}"
        
        prompt += """

INSTRUCTIONS:
1. Use the available tools to interact with the world
2. Think about your strategy before acting
3. Be efficient—you have limited steps
4. Use the "think" tool to explain your reasoning
5. Use "observe" if you need to refresh your perception

What do you do next?"""
        
        return prompt
    
    def _is_task_complete(
        self,
        action_type: str,
        action_result: ActionResult,
        task_description: str
    ) -> bool:
        """
        Check if the task is completed.
        
        For now: Task is complete if explicitly stated in action result.
        
        In Phase 4, we'll add:
        - Goal checking (agent reached target)
        - Item collection (agent has all required items)
        - Location checking (agent at specific coordinate)
        """
        # Simple heuristic: if action is "observe" and successful,
        # agent might be checking a completed goal
        # (More sophisticated checking comes later)
        
        return False  # For now, never auto-complete
    
    # ===== LOGGING =====
    
    async def _log_action(
        self,
        db_session,
        session_id: int,
        action_type: str,
        action_args: Dict,
        action_result: ActionResult,
        step_number: int
    ):
        """
        Log an action to the database.
        
        Used for analysis, debugging, and learning from agent behavior.
        """
        agent_action = AgentAction(
            session_id=session_id,
            action_type=action_type,
            action_args=action_args,
            success=action_result.success,
            result_message=action_result.message,
            agent_position_before_x=self.environment.agent.position[0],
            agent_position_before_y=self.environment.agent.position[1],
            agent_position_before_z=self.environment.agent.position[2],
            agent_position_after_x=action_result.new_position[0] if action_result.new_position else None,
            agent_position_after_y=action_result.new_position[1] if action_result.new_position else None,
            agent_position_after_z=action_result.new_position[2] if action_result.new_position else None,
            step_number=step_number,
            observation=self.environment.get_observation("").dict()
        )
        db_session.add(agent_action)
        await db_session.flush()
    
    # ===== UTILITIES =====
    
    async def setup_world(self, world_objects: List[WorldObject]):
        """
        Setup the world with objects.
        
        Args:
            world_objects: List of WorldObject to add to the world
        
        Example:
        ```python
        red_cube = WorldObject(
            id=1, name="Red Cube", object_type="cube",
            position=[5, 0, 5], color="red", pickupable=True
        )
        blue_door = WorldObject(
            id=2, name="Blue Door", object_type="door",
            position=[10, 0, 10], color="blue",
            state="locked", interactable=True
        )
        
        await agent_service.setup_world([red_cube, blue_door])
        ```
        """
        for obj in world_objects:
            self.environment.add_object(obj)
    
    def get_environment_status(self) -> Dict:
        """Get current environment status."""
        return self.environment.get_status()
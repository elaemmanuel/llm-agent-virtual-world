# backend/main.py
"""
FastAPI Main Application.

This is the entry point for the entire backend. It:
1. Creates the FastAPI app
2. Registers routes (REST endpoints)
3. Registers WebSocket handlers
4. Sets up middleware (CORS, logging)
5. Initializes startup/shutdown logic

How to run:
    uvicorn main:app --reload

This starts the server on http://localhost:8000
API docs available at http://localhost:8000/docs
"""

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import json

from config import settings
from database import init_db, close_db, async_session
from services.environment import VirtualEnvironment
from services.agent import AgentService
from services.llm import LLMService
from utils.logger import get_logger


# ===== LOGGING =====
logger = get_logger(__name__)


# ===== GLOBAL STATE =====
# These will be initialized on startup
app_state = {
    "environment": None,
    "agent_service": None,
    "llm_service": None,
    "active_sessions": {}  # Track WebSocket connections
}


# ===== STARTUP & SHUTDOWN =====

async def startup_event():
    """
    Called when server starts.
    
    Initializes:
    - Database tables
    - Virtual environment
    - Services (Agent, LLM)
    """
    logger.info("🚀 Starting up server...")
    
    try:
        # Initialize database
        logger.info("📦 Initializing database...")
        await init_db()
        logger.info("✓ Database initialized")
        
        # Create environment
        logger.info("🌍 Creating virtual environment...")
        app_state["environment"] = VirtualEnvironment(
            world_size_x=settings.WORLD_SIZE_X,
            world_size_y=settings.WORLD_SIZE_Y,
            world_size_z=settings.WORLD_SIZE_Z,
        )
        logger.info(f"✓ Environment created ({settings.WORLD_SIZE_X}x{settings.WORLD_SIZE_Y}x{settings.WORLD_SIZE_Z})")
        
        # Create LLM service
        logger.info("🤖 Initializing LLM service...")
        app_state["llm_service"] = LLMService(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
            temperature=settings.AGENT_TEMPERATURE
        )
        logger.info(f"✓ LLM service initialized (model: {settings.ANTHROPIC_MODEL})")
        
        # Create agent service
        logger.info("🎯 Initializing agent service...")
        app_state["agent_service"] = AgentService(
            environment=app_state["environment"],
            llm_service=app_state["llm_service"],
            agent_name=settings.ANTHROPIC_MODEL
        )
        logger.info("✓ Agent service initialized")
        
        logger.info("✅ Server startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise


async def shutdown_event():
    """
    Called when server shuts down.
    
    Cleans up:
    - Database connections
    - Any open WebSocket connections
    """
    logger.info("💤 Shutting down server...")
    
    try:
        # Close database
        await close_db()
        logger.info("✓ Database connections closed")
        
        # Close WebSocket connections
        for session_id, ws in app_state["active_sessions"].items():
            try:
                await ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {session_id}: {e}")
        
        logger.info("✓ WebSocket connections closed")
        logger.info("✅ Server shutdown complete!")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}", exc_info=True)


# ===== LIFESPAN MANAGEMENT =====
# This is the modern FastAPI way to handle startup/shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for app lifespan.
    
    Everything before 'yield' runs on startup.
    Everything after runs on shutdown.
    """
    # Startup
    await startup_event()
    
    yield  # App is running
    
    # Shutdown
    await shutdown_event()


# ===== CREATE FASTAPI APP =====

app = FastAPI(
    title=settings.APP_NAME,
    description="LLM Agent in Virtual World - Phase 2 API",
    version=settings.APP_VERSION,
    lifespan=lifespan  # Use lifespan context manager
)


# ===== MIDDLEWARE =====

# CORS (Cross-Origin Resource Sharing)
# Allows requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

logger.info(f"✓ CORS configured for origins: {settings.CORS_ORIGINS}")


# ===== HEALTH CHECK =====

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns 200 if server is running.
    Used by load balancers and monitoring tools.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# ===== ENVIRONMENT ROUTES =====

@app.post("/world/setup")
async def setup_world(objects: list[dict]):
    """
    Set up the world with initial objects.
    
    Args:
        objects: List of objects to add
        
    Example:
        POST /world/setup
        [
            {
                "id": 1,
                "name": "Red Cube",
                "object_type": "cube",
                "position": [5, 0, 5],
                "color": "red",
                "pickupable": true
            }
        ]
    """
    try:
        from services.environment import WorldObject
        
        for obj_data in objects:
            obj = WorldObject(**obj_data)
            app_state["environment"].add_object(obj)
        
        logger.info(f"✓ World setup with {len(objects)} objects")
        
        return {
            "status": "success",
            "objects_added": len(objects),
            "world_status": app_state["environment"].get_status()
        }
    
    except Exception as e:
        logger.error(f"Error setting up world: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.get("/world/status")
async def get_world_status():
    """
    Get current world status.
    
    Returns:
        Agent position, world size, objects, step count, etc.
    """
    return {
        "status": "success",
        "world": app_state["environment"].get_status()
    }


@app.get("/world/observation")
async def get_observation(task: str = ""):
    """
    Get current observation.
    
    Args:
        task: Current task description
    
    Returns:
        What the agent perceives
    """
    observation = app_state["environment"].get_observation(task)
    return {
        "status": "success",
        "observation": observation.dict()
    }


# ===== TASK ROUTES =====

@app.post("/tasks/start")
async def start_task(task_description: str, max_steps: int = 100):
    """
    Start a new agent task.
    
    Args:
        task_description: What the agent should do
        max_steps: Maximum actions allowed
    
    Returns:
        Task ID and initial status
        
    Example:
        POST /tasks/start
        {
            "task_description": "Navigate to the red cube",
            "max_steps": 50
        }
    """
    try:
        logger.info(f"Starting task: {task_description}")
        
        # Run the task
        result = await app_state["agent_service"].run_task(
            task_description=task_description,
            max_steps=max_steps
        )
        
        logger.info(f"Task completed: {result}")
        
        return {
            "status": "success",
            "task_result": result
        }
    
    except Exception as e:
        logger.error(f"Error running task: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: int):
    """
    Get status and results of a completed task.
    
    Args:
        task_id: Session ID from database
    
    Returns:
        Task details, success status, steps taken
    """
    try:
        async with async_session() as session:
            from models.environment import EnvironmentSession
            from sqlalchemy import select
            
            stmt = select(EnvironmentSession).where(EnvironmentSession.id == task_id)
            result = await session.execute(stmt)
            env_session = result.scalar_one_or_none()
            
            if not env_session:
                return {"status": "error", "message": "Task not found"}, 404
            
            return {
                "status": "success",
                "task": {
                    "id": env_session.id,
                    "task_description": env_session.task_description,
                    "agent_name": env_session.agent_name,
                    "status": env_session.status,
                    "success": env_session.success,
                    "steps_taken": env_session.steps_taken,
                    "max_steps": env_session.max_steps,
                    "created_at": env_session.created_at.isoformat(),
                    "completion_time": env_session.completion_time.isoformat() if env_session.completion_time else None
                }
            }
    
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.get("/tasks/{task_id}/actions")
async def get_task_actions(task_id: int):
    """
    Get all actions (steps) in a task.
    
    Args:
        task_id: Session ID
    
    Returns:
        List of all actions with details
    """
    try:
        async with async_session() as session:
            from models.environment import AgentAction
            from sqlalchemy import select
            
            stmt = select(AgentAction).where(AgentAction.session_id == task_id)
            result = await session.execute(stmt)
            actions = result.scalars().all()
            
            return {
                "status": "success",
                "task_id": task_id,
                "action_count": len(actions),
                "actions": [
                    {
                        "step_number": a.step_number,
                        "action_type": a.action_type,
                        "action_args": a.action_args,
                        "success": a.success,
                        "result_message": a.result_message,
                        "position_before": a.get_position_before(),
                        "position_after": a.get_position_after(),
                        "created_at": a.created_at.isoformat()
                    }
                    for a in actions
                ]
            }
    
    except Exception as e:
        logger.error(f"Error getting task actions: {e}")
        return {"status": "error", "message": str(e)}, 500


# ===== WEBSOCKET HANDLER =====

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int):
    """
    WebSocket endpoint for real-time task updates.
    
    Client connects and receives updates as agent executes:
    - observation_update: New observation
    - action_executed: Action was executed
    - task_complete: Task finished
    - error: Something went wrong
    
    Usage (from React):
        const ws = new WebSocket(`ws://localhost:8000/ws/${task_id}`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Update:', data);
        };
    """
    await websocket.accept()
    app_state["active_sessions"][task_id] = websocket
    
    try:
        logger.info(f"WebSocket connected: task_id={task_id}")
        
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected to task {task_id}"
        })
        
        # Keep connection alive
        # In a real app, you'd stream task updates here
        while True:
            data = await websocket.receive_text()
            # Echo back (for testing)
            await websocket.send_json({
                "type": "echo",
                "data": data
            })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        app_state["active_sessions"].pop(task_id, None)
        logger.info(f"WebSocket disconnected: task_id={task_id}")


# ===== ERROR HANDLERS =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.
    
    Catches any unhandled exceptions and returns formatted error.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "status": "error",
        "message": "Internal server error",
        "detail": str(exc) if settings.DEBUG else None
    }, 500


# ===== STARTUP MESSAGE =====

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"""
    
    ╔════════════════════════════════════════════════════════╗
    ║  🚀 LLM Agent in Virtual World - Phase 2 Server       
    ║                                                        
    ║  Starting server...                                   
    ║  Environment: {'development' if settings.DEBUG else 'production'}                           
    ║  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'unknown'}             
    ║  LLM Model: {settings.ANTHROPIC_MODEL}              
    ║                                                        
    ║  📚 API Docs: http://localhost:8000/docs            
    ║  💚 Health Check: http://localhost:8000/health      
    ║                                                        
    ╚════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
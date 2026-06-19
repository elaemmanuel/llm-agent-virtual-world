# backend/config.py
"""
Configuration management for the LLM Agent application.

This module centralizes all configuration settings, reading from:
1. Environment variables (.env file)
2. System environment
3. Defaults

This approach follows the 12-factor app methodology for portability
and security (API keys are never hardcoded).
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Application settings using Pydantic.
    
    Pydantic BaseSettings automatically:
    - Reads from .env file
    - Validates types
    - Provides defaults
    
    Access settings with: settings.DATABASE_URL, settings.ANTHROPIC_API_KEY, etc.
    """
    
    # ===== APP SETTINGS =====
    # Basic app configuration
    APP_NAME: str = "LLM Agent in Virtual World"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False  # Set to True in development
    
    # ===== SERVER SETTINGS =====
    # FastAPI server configuration
    HOST: str = "0.0.0.0"  # Listen on all interfaces
    PORT: int = 8000       # API port
    RELOAD: bool = False   # Auto-reload on code changes (development only)
    
    # ===== DATABASE SETTINGS =====
    # PostgreSQL connection string
    # Format: postgresql+asyncpg://username:password@localhost:5432/database_name
    # asyncpg is the async driver for PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/llm_agent_dev"
    
    # Database pool settings for connection management
    DB_ECHO: bool = False  # Log all SQL queries (True in development for debugging)
    DB_POOL_SIZE: int = 20  # Max concurrent connections
    DB_MAX_OVERFLOW: int = 0  # Additional connections beyond pool size
    
    # ===== LLM SETTINGS =====
    # Anthropic Claude API configuration
    ANTHROPIC_API_KEY: str = ""  # Set in .env file
    ANTHROPIC_MODEL: str = "claude-opus-4-6"  # Model to use
    
    # ===== AGENT SETTINGS =====
    # Agent behavior configuration
    AGENT_TIMEOUT: int = 30  # Seconds to wait for LLM response
    AGENT_MAX_STEPS: int = 100  # Max actions per task
    AGENT_TEMPERATURE: float = 0.7  # LLM creativity (0=deterministic, 1=random)
    
    # ===== ENVIRONMENT SETTINGS =====
    # Virtual world configuration
    WORLD_SIZE_X: int = 20  # World width
    WORLD_SIZE_Y: int = 20  # World height
    WORLD_SIZE_Z: int = 10  # World depth (for 3D)
    
    # ===== LOGGING SETTINGS =====
    # Structured logging configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # "json" for structured logs, "text" for human-readable
    
    # ===== CORS SETTINGS =====
    # Cross-Origin Resource Sharing for frontend
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # API docs
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # ===== WEBSOCKET SETTINGS =====
    # Real-time communication configuration
    WEBSOCKET_TIMEOUT: int = 60  # Seconds before closing idle connection
    MAX_CONCURRENT_CONNECTIONS: int = 100  # Max WebSocket clients
    
    class Config:
        """Pydantic config for loading .env file."""
        env_file = ".env"  # Load from .env file
        case_sensitive = True  # Environment variables are case-sensitive


# Create a global settings instance
# Access anywhere with: from config import settings
settings = Settings()
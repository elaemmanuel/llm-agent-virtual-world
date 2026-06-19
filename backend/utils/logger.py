# backend/utils/logger.py
"""
Structured Logging Setup.

Provides consistent, readable logging across the app.

Features:
- Color-coded output (dev mode)
- JSON output (production mode)
- Per-module loggers
- Consistent format
"""

import logging
import sys
from config import settings


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter with color support for terminal output.
    
    Helps visually distinguish log levels during development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        if settings.DEBUG:
            # Add colors in development
            levelname = record.levelname
            if levelname in self.COLORS:
                color = self.COLORS[levelname]
                reset = self.COLORS['RESET']
                record.levelname = f"{color}{levelname}{reset}"
        
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Configured logger instance
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set log level from config
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Format: [LEVEL] module_name: message
        if settings.DEBUG:
            # Development: colored, human-readable
            formatter = ColoredFormatter(
                '[%(levelname)s] %(name)s: %(message)s'
            )
        else:
            # Production: JSON format (for log aggregation)
            formatter = logging.Formatter(
                '{"level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


# Root logger
logger = get_logger("llm_agent_backend")

logger.info(f"Logging initialized (level: {settings.LOG_LEVEL}, format: {'JSON' if not settings.DEBUG else 'colored'})")
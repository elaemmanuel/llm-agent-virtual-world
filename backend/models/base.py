# backend/models/base.py
"""
Base model class for all SQLAlchemy ORM models.

Provides common functionality:
- Auto timestamps (created_at, updated_at)
- ID primary key
- Serialization to dict

All your models inherit from Base, then get these features for free.
"""

from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.orm import declared_attr
from datetime import datetime
import uuid

from database import Base


class BaseModel(Base):
    """
    Abstract base class for all database models.
    
    Provides:
    - id: Unique identifier
    - created_at: When record was created
    - updated_at: When record was last modified
    
    Usage:
    ```python
    class Agent(BaseModel):
        __tablename__ = "agents"
        
        name: Mapped[str] = mapped_column(String)
    ```
    """
    
    __abstract__ = True  # Don't create a table for this class
    
    @declared_attr
    def id(cls):
        """Unique integer ID (auto-incrementing primary key)."""
        return Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    @declared_attr
    def created_at(cls):
        """Timestamp when record was created."""
        return Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False,
            index=True
        )
    
    @declared_attr
    def updated_at(cls):
        """Timestamp when record was last modified."""
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary.
        
        Useful for JSON serialization.
        Override in subclasses for custom serialization.
        """
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.__class__.__name__} id={self.id}>"
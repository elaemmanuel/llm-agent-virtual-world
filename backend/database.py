# backend/database.py
"""
Database setup and session management.

This module handles:
1. SQLAlchemy async engine creation
2. Session factory for database operations
3. Context managers for safe session handling
4. Dependency injection for FastAPI

Why async? FastAPI is async-first. Using async database drivers
(asyncpg for PostgreSQL) prevents blocking the event loop.

Why SQLAlchemy ORM? You get:
- Type safety
- Migration management (with Alembic)
- Relationship handling
- Query building
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,        # Async engine factory
    AsyncSession,               # Async session class
    async_sessionmaker,         # Async session factory
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config import settings

# ===== ASYNC ENGINE SETUP =====
"""
AsyncEngine:
- Uses asyncpg driver (async-native PostgreSQL driver)
- Connection pooling for efficiency
- Echo=DB_ECHO to log SQL (useful for debugging)

Development vs Production:
- DEBUG=True: Use NullPool (new connection per request, simpler)
- DEBUG=False: Use default pool with size and overflow settings (better performance)
"""

# Build engine kwargs dynamically based on DEBUG setting
engine_kwargs = {
    "echo": settings.DB_ECHO,  # Set True to see SQL queries
}

if settings.DEBUG:
    # Development: Use NullPool (no connection pooling)
    # Each operation gets a new connection, which is simpler but slower
    engine_kwargs["poolclass"] = NullPool
else:
    # Production: Use default pool with connection management
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE  # Max connections to keep in pool
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW  # Extra connections beyond pool

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# ===== SESSION FACTORY =====
"""
AsyncSessionMaker:
- Creates new AsyncSession instances
- Automatically manages transaction lifecycle
- expire_on_commit=False keeps objects loaded after commit (optional)
"""
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Objects remain accessible after commit
)

# ===== BASE CLASS FOR MODELS =====
"""
DeclarativeBases:
- Used to define SQLAlchemy ORM models
- All your model classes inherit from Base
- Contains metadata for migrations
"""
Base = declarative_base()


# ===== DEPENDENCY INJECTION FOR FASTAPI =====
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to inject database session into route handlers.
    
    Usage in route:
    ```python
    @app.get("/items")
    async def get_items(session: AsyncSession = Depends(get_db_session)):
        result = await session.execute(select(Item))
        return result.scalars().all()
    ```
    
    FastAPI automatically:
    1. Calls get_db_session()
    2. Injects the session
    3. Closes it after the route completes
    """
    async with async_session() as session:
        try:
            yield session  # Provide session to route handler
        finally:
            await session.close()  # Cleanup


# ===== DATABASE INITIALIZATION =====
async def init_db():
    """
    Initialize database tables.
    
    Runs on app startup. Creates all tables defined by models
    that inherit from Base.
    
    Usage:
    ```python
    @app.on_event("startup")
    async def startup():
        await init_db()
    ```
    
    Note: In production, use Alembic migrations instead.
    We'll set that up later.
    """
    async with engine.begin() as conn:
        # Create all tables (won't recreate if they exist)
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """
    Drop all database tables.
    
    Warning: This destroys all data! Only use in development/testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db():
    """
    Close the database connection pool.
    
    Usage on app shutdown:
    ```python
    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
    ```
    """
    await engine.dispose()
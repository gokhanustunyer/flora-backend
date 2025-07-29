"""Database connection configuration for Supabase."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from config.settings import settings
from utils.logging_config import get_logger

# Add UUID support for SQLite
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.dialects.postgresql import UUID

def visit_UUID(self, type_, **kw):
    return "TEXT"

# Monkey patch UUID support for SQLite
SQLiteTypeCompiler.visit_UUID = visit_UUID

logger = get_logger(__name__)

# Create declarative base for models
Base = declarative_base()

# Global variables for engine and session
engine = None
AsyncSessionLocal = None

def get_database_url() -> str:
    """Get the appropriate database URL based on configuration."""
    if settings.database_url and "[YOUR_DB_PASSWORD]" not in str(settings.database_url):
        # Direct database URL provided and it's valid
        # Convert asyncpg to psycopg for better Supabase compatibility
        db_url = str(settings.database_url)
        if "postgresql+asyncpg://" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
            logger.info("Converting asyncpg to psycopg for better Supabase compatibility")
        return db_url
    elif settings.supabase_enabled:
        # Build database URL from Supabase settings
        project_url = settings.supabase_url
        if not project_url:
            raise ValueError("Supabase URL is required when using Supabase database")
        
        # Extract project ID from Supabase URL
        # Format: https://your-project.supabase.co
        project_id = project_url.replace("https://", "").replace("http://", "").split(".")[0]
        
        # Supabase direct database connection format - use psycopg for better pgbouncer compatibility
        db_url = f"postgresql+psycopg://postgres:[YOUR_DB_PASSWORD]@db.{project_id}.supabase.co:6543/postgres"
        
        logger.warning(
            "Using Supabase database URL template. "
            "Please replace [YOUR_DB_PASSWORD] with your actual Supabase database password in DATABASE_URL."
        )
        return db_url
    else:
        # Fallback to SQLite for local development when no database config
        logger.info("No database configuration found. Using SQLite for local development.")
        return "sqlite+aiosqlite:///./gnb_generations.db"

# Create async engine only if database is enabled
if settings.database_enabled:
    try:
        database_url = get_database_url()
        
        # Check if we have a real database URL
        if database_url.startswith("sqlite"):
            # Use SQLite for local development
            logger.info("Using SQLite for local development")
            engine = create_async_engine(
                database_url,
                echo=settings.database_echo,
                future=True,
            )
            
            # Create session factory
            AsyncSessionLocal = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("SQLite database engine initialized successfully for local development")
        else:
            # Use the provided database URL (PostgreSQL/Supabase)
            # Configure engine parameters based on database type
            engine_params = {
                "echo": settings.database_echo,
                "future": True,
            }
            
            # For Supabase/PostgreSQL, configure for pgbouncer compatibility
            if "postgresql" in database_url:
                engine_params["poolclass"] = NullPool
                
                if "psycopg" in database_url:
                    # psycopg-specific settings for Supabase
                    engine_params["connect_args"] = {
                        "prepare_threshold": None,  # Disable prepared statements
                        "options": "-c jit=off"  # Server settings for psycopg
                    }
                else:
                    # asyncpg settings (fallback)
                    engine_params["connect_args"] = {
                        "statement_cache_size": 0,
                        "prepared_statement_cache_size": 0,
                        "command_timeout": 60,
                        "server_settings": {
                            "jit": "off",
                            "statement_timeout": "30s"
                        }
                    }
                    
                # Also disable SQLAlchemy's own statement caching
                engine_params["pool_pre_ping"] = True
                engine_params["pool_recycle"] = 300
            else:
                # For regular PostgreSQL, use connection pooling
                engine_params.update({
                    "pool_size": settings.database_pool_size,
                    "max_overflow": settings.database_max_overflow,
                })
            
            engine = create_async_engine(database_url, **engine_params)
            
            # Create session factory
            AsyncSessionLocal = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database engine initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        engine = None
        AsyncSessionLocal = None
else:
    logger.info("Database features disabled")
    engine = None
    AsyncSessionLocal = None

async def init_database():
    """Initialize database tables."""
    if not engine:
        logger.warning("Database engine not available, skipping table initialization")
        return
        
    try:
        async with engine.begin() as conn:
            # Import models to ensure they're registered
            from models.image_generation import ImageGeneration
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise

async def get_db_session() -> AsyncSession:
    """Get database session."""
    if not AsyncSessionLocal:
        raise RuntimeError("Database not configured or session factory not available")
    
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        
        # Handle specific pgbouncer/prepared statement errors
        error_str = str(e).lower()
        if "prepared statement" in error_str and "already exists" in error_str:
            logger.warning("pgbouncer prepared statement conflict detected, retrying session")
        elif "pendingrollbackerror" in error_str:
            logger.warning("Session rollback detected, session will be recreated")
        
        raise
    finally:
        await session.close()

# Dependency for FastAPI
async def get_db():
    """FastAPI dependency for database sessions."""
    if not settings.database_enabled or not AsyncSessionLocal:
        yield None
        return
        
    session = None
    try:
        session = AsyncSessionLocal()
        yield session
    except Exception as e:
        if session:
            await session.rollback()
        
        error_str = str(e).lower()
        if "prepared statement" in error_str and "already exists" in error_str:
            logger.warning("pgbouncer prepared statement conflict detected")
        
        logger.error(f"Database session error: {e}")
        # Return None to gracefully degrade to non-database mode
        yield None
    finally:
        if session:
            await session.close()

async def close_database():
    """Close database connections."""
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")

# Health check function
async def check_database_health() -> dict:
    """Check database connectivity and return status."""
    if not settings.database_enabled:
        return {
            "status": "disabled",
            "message": "Database features are disabled"
        }
    
    if not engine:
        return {
            "status": "error",
            "message": "Database engine not initialized"
        }
    
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "message": "Database connection successful",
            "type": "supabase" if settings.supabase_enabled else "postgresql"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        } 
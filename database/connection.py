"""Database connection configuration for Supabase only."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from config.settings import settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Create declarative base for models
Base = declarative_base()

# Global variables for engine and session
engine = None
AsyncSessionLocal = None

def get_database_url() -> str:
    """Get the Supabase database URL."""
    if settings.database_url and "[YOUR_DB_PASSWORD]" not in str(settings.database_url):
        # Direct database URL provided and it's valid
        db_url = str(settings.database_url)
        if "postgresql+asyncpg://" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
            logger.info("Converting asyncpg to psycopg for better Supabase compatibility")
        return db_url
    elif settings.supabase_enabled:
        # Build database URL from Supabase settings
        project_url = settings.supabase_url
        if not project_url:
            raise ValueError("Supabase URL is required")
        
        # Extract project ID from Supabase URL
        project_id = project_url.replace("https://", "").replace("http://", "").split(".")[0]
        
        # Supabase direct database connection format
        db_url = f"postgresql+psycopg://postgres:[YOUR_DB_PASSWORD]@db.{project_id}.supabase.co:6543/postgres"
        
        logger.warning(
            "Using Supabase database URL template. "
            "Please set DATABASE_URL with your actual Supabase database password."
        )
        return db_url
    else:
        raise ValueError("Database configuration required. Please set SUPABASE_URL and SUPABASE_ANON_KEY or DATABASE_URL.")

# Create async engine only if database is enabled
if settings.database_enabled:
    try:
        database_url = get_database_url()
        
        # Configure engine for Supabase/PostgreSQL with pgbouncer compatibility
        engine_params = {
            "echo": settings.database_echo,
            "future": True,
            "poolclass": NullPool,  # Required for Supabase pgbouncer
        }
        
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
        
        # Additional pgbouncer compatibility settings
        engine_params["pool_pre_ping"] = True
        engine_params["pool_recycle"] = 300
        
        engine = create_async_engine(database_url, **engine_params)
        
        # Create session factory
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Supabase database engine initialized successfully")
        
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
            "type": "supabase"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}"
        }
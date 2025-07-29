"""Main FastAPI application for the GNB Dog Image Generation Backend."""

import asyncio
import sys

# Windows psycopg compatibility fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime, timezone

from config.settings import settings
from utils.logging_config import configure_logging, get_logger
from utils.exceptions import BaseCustomException

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting GNB Dog Image Generation Backend", version="1.0.0")
    
    # Log feature status
    feature_status = settings.get_feature_status()
    logger.info("Feature status", **feature_status)
    
    # Initialize database if enabled
    if settings.database_enabled:
        try:
            from database.connection import init_database
            await init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            if settings.debug_mode:
                raise
            else:
                logger.warning("Continuing without database features")
    else:
        logger.info("Database features disabled (DATABASE_URL not configured)")

    
    # Log configuration summary
    logger.info("Configuration summary", 
                port=settings.app_port,
                cors_origins=settings.cors_origins,
                max_image_size_mb=settings.max_image_size_mb)
    
    yield
    
    # Shutdown
    logger.info("Shutting down GNB Dog Image Generation Backend")
    
    # Close database connections if enabled
    if settings.database_enabled:
        try:
            from database.connection import close_database
            await close_database()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error("Failed to close database connections", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="GNB Dog Image Generation API",
    description="""
    A production-ready FastAPI backend that integrates with Azure AI services to transform 
    dog photos into AI-generated images of dogs wearing GNB-branded apparel.
    
    ## 🚀 Features
    
    * **Azure AI Integration**: Uses Azure OpenAI DALL-E for high-quality image generation
    * **Image Processing**: Validates, resizes, and processes uploaded dog photos
    * **Logo Overlay**: Automatically adds GNB branding to generated images
    * **Database Tracking**: Tracks generation requests, status, and performance metrics
    * **Generation History**: View past generations and their status
    * **Analytics**: Get aggregated statistics about image generation performance
    * **Production Ready**: Comprehensive error handling, logging, and monitoring
    * **Modular Architecture**: Clean, maintainable code structure
    * **CORS Support**: Configured for frontend integration
    * **Structured Logging**: JSON-formatted logs with request tracking
    
    ## 📖 Available Endpoints
    
    ### Core Generation
    * `POST /api/v1/generate` - Generate AI dog images with GNB apparel
    * `GET /api/v1/health` - Service health check
    
    ### Database Features (when DATABASE_URL is configured)
    * `GET /api/v1/generations` - List recent image generations with pagination
    * `GET /api/v1/generations/{id}` - Get specific generation details
    * `GET /api/v1/statistics` - Get aggregated statistics and performance metrics
    
    ## 🔧 Configuration
    
    * **DATABASE_URL**: Enable database features for request tracking and analytics
    * **Azure OpenAI**: Configure Azure credentials for DALL-E image generation
    * **File Upload**: Customize max file size and allowed image types
    """,
    version="1.0.0",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include core endpoints
from api.v1.endpoints import router as api_router
app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["Image Generation"]
)


@app.exception_handler(BaseCustomException)
async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """
    Global exception handler for custom exceptions.
    """
    logger.error(
        "Custom exception caught",
        exception_type=type(exc).__name__,
        message=exc.message,
        details=exc.details,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unexpected errors.
    """
    logger.error(
        "Unexpected exception caught",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug_mode else "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    feature_status = settings.get_feature_status()
    
    return {
        "message": "GNB Dog Image Generation API",
        "version": "1.0.0",
        "description": "Transform your dog photos with AI-generated GNB apparel",
        "features": feature_status,
        "endpoints": {
            "docs": "/docs" if settings.enable_api_docs else "disabled",
            "health": "/api/v1/health",
            "generate": "/api/v1/generate",
            "generations": "/api/v1/generations" if settings.database_enabled else "disabled",
            "generation_details": "/api/v1/generations/{id}" if settings.database_enabled else "disabled", 
            "statistics": "/api/v1/statistics" if settings.database_enabled else "disabled"
        }
    }


@app.get("/health", tags=["Health"])
async def root_health():
    """
    Simple health check endpoint.
    """
    feature_status = settings.get_feature_status()
    
    return {
        "status": "healthy", 
        "service": "GNB Dog Image Generation API", 
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": feature_status
    }


# Export the app for Vercel
# This is required for Vercel deployment
handler = app

if __name__ == "__main__":
    # Run the application locally
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.reload_on_change and settings.debug_mode,
        log_config=None  # Use our custom logging configuration
    ) 
"""
Flora Backend - AI-powered dog image generation service.

A simplified backend service that uses Stability.ai for image generation,
Supabase for database operations and storage, with comprehensive validation and logging.

Author: Assistant
Version: 2.0 (Simplified for Production)
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize FastAPI app
app = FastAPI(
    title="Flora Backend API",
    description="AI-powered dog image generation service with Stability.ai and Supabase",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check endpoint (must be available before imports)
@app.get("/")
@app.get("/health") 
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "flora-backend", "version": "2.0.0"}

# Import and include routers after app initialization
try:
    from api.v1.endpoints import router as api_router
    app.include_router(api_router, prefix="/api/v1", tags=["API v1"])
except Exception as e:
    print(f"❌ Failed to import API router: {e}")

# Vercel handler - export app directly
app = app  # Make sure app is available for Vercel

# For local development
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=3001,
        reload=True,
        log_level="info"
    ) 
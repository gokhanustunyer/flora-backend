"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Dict


class ImageGenerationResponse(BaseModel):
    """Response schema for image generation endpoint."""
    
    success: bool = Field(
        default=True,
        description="Success status"
    )
    
    data: dict = Field(
        default={},
        description="Data dictionary"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message"
    )
    


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health message")
    timestamp: str = Field(..., description="Response timestamp")
    services: Optional[Dict[str, str]] = Field(None, description="Detailed service statuses") 
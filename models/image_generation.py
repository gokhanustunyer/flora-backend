"""Image generation model for tracking generation requests (simplified)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON

from database.connection import Base


class ImageGeneration(Base):
    """Model for tracking image generation requests (no user authentication required)."""
    
    __tablename__ = "image_generations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Original image information
    original_image_filename = Column(String)
    original_image_url = Column(String)  # Azure Blob Storage URL
    original_image_size = Column(Integer)  # Size in bytes
    original_image_format = Column(String)  # JPEG, PNG, etc.
    
    # Generated image information
    generated_image_url = Column(String)  # Azure Blob Storage URL
    generated_image_size = Column(Integer)  # Size in bytes
    
    # Processing information
    prompt_used = Column(Text)  # The prompt sent to DALL-E
    dog_description = Column(Text)  # Description of the dog (if provided)
    processing_time = Column(Float)  # Time in seconds
    status = Column(String, default="pending")  # pending, processing, completed, failed
    
    # Azure AI information
    azure_response_data = Column(JSON)  # Store Azure API response metadata
    error_message = Column(Text)  # Error details if generation failed
    
    # Logo overlay information
    logo_applied = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime)  # When processing started
    completed_at = Column(DateTime)  # When processing completed
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "original_image_filename": self.original_image_filename,
            "original_image_url": self.original_image_url,
            "generated_image_url": self.generated_image_url,
            "prompt_used": self.prompt_used,
            "processing_time": self.processing_time,
            "status": self.status,
            "logo_applied": self.logo_applied,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def update_status(self, status: str, error_message: str = None):
        """Update generation status and timestamps."""
        self.status = status
        if error_message:
            self.error_message = error_message
        
        now = datetime.now(timezone.utc)
        
        if status == "processing":
            self.started_at = now
        elif status in ["completed", "failed"]:
            self.completed_at = now
            if self.started_at:
                # Ensure both datetimes are timezone-aware for calculation
                if self.started_at.tzinfo is None:
                    # Convert naive datetime to UTC if needed
                    started_utc = self.started_at.replace(tzinfo=timezone.utc)
                else:
                    started_utc = self.started_at
                
                self.processing_time = (self.completed_at - started_utc).total_seconds()


class GenerationStatistics(Base):
    """Model for storing generation statistics and analytics."""
    
    __tablename__ = "generation_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Daily statistics
    total_generations = Column(Integer, default=0)
    successful_generations = Column(Integer, default=0)
    failed_generations = Column(Integer, default=0)
    
    # Performance metrics
    average_processing_time = Column(Float, default=0.0)
    total_processing_time = Column(Float, default=0.0)
    
    # Resource usage
    total_images_processed = Column(Integer, default=0)
    total_storage_used = Column(Integer, default=0)  # in bytes
    
    # Error tracking
    azure_api_errors = Column(Integer, default=0)
    image_processing_errors = Column(Integer, default=0)
    logo_overlay_errors = Column(Integer, default=0)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "date": self.date.isoformat() if self.date else None,
            "total_generations": self.total_generations,
            "successful_generations": self.successful_generations,
            "failed_generations": self.failed_generations,
            "success_rate": (self.successful_generations / self.total_generations * 100) if self.total_generations > 0 else 0,
            "average_processing_time": self.average_processing_time,
            "total_storage_used": self.total_storage_used
        } 
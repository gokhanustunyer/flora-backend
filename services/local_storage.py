"""Simple local storage service for development."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)


class LocalStorageService:
    """Simple local file storage service."""
    
    def __init__(self, base_path: str = "./storage"):
        """Initialize local storage."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
        # Create main folders
        (self.base_path / "originals").mkdir(exist_ok=True)
        (self.base_path / "generations").mkdir(exist_ok=True)
        
        logger.info(f"🗂️ Local storage initialized at: {self.base_path.absolute()}")
    
    def save_image(self, image_bytes: bytes, filename: str, folder: str = "generations") -> str:
        """
        Save image bytes to local storage.
        
        Args:
            image_bytes: Image data as bytes
            filename: Original filename (for extension)
            folder: Storage folder ("originals" or "generations")
            
        Returns:
            Relative file path as string
        """
        try:
            # Create date-based folder structure
            now = datetime.now()
            date_folder = f"{now.year}/{now.month:02d}/{now.day:02d}"
            folder_path = self.base_path / folder / date_folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename with proper extension
            file_extension = "png"  # Default
            if "." in filename:
                file_extension = filename.split(".")[-1].lower()
            
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = folder_path / unique_filename
            
            # Save the file
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            
            # Return relative path from storage root
            relative_path = str(file_path.relative_to(self.base_path))
            
            logger.info(f"📁 Image saved: storage/{relative_path}")
            return f"storage/{relative_path}"
            
        except Exception as e:
            logger.error(f"❌ Failed to save image: {e}")
            raise Exception(f"Storage save failed: {str(e)}")
    
    def get_full_path(self, relative_path: str) -> Path:
        """Get full file path from relative path."""
        # Remove 'storage/' prefix if present
        if relative_path.startswith("storage/"):
            relative_path = relative_path[8:]
        
        return self.base_path / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        return self.get_full_path(relative_path).exists()
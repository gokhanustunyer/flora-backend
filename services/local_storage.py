"""Local file storage service for development/fallback."""

import os
import uuid
from datetime import datetime
from typing import Tuple
from pathlib import Path

from utils.logging_config import get_logger
from utils.exceptions import ImageProcessingError

logger = get_logger(__name__)


class LocalStorageService:
    """Local file storage service for development."""
    
    def __init__(self, base_path: str = "./storage"):
        """Initialize local storage service."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_path.absolute()}")
    
    async def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        folder: str = "generations",
        content_type: str = "image/png"
    ) -> Tuple[str, str]:
        """
        Save image to local storage.
        
        Args:
            image_bytes: Image data as bytes
            filename: Original filename
            folder: Storage folder (e.g., 'originals', 'generations')
            content_type: MIME type of the image
            
        Returns:
            Tuple of (file_path, public_url)
        """
        try:
            # Generate unique filename
            file_extension = filename.split('.')[-1] if '.' in filename else 'png'
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Create folder structure
            folder_path = self.base_path / folder / datetime.utcnow().strftime('%Y/%m/%d')
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # File path
            file_path = folder_path / unique_filename
            relative_path = str(file_path.relative_to(self.base_path))
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            # Generate "public URL" (local path)
            public_url = f"/storage/{relative_path}"
            
            logger.info(f"Image saved locally: {file_path}")
            
            return relative_path, public_url
            
        except Exception as e:
            logger.error(f"Error saving image locally: {e}")
            raise ImageProcessingError(f"Local storage failed: {str(e)}")
    
    def get_file_path(self, relative_path: str) -> Path:
        """Get absolute file path from relative path."""
        return self.base_path / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        return self.get_file_path(relative_path).exists()
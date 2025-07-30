"""Supabase Storage service for managing image uploads and downloads."""

import uuid
import io
from typing import Optional, Tuple
from datetime import datetime, timedelta
from supabase import create_client, Client
from PIL import Image

from config.settings import settings
from utils.exceptions import ImageProcessingError, AzureAPIError
from utils.logging_config import get_logger

logger = get_logger(__name__)

class SupabaseStorageService:
    """Service for managing image storage in Supabase Storage."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not settings.supabase_enabled:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key
        self.bucket_name = "images"  # User created "images" bucket
        
        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        logger.info(f"Supabase Storage service initialized for bucket: {self.bucket_name}")
    
    async def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        folder: str = "generations",
        content_type: str = "image/png"
    ) -> Tuple[str, str]:
        """
        Upload image to Supabase Storage.
        
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
            file_path = f"{folder}/{datetime.utcnow().strftime('%Y/%m/%d')}/{unique_filename}"
            
            logger.info(f"Uploading image to Supabase Storage: {file_path}")
            
            # Upload file to Supabase Storage
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=image_bytes,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600"
                }
            )
            
            # Modern supabase handles response differently
            logger.info(f"Upload response type: {type(response)}")
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            logger.info(f"Image uploaded successfully to: {public_url}")
            
            return file_path, public_url
            
        except Exception as e:
            logger.error(f"Error uploading image to Supabase Storage: {e}")
            raise ImageProcessingError(f"Storage upload failed: {str(e)}")
    
    async def download_image(self, file_path: str) -> bytes:
        """
        Download image from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Image data as bytes
        """
        try:
            logger.info(f"Downloading image from Supabase Storage: {file_path}")
            
            # Download file from Supabase Storage
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            
            if isinstance(response, dict) and response.get('error'):
                raise ImageProcessingError(
                    f"Failed to download image from Supabase Storage: {response['error']}"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error downloading image from Supabase Storage: {e}")
            raise ImageProcessingError(f"Storage download failed: {str(e)}")
    
    async def delete_image(self, file_path: str) -> bool:
        """
        Delete image from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if deletion was successful
        """
        try:
            logger.info(f"Deleting image from Supabase Storage: {file_path}")
            
            # Delete file from Supabase Storage
            response = self.client.storage.from_(self.bucket_name).remove([file_path])
            
            if response.get('error'):
                logger.warning(f"Failed to delete image: {response['error']}")
                return False
            
            logger.info(f"Image deleted successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image from Supabase Storage: {e}")
            return False
    
    async def generate_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a signed URL for private file access.
        
        Args:
            file_path: Path to the file in storage
            expires_in: URL expiry time in seconds (default: 1 hour)
            
        Returns:
            Signed URL for file access
        """
        try:
            logger.info(f"Generating signed URL for: {file_path}")
            
            # Create signed URL
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            
            if response.get('error'):
                raise ImageProcessingError(
                    f"Failed to generate signed URL: {response['error']}"
                )
            
            signed_url = response.get('signedURL')
            logger.info(f"Signed URL generated successfully")
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            raise ImageProcessingError(f"Signed URL generation failed: {str(e)}")
    
    async def list_files(
        self,
        folder: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        List files in storage bucket.
        
        Args:
            folder: Folder to list files from
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            List of file objects
        """
        try:
            logger.info(f"Listing files in folder: {folder}")
            
            # List files in bucket
            response = self.client.storage.from_(self.bucket_name).list(
                path=folder,
                limit=limit,
                offset=offset
            )
            
            if isinstance(response, dict) and response.get('error'):
                raise ImageProcessingError(
                    f"Failed to list files: {response['error']}"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise ImageProcessingError(f"File listing failed: {str(e)}")
    
    async def get_storage_statistics(self) -> dict:
        """
        Get storage usage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            # Get bucket info (this might not be available in all Supabase plans)
            # For now, return basic stats
            originals = await self.list_files("originals")
            generations = await self.list_files("generations")
            
            total_files = len(originals) + len(generations)
            
            # Calculate approximate storage size
            total_size = 0
            for file_list in [originals, generations]:
                for file_obj in file_list:
                    if isinstance(file_obj, dict) and 'metadata' in file_obj:
                        total_size += file_obj['metadata'].get('size', 0)
            
            return {
                "bucket_name": self.bucket_name,
                "total_files": total_files,
                "original_images": len(originals),
                "generated_images": len(generations),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "provider": "supabase"
            }
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {
                "bucket_name": self.bucket_name,
                "error": str(e),
                "provider": "supabase"
            }
    
    def _validate_image(self, image_bytes: bytes) -> bool:
        """
        Validate image format and content.
        
        Args:
            image_bytes: Image data to validate
            
        Returns:
            True if image is valid
        """
        try:
            # Try to open image with PIL
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()
            return True
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            return False

# Initialize storage service
storage_service = None
if settings.supabase_enabled:
    try:
        storage_service = SupabaseStorageService()
        logger.info("✅ Supabase Storage service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase Storage service: {e}")
        storage_service = None 
"""Azure Blob Storage service for image storage and retrieval."""

import uuid
import io
from datetime import datetime, timedelta
from typing import Optional, Tuple
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from config.settings import settings
from utils.exceptions import ImageProcessingError
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AzureStorageService:
    """Service for managing image storage in Azure Blob Storage."""
    
    def __init__(self):
        """Initialize Azure Blob Storage client."""
        try:
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{settings.azure_storage_account_name}.blob.core.windows.net",
                credential=settings.azure_storage_account_key
            )
            self.container_name = settings.azure_storage_container_name
            self._ensure_container_exists()
            logger.info("Azure Blob Storage client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Azure Blob Storage client", error=str(e))
            raise ImageProcessingError(f"Failed to initialize Azure Storage: {str(e)}")
    
    def _ensure_container_exists(self):
        """Ensure the blob container exists, create if it doesn't."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
            logger.info(f"Container '{self.container_name}' exists")
        except ResourceNotFoundError:
            try:
                container_client = self.blob_service_client.create_container(self.container_name)
                logger.info(f"Created container '{self.container_name}'")
            except ResourceExistsError:
                logger.info(f"Container '{self.container_name}' already exists")
            except Exception as e:
                logger.error("Failed to create container", error=str(e))
                raise ImageProcessingError(f"Failed to create storage container: {str(e)}")
    
    async def upload_image(
        self, 
        image_bytes: bytes, 
        filename: Optional[str] = None,
        content_type: str = "image/png",
        folder: str = "images"
    ) -> Tuple[str, str]:
        """
        Upload image to Azure Blob Storage.
        
        Args:
            image_bytes: Image data as bytes
            filename: Optional filename, will generate UUID if not provided
            content_type: MIME type of the image
            folder: Folder within container to store the image
            
        Returns:
            Tuple of (blob_name, blob_url)
            
        Raises:
            ImageProcessingError: If upload fails
        """
        try:
            # Generate filename if not provided
            if not filename:
                file_extension = self._get_extension_from_content_type(content_type)
                filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create blob name with folder structure
            blob_name = f"{folder}/{datetime.utcnow().strftime('%Y/%m/%d')}/{filename}"
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                data=image_bytes,
                content_type=content_type,
                overwrite=True
            )
            
            # Get the URL
            blob_url = blob_client.url
            
            logger.info(
                "Image uploaded to Azure Storage",
                blob_name=blob_name,
                size_bytes=len(image_bytes),
                content_type=content_type
            )
            
            return blob_name, blob_url
            
        except Exception as e:
            logger.error("Failed to upload image to Azure Storage", error=str(e))
            raise ImageProcessingError(f"Failed to upload image: {str(e)}")
    
    async def download_image(self, blob_name: str) -> bytes:
        """
        Download image from Azure Blob Storage.
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Image data as bytes
            
        Raises:
            ImageProcessingError: If download fails
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_data = blob_client.download_blob()
            image_bytes = blob_data.readall()
            
            logger.info(
                "Image downloaded from Azure Storage",
                blob_name=blob_name,
                size_bytes=len(image_bytes)
            )
            
            return image_bytes
            
        except ResourceNotFoundError:
            logger.error("Blob not found", blob_name=blob_name)
            raise ImageProcessingError(f"Image not found: {blob_name}")
        except Exception as e:
            logger.error("Failed to download image from Azure Storage", error=str(e))
            raise ImageProcessingError(f"Failed to download image: {str(e)}")
    
    def generate_sas_url(
        self, 
        blob_name: str, 
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        """
        Generate a SAS URL for secure access to a blob.
        
        Args:
            blob_name: Name of the blob
            expiry_hours: Hours until the SAS token expires
            permissions: Permissions for the SAS token (r=read, w=write, etc.)
            
        Returns:
            SAS URL for the blob
        """
        try:
            # Convert permissions string to BlobSasPermissions
            sas_permissions = BlobSasPermissions(read=True if 'r' in permissions else False)
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=settings.azure_storage_account_name,
                account_key=settings.azure_storage_account_key,
                container_name=self.container_name,
                blob_name=blob_name,
                permission=sas_permissions,
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Construct full URL
            blob_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            
            logger.info(
                "Generated SAS URL",
                blob_name=blob_name,
                expiry_hours=expiry_hours
            )
            
            return blob_url
            
        except Exception as e:
            logger.error("Failed to generate SAS URL", error=str(e))
            raise ImageProcessingError(f"Failed to generate secure URL: {str(e)}")
    
    async def delete_image(self, blob_name: str) -> bool:
        """
        Delete image from Azure Blob Storage.
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            ImageProcessingError: If deletion fails
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            
            logger.info("Image deleted from Azure Storage", blob_name=blob_name)
            return True
            
        except ResourceNotFoundError:
            logger.warning("Blob not found for deletion", blob_name=blob_name)
            return False
        except Exception as e:
            logger.error("Failed to delete image from Azure Storage", error=str(e))
            raise ImageProcessingError(f"Failed to delete image: {str(e)}")
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        extensions = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif"
        }
        return extensions.get(content_type, ".png")
    
    async def get_storage_statistics(self) -> dict:
        """
        Get storage usage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            total_size = 0
            blob_count = 0
            
            async for blob in container_client.list_blobs():
                total_size += blob.size
                blob_count += 1
            
            stats = {
                "total_blobs": blob_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "container_name": self.container_name
            }
            
            logger.info("Retrieved storage statistics", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to get storage statistics", error=str(e))
            raise ImageProcessingError(f"Failed to get storage statistics: {str(e)}")


# Global instance
azure_storage = AzureStorageService() 
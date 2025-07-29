"""Image processing service for validation, conversion, and logo overlay."""

import base64
import io
from typing import Tuple
from PIL import Image, ImageDraw
from fastapi import UploadFile

from utils.exceptions import (
    FileSizeExceededError,
    InvalidFileTypeError,
    ImageProcessingError,
    LogoOverlayError
)
from utils.logging_config import get_logger


logger = get_logger(__name__)


async def validate_and_process_image(
    file: UploadFile, 
    max_size_mb: int, 
    allowed_types: list
) -> bytes:
    """
    Validate and process uploaded image.
    
    Args:
        file: FastAPI UploadFile object
        max_size_mb: Maximum allowed file size in MB
        allowed_types: List of allowed MIME types
        
    Returns:
        Image content as bytes
        
    Raises:
        FileSizeExceededError: If file exceeds size limit
        InvalidFileTypeError: If file type is not allowed
        ImageProcessingError: If image processing fails
    """
    try:
        # Read file content
        content = await file.read()
        
        # Validate file size
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise FileSizeExceededError(
                f"File size {file_size_mb:.2f}MB exceeds limit of {max_size_mb}MB"
            )
        
        # Validate file type
        content_type = file.content_type
        if content_type not in allowed_types:
            raise InvalidFileTypeError(
                f"File type {content_type} not allowed. Allowed types: {allowed_types}"
            )
        
        # Validate that it's actually an image by trying to open it
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # Verify it's a valid image
            logger.info(
                "Image validated successfully",
                file_size_mb=round(file_size_mb, 2),
                content_type=content_type,
                image_size=image.size
            )
        except Exception as e:
            raise ImageProcessingError(f"Invalid image file: {str(e)}")
        
        return content
        
    except (FileSizeExceededError, InvalidFileTypeError, ImageProcessingError):
        raise
    except Exception as e:
        logger.error("Unexpected error in image validation", error=str(e))
        raise ImageProcessingError(f"Failed to process image: {str(e)}")


def convert_image_to_base64(image_bytes: bytes, image_format: str = "PNG") -> str:
    """
    Convert image bytes to base64 encoded string with data URI prefix.
    
    Args:
        image_bytes: Image content as bytes
        image_format: Output image format (PNG, JPEG, etc.)
        
    Returns:
        Base64 encoded string with data URI prefix
        
    Raises:
        ImageProcessingError: If conversion fails
    """
    try:
        # Encode to base64
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create data URI with appropriate MIME type
        mime_type = f"image/{image_format.lower()}"
        data_uri = f"data:{mime_type};base64,{base64_encoded}"
        
        logger.info(
            "Image converted to base64",
            format=image_format,
            size_bytes=len(image_bytes)
        )
        
        return data_uri
        
    except Exception as e:
        logger.error("Failed to convert image to base64", error=str(e))
        raise ImageProcessingError(f"Failed to convert image to base64: {str(e)}")


def overlay_logo(background_image_bytes: bytes, logo_path: str) -> bytes:
    """
    Overlay GNB logo onto the generated image.
    
    Args:
        background_image_bytes: Generated image bytes
        logo_path: Path to the GNB logo image
        
    Returns:
        Image with logo overlay as bytes
        
    Raises:
        LogoOverlayError: If logo overlay fails
    """
    try:
        # Open the background image
        background = Image.open(io.BytesIO(background_image_bytes))
        
        # Ensure background is in RGBA mode for transparency support
        if background.mode != 'RGBA':
            background = background.convert('RGBA')
        
        # Open the logo image
        try:
            logo = Image.open(logo_path)
        except FileNotFoundError:
            logger.warning(f"Logo file not found at {logo_path}, skipping overlay")
            # Return original image if logo is not found
            return background_image_bytes
        
        # Ensure logo is in RGBA mode
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')
        
        # Calculate logo size (10% of background width, maintaining aspect ratio)
        bg_width, bg_height = background.size
        logo_width = int(bg_width * 0.1)
        logo_ratio = logo.size[1] / logo.size[0]  # height/width
        logo_height = int(logo_width * logo_ratio)
        
        # Resize logo
        logo_resized = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Position logo in bottom-right corner with padding
        padding = 20
        x_position = bg_width - logo_width - padding
        y_position = bg_height - logo_height - padding
        
        # Create a copy of background for overlay
        result = background.copy()
        
        # Paste logo with transparency
        result.paste(logo_resized, (x_position, y_position), logo_resized)
        
        # Convert back to bytes
        output_buffer = io.BytesIO()
        result.save(output_buffer, format='PNG')
        result_bytes = output_buffer.getvalue()
        
        logger.info(
            "Logo overlay completed",
            logo_size=(logo_width, logo_height),
            position=(x_position, y_position),
            background_size=background.size
        )
        
        return result_bytes
        
    except LogoOverlayError:
        raise
    except Exception as e:
        logger.error("Failed to overlay logo", error=str(e))
        raise LogoOverlayError(f"Failed to overlay logo: {str(e)}")


def resize_image_if_needed(image_bytes: bytes, max_dimension: int = 1024) -> bytes:
    """
    Resize image if it exceeds maximum dimension while maintaining aspect ratio.
    
    Args:
        image_bytes: Image content as bytes
        max_dimension: Maximum width or height in pixels
        
    Returns:
        Resized image bytes or original if no resize needed
        
    Raises:
        ImageProcessingError: If resize fails
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        # Check if resize is needed
        if width <= max_dimension and height <= max_dimension:
            return image_bytes
        
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert back to bytes
        output_buffer = io.BytesIO()
        format_to_use = image.format if image.format else 'PNG'
        resized_image.save(output_buffer, format=format_to_use)
        resized_bytes = output_buffer.getvalue()
        
        logger.info(
            "Image resized",
            original_size=(width, height),
            new_size=(new_width, new_height),
            format=format_to_use
        )
        
        return resized_bytes
        
    except Exception as e:
        logger.error("Failed to resize image", error=str(e))
        raise ImageProcessingError(f"Failed to resize image: {str(e)}") 
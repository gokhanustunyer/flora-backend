"""Tests for image processing services."""

import pytest
import io
from PIL import Image
from fastapi import UploadFile

from services.image_processing import (
    validate_and_process_image,
    convert_image_to_base64,
    overlay_logo,
    resize_image_if_needed
)
from utils.exceptions import (
    FileSizeExceededError,
    InvalidFileTypeError,
    ImageProcessingError,
    LogoOverlayError
)


class TestImageValidation:
    """Tests for image validation and processing."""
    
    @pytest.mark.asyncio
    async def test_validate_image_success(self, sample_dog_image: bytes):
        """Test successful image validation."""
        # Create mock UploadFile
        file = UploadFile(
            filename="test_dog.jpg",
            file=io.BytesIO(sample_dog_image),
            headers={"content-type": "image/jpeg"}
        )
        
        result = await validate_and_process_image(
            file=file,
            max_size_mb=10,
            allowed_types=["image/jpeg", "image/png"]
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify it's a valid image
        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)
    
    @pytest.mark.asyncio
    async def test_validate_image_too_large(self, sample_large_image: bytes):
        """Test file size validation."""
        file = UploadFile(
            filename="large_dog.jpg",
            file=io.BytesIO(sample_large_image),
            headers={"content-type": "image/jpeg"}
        )
        
        with pytest.raises(FileSizeExceededError):
            await validate_and_process_image(
                file=file,
                max_size_mb=1,  # Set very low limit
                allowed_types=["image/jpeg"]
            )
    
    @pytest.mark.asyncio
    async def test_validate_invalid_file_type(self, sample_dog_image: bytes):
        """Test invalid file type validation."""
        file = UploadFile(
            filename="test_dog.txt",
            file=io.BytesIO(sample_dog_image),
            headers={"content-type": "text/plain"}
        )
        
        with pytest.raises(InvalidFileTypeError):
            await validate_and_process_image(
                file=file,
                max_size_mb=10,
                allowed_types=["image/jpeg", "image/png"]
            )
    
    @pytest.mark.asyncio
    async def test_validate_corrupted_image(self, invalid_file: bytes):
        """Test corrupted image validation."""
        file = UploadFile(
            filename="corrupted.jpg",
            file=io.BytesIO(invalid_file),
            headers={"content-type": "image/jpeg"}
        )
        
        with pytest.raises(ImageProcessingError):
            await validate_and_process_image(
                file=file,
                max_size_mb=10,
                allowed_types=["image/jpeg"]
            )


class TestImageConversion:
    """Tests for image format conversion."""
    
    def test_convert_to_base64_png(self, sample_dog_image: bytes):
        """Test PNG to base64 conversion."""
        result = convert_image_to_base64(sample_dog_image, "PNG")
        
        assert result.startswith("data:image/png;base64,")
        assert len(result) > len("data:image/png;base64,")
    
    def test_convert_to_base64_jpeg(self, sample_dog_image: bytes):
        """Test JPEG to base64 conversion."""
        result = convert_image_to_base64(sample_dog_image, "JPEG")
        
        assert result.startswith("data:image/jpeg;base64,")
        assert len(result) > len("data:image/jpeg;base64,")
    
    def test_convert_empty_image(self):
        """Test conversion with empty image data."""
        # Empty bytes should create a valid base64 string, not raise an error
        result = convert_image_to_base64(b"", "PNG")
        assert result.startswith("data:image/png;base64,")
        # The content will be empty but format should be valid


class TestLogoOverlay:
    """Tests for logo overlay functionality."""
    
    def test_overlay_logo_success(self, sample_dog_image: bytes, temp_logo_file: str):
        """Test successful logo overlay."""
        result = overlay_logo(sample_dog_image, temp_logo_file)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify the result is a valid image
        img = Image.open(io.BytesIO(result))
        assert img.mode == 'RGBA'
    
    def test_overlay_logo_missing_file(self, sample_dog_image: bytes):
        """Test logo overlay with missing logo file."""
        # Should return original image when logo is missing
        result = overlay_logo(sample_dog_image, "nonexistent_logo.png")
        
        assert result == sample_dog_image
    
    def test_overlay_logo_invalid_background(self, temp_logo_file: str):
        """Test logo overlay with invalid background image."""
        with pytest.raises(LogoOverlayError):
            overlay_logo(b"invalid image data", temp_logo_file)


class TestImageResizing:
    """Tests for image resizing functionality."""
    
    def test_resize_large_image(self):
        """Test resizing a large image."""
        # Create a large image
        large_img = Image.new('RGB', (2048, 1536), color='blue')
        img_buffer = io.BytesIO()
        large_img.save(img_buffer, format='PNG')
        large_img_bytes = img_buffer.getvalue()
        
        result = resize_image_if_needed(large_img_bytes, max_dimension=1024)
        
        # Check that image was resized
        resized_img = Image.open(io.BytesIO(result))
        assert max(resized_img.size) == 1024
        assert resized_img.size == (1024, 768)  # Maintaining aspect ratio
    
    def test_resize_small_image(self, sample_dog_image: bytes):
        """Test that small images are not resized."""
        result = resize_image_if_needed(sample_dog_image, max_dimension=1024)
        
        # Should return original image data
        assert result == sample_dog_image
    
    def test_resize_square_image(self):
        """Test resizing a square image."""
        # Create a square image larger than max dimension
        square_img = Image.new('RGB', (1500, 1500), color='red')
        img_buffer = io.BytesIO()
        square_img.save(img_buffer, format='PNG')
        square_img_bytes = img_buffer.getvalue()
        
        result = resize_image_if_needed(square_img_bytes, max_dimension=1000)
        
        resized_img = Image.open(io.BytesIO(result))
        assert resized_img.size == (1000, 1000)
    
    def test_resize_portrait_image(self):
        """Test resizing a portrait orientation image."""
        # Create a portrait image
        portrait_img = Image.new('RGB', (800, 1200), color='green')
        img_buffer = io.BytesIO()
        portrait_img.save(img_buffer, format='PNG')
        portrait_img_bytes = img_buffer.getvalue()
        
        result = resize_image_if_needed(portrait_img_bytes, max_dimension=1000)
        
        resized_img = Image.open(io.BytesIO(result))
        assert resized_img.size[1] == 1000  # Height should be max dimension
        assert resized_img.size[0] < 1000    # Width should be proportionally smaller
    
    def test_resize_invalid_image(self):
        """Test resizing with invalid image data."""
        with pytest.raises(ImageProcessingError):
            resize_image_if_needed(b"invalid image data", max_dimension=1024)


class TestImageFormats:
    """Tests for different image format support."""
    
    @pytest.mark.parametrize("format,color_mode", [
        ("JPEG", "RGB"),
        ("PNG", "RGBA"),
        ("WebP", "RGB")
    ])
    def test_different_formats(self, format: str, color_mode: str, temp_logo_file: str):
        """Test processing different image formats."""
        # Create image in specified format
        img = Image.new(color_mode, (500, 500), color='purple')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format=format)
        img_bytes = img_buffer.getvalue()
        
        # Test resizing
        resized = resize_image_if_needed(img_bytes, max_dimension=1024)
        assert len(resized) > 0
        
        # Test base64 conversion
        b64_result = convert_image_to_base64(resized, format)
        assert b64_result.startswith(f"data:image/{format.lower()};base64,")
        
        # Test logo overlay (only for supported formats)
        if format in ["JPEG", "PNG"]:
            overlay_result = overlay_logo(resized, temp_logo_file)
            assert len(overlay_result) > 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_very_small_image(self):
        """Test processing a very small image."""
        tiny_img = Image.new('RGB', (10, 10), color='yellow')
        img_buffer = io.BytesIO()
        tiny_img.save(img_buffer, format='PNG')
        tiny_img_bytes = img_buffer.getvalue()
        
        # Should not be resized
        result = resize_image_if_needed(tiny_img_bytes, max_dimension=1024)
        assert result == tiny_img_bytes
        
        # Should convert to base64 successfully
        b64_result = convert_image_to_base64(result, "PNG")
        assert b64_result.startswith("data:image/png;base64,")
    
    def test_extreme_aspect_ratio(self):
        """Test image with extreme aspect ratio."""
        # Very wide image
        wide_img = Image.new('RGB', (3000, 100), color='cyan')
        img_buffer = io.BytesIO()
        wide_img.save(img_buffer, format='PNG')
        wide_img_bytes = img_buffer.getvalue()
        
        result = resize_image_if_needed(wide_img_bytes, max_dimension=1000)
        
        resized_img = Image.open(io.BytesIO(result))
        assert resized_img.size[0] == 1000  # Width should be max dimension
        assert resized_img.size[1] < 100     # Height should be proportionally smaller
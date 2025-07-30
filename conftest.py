"""Pytest configuration and fixtures for testing."""

import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
import tempfile
import os
from PIL import Image
import io

from main import app
from database.connection import get_db, Base
from config.settings import settings


# Test database URL (in-memory SQLite for testing)  
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"



@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client(test_session):
    """Create test client with database override."""
    
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_dog_image():
    """Create a sample dog image for testing."""
    # Create a simple test image
    img = Image.new('RGB', (512, 512), color='brown')
    
    # Add some simple features to make it look more like a dog
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Draw simple dog-like features
    # Eyes
    draw.ellipse([200, 200, 230, 230], fill='black')
    draw.ellipse([280, 200, 310, 230], fill='black')
    # Nose
    draw.ellipse([245, 260, 265, 280], fill='black')
    # Mouth
    draw.arc([230, 280, 280, 320], 0, 180, fill='black', width=3)
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    img_bytes = img_buffer.getvalue()
    
    return img_bytes


@pytest.fixture
def sample_large_image():
    """Create a large image for size testing."""
    # Create a valid JPEG header + large random data (>10MB)
    jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    large_data = b'x' * (12 * 1024 * 1024)  # 12MB of data
    jpeg_footer = b'\xff\xd9'
    return jpeg_header + large_data + jpeg_footer


@pytest.fixture
def invalid_file():
    """Create an invalid file for testing."""
    return b"This is not an image file"


@pytest.fixture
def mock_stability_success(monkeypatch):
    """Mock successful Stability.ai response."""
    
    async def mock_generate_image(self, image_bytes, dog_description="", timeout=30):
        # Return a simple generated image
        img = Image.new('RGB', (512, 512), color='green')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def mock_health_check(self):
        return True
    
    from services.stability_ai_generation import StabilityAIGenerator
    monkeypatch.setattr(StabilityAIGenerator, 'generate_image', mock_generate_image)
    monkeypatch.setattr(StabilityAIGenerator, 'health_check', mock_health_check)


@pytest.fixture
def mock_stability_failure(monkeypatch):
    """Mock failed Stability.ai response."""
    
    async def mock_generate_image_fail(self, image_bytes, dog_description="", timeout=30):
        from utils.exceptions import AIGenerationFailedError
        raise AIGenerationFailedError("Mock API failure")
    
    def mock_health_check_fail(self):
        return False
    
    from services.stability_ai_generation import StabilityAIGenerator
    monkeypatch.setattr(StabilityAIGenerator, 'generate_image', mock_generate_image_fail)
    monkeypatch.setattr(StabilityAIGenerator, 'health_check', mock_health_check_fail)


@pytest.fixture
def temp_logo_file():
    """Create a temporary logo file for testing."""
    # Create a simple logo image
    img = Image.new('RGBA', (100, 100), color=(0, 128, 0, 128))  # Semi-transparent green
    
    # Add some text or shape
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "GNB", fill='white')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name, format='PNG')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture
def override_settings(monkeypatch, temp_logo_file):
    """Override settings for testing."""
    monkeypatch.setattr(settings, 'gnb_logo_path', temp_logo_file)
    monkeypatch.setattr(settings, 'max_image_size_mb', 10)
    monkeypatch.setattr(settings, 'ai_generation_timeout', 5)
    monkeypatch.setattr(settings, 'debug_mode', True)
"""Tests for Stability.ai integration."""

import pytest
import io
from unittest.mock import Mock, patch, AsyncMock
import requests
from PIL import Image

from services.stability_ai_generation import StabilityAIGenerator
from utils.exceptions import AIGenerationFailedError


class TestStabilityAIGenerator:
    """Tests for StabilityAIGenerator class."""
    
    def test_init_valid_api_key(self):
        """Test initialization with valid API key."""
        generator = StabilityAIGenerator("sk-test-key-123")
        
        assert generator.api_key == "sk-test-key-123"
        assert generator.base_url == "https://api.stability.ai/v2beta/stable-image"
    
    def test_init_invalid_api_key(self):
        """Test initialization with invalid API key format."""
        # Should still initialize but log warning
        generator = StabilityAIGenerator("invalid-key")
        assert generator.api_key == "invalid-key"
    
    def test_create_inpaint_prompt_basic(self):
        """Test basic prompt creation."""
        generator = StabilityAIGenerator("sk-test-key")
        prompt = generator._create_inpaint_prompt()
        
        assert "Good Natured Brand" in prompt
        assert "GNB" in prompt
        assert "cozy" in prompt
        assert "sustainable" in prompt
        assert "photorealistic" in prompt
    
    def test_create_inpaint_prompt_with_context(self):
        """Test prompt creation with additional context."""
        generator = StabilityAIGenerator("sk-test-key")
        prompt = generator._create_inpaint_prompt("golden retriever, playful")
        
        assert "Good Natured Brand" in prompt
        assert "golden retriever, playful" in prompt
    
    def test_create_clothing_mask(self, sample_dog_image: bytes):
        """Test clothing mask creation."""
        generator = StabilityAIGenerator("sk-test-key")
        mask_bytes = generator._create_clothing_mask(sample_dog_image)
        
        assert isinstance(mask_bytes, bytes)
        assert len(mask_bytes) > 0
        
        # Verify it's a valid image
        mask_img = Image.open(io.BytesIO(mask_bytes))
        assert mask_img.mode == 'RGB'
    
    def test_create_clothing_mask_invalid_image(self):
        """Test mask creation with invalid image."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Should return fallback mask
        mask_bytes = generator._create_clothing_mask(b"invalid")
        assert isinstance(mask_bytes, bytes)
        assert len(mask_bytes) > 0
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self, sample_dog_image: bytes):
        """Test successful image generation."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Create a simple generated image
        generated_img = Image.new('RGB', (512, 512), color='green')
        img_buffer = io.BytesIO()
        generated_img.save(img_buffer, format='PNG')
        mock_response.content = img_buffer.getvalue()
        
        with patch('requests.post', return_value=mock_response):
            result = await generator.generate_image(
                image_bytes=sample_dog_image,
                dog_description="friendly golden retriever"
            )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify it's a valid image
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (512, 512)
    
    @pytest.mark.asyncio
    async def test_generate_image_no_input(self):
        """Test generation with no input image."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with pytest.raises(AIGenerationFailedError, match="Image must be successfully uploaded"):
            await generator.generate_image(image_bytes=None)
        
        with pytest.raises(AIGenerationFailedError, match="Image must be successfully uploaded"):
            await generator.generate_image(image_bytes=b"")
    
    @pytest.mark.asyncio
    async def test_generate_image_api_error(self, sample_dog_image: bytes):
        """Test API error handling."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_response.text = "Bad Request"
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(AIGenerationFailedError, match="Stability.ai API error: 400"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_empty_response(self, sample_dog_image: bytes):
        """Test handling empty API response."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(AIGenerationFailedError, match="No image data received"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_invalid_response(self, sample_dog_image: bytes):
        """Test handling invalid image response."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Mock invalid image response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"This is not an image"
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(AIGenerationFailedError, match="Invalid image received"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_connection_error(self, sample_dog_image: bytes):
        """Test connection error handling."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with patch('requests.post', side_effect=requests.ConnectionError("Connection failed")):
            with pytest.raises(AIGenerationFailedError, match="Failed to connect to Stability.ai API"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_timeout(self, sample_dog_image: bytes):
        """Test timeout handling."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with patch('requests.post', side_effect=requests.Timeout("Request timed out")):
            with pytest.raises(AIGenerationFailedError, match="Failed to connect to Stability.ai API"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_quota_exceeded(self, sample_dog_image: bytes):
        """Test quota exceeded error."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with patch('requests.post', side_effect=Exception("Quota exceeded")):
            with pytest.raises(AIGenerationFailedError, match="Stability.ai API quota or rate limit exceeded"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_auth_error(self, sample_dog_image: bytes):
        """Test authentication error."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with patch('requests.post', side_effect=Exception("Authentication failed")):
            with pytest.raises(AIGenerationFailedError, match="Stability.ai API authentication failed"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    @pytest.mark.asyncio
    async def test_generate_image_content_policy(self, sample_dog_image: bytes):
        """Test content policy error."""
        generator = StabilityAIGenerator("sk-test-key")
        
        with patch('requests.post', side_effect=Exception("Content policy violation")):
            with pytest.raises(AIGenerationFailedError, match="Image generation failed: Content policy violation"):
                await generator.generate_image(image_bytes=sample_dog_image)
    
    def test_health_check_success(self):
        """Test successful health check."""
        generator = StabilityAIGenerator("sk-valid-key-12345")
        
        result = generator.health_check()
        assert result is True
    
    def test_health_check_invalid_key(self):
        """Test health check with invalid key."""
        generator = StabilityAIGenerator("invalid-key")
        
        result = generator.health_check()
        assert result is False
    
    def test_health_check_short_key(self):
        """Test health check with short key."""
        generator = StabilityAIGenerator("sk-123")
        
        result = generator.health_check()
        assert result is False


class TestStabilityAIIntegration:
    """Integration tests for Stability.ai service."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self, sample_dog_image: bytes):
        """Test full pipeline with mocked API."""
        generator = StabilityAIGenerator("sk-test-key")
        
        # Mock the entire request flow
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Create realistic generated image
        generated_img = Image.new('RGB', (512, 512), color='brown')
        # Add some visual elements to simulate a dog with clothing
        from PIL import ImageDraw
        draw = ImageDraw.Draw(generated_img)
        draw.rectangle([100, 200, 400, 400], fill='blue')  # Simulate clothing
        
        img_buffer = io.BytesIO()
        generated_img.save(img_buffer, format='PNG')
        mock_response.content = img_buffer.getvalue()
        
        with patch('requests.post', return_value=mock_response) as mock_post:
            result = await generator.generate_image(
                image_bytes=sample_dog_image,
                dog_description="happy golden retriever",
                timeout=30
            )
            
            # Verify API call was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Check URL
            assert "inpaint" in call_args[0][0]
            
            # Check headers
            assert "authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["authorization"].startswith("Bearer sk-")
            
            # Check files were sent
            assert "image" in call_args[1]["files"]
            assert "mask" in call_args[1]["files"]
            
            # Check data
            assert "prompt" in call_args[1]["data"]
            assert "Good Natured Brand" in call_args[1]["data"]["prompt"]
        
        # Verify result
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify it's a valid image
        result_img = Image.open(io.BytesIO(result))
        assert result_img.mode == 'RGB'


class TestPromptEngineering:
    """Tests for prompt engineering and creation."""
    
    def test_prompt_contains_brand_elements(self):
        """Test that prompts contain required brand elements."""
        generator = StabilityAIGenerator("sk-test-key")
        prompt = generator._create_inpaint_prompt("cute puppy")
        
        # Check for brand mentions
        assert "Good Natured Brand" in prompt or "GNB" in prompt
        
        # Check for apparel descriptions
        assert any(word in prompt.lower() for word in ['sweater', 'jacket', 'bandana', 'apparel'])
        
        # Check for quality descriptors
        assert any(word in prompt.lower() for word in ['cozy', 'premium', 'comfortable'])
        
        # Check for material descriptions
        assert any(word in prompt.lower() for word in ['natural', 'sustainable'])
        
        # Check for style requirements
        assert "photorealistic" in prompt.lower()
    
    def test_prompt_with_different_dog_descriptions(self):
        """Test prompt generation with various dog descriptions."""
        generator = StabilityAIGenerator("sk-test-key")
        
        test_cases = [
            "golden retriever, playful",
            "small terrier, energetic", 
            "large german shepherd, calm",
            "mixed breed, friendly"
        ]
        
        for dog_desc in test_cases:
            prompt = generator._create_inpaint_prompt(dog_desc)
            
            # Should contain the dog description
            assert dog_desc in prompt
            
            # Should still contain brand elements
            assert "Good Natured Brand" in prompt or "GNB" in prompt
            
            # Should be reasonably long (detailed prompt)
            assert len(prompt) > 200
    
    def test_prompt_structure(self):
        """Test the structure and quality of generated prompts."""
        generator = StabilityAIGenerator("sk-test-key")
        prompt = generator._create_inpaint_prompt()
        
        # Should be substantial length
        assert len(prompt) > 100
        
        # Should contain specific styling instructions
        assert "photorealistic" in prompt.lower()
        assert "professional" in prompt.lower()
        
        # Should contain setting descriptions
        assert any(word in prompt.lower() for word in ['lighting', 'background', 'environment'])
        
        # Should contain dog welfare considerations
        assert "comfortable" in prompt.lower() or "well-fitted" in prompt.lower()
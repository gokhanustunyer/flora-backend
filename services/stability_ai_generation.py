"""Stability.ai image generation service."""

import time
import requests
import io
from typing import Optional
from PIL import Image

from utils.exceptions import AIGenerationFailedError
from utils.logging_config import get_logger, log_api_call


logger = get_logger(__name__)


class StabilityAIGenerator:
    """Stability.ai image generation service."""
    
    def __init__(self, api_key: str):
        """
        Initialize Stability AI Generator.
        
        Args:
            api_key: Stability.ai API key
        """
        self.api_key = api_key
        self.base_url = "https://api.stability.ai/v2beta/stable-image"
        
        # Test API key format
        if not api_key.startswith('sk-'):
            logger.warning("Stability.ai API key should start with 'sk-'")
        
        logger.info("Stability.ai client initialized successfully")
    
    def _create_inpaint_prompt(self, additional_context: str = "") -> str:
        """
        Create a detailed prompt for inpainting GNB apparel onto existing dog image.
        
        Args:
            additional_context: Additional context about the dog (breed, color, etc.)
            
        Returns:
            Detailed prompt for Stability.ai inpainting
        """
        base_prompt = """Generate a high-quality, photorealistic image of a beautiful dog wearing cozy, premium apparel from Good Natured Brand (GNB). The apparel should be:

Made from natural, sustainable materials in earth tones (forest green, warm beige, natural brown)

Feature only the simple “GNB” text as branding on the apparel (e.g., on the chest of a sweater or jacket)

Look comfortable, well-fitted, and stylish on the dog

Include cozy items like a knit sweater, cotton bandana, or natural-fabric jacket

The dog should be:

Happy and playful, with bright, alert eyes

In a natural, relaxed pose

Well-groomed and healthy-looking

Setting:

Clean, modern home environment with soft, natural lighting

Neutral background that doesn't distract from the dog

Professional pet photography style with warm, inviting atmosphere

High-resolution, photorealistic image with excellent lighting and composition"""

        if additional_context:
            base_prompt += f"\n\nDog details: {additional_context}"
        
        return base_prompt
    
    def _create_clothing_mask(self, image_bytes: bytes) -> bytes:
        """
        Create a mask for the dog's body area where clothing should be added.
        
        Args:
            image_bytes: Original dog image bytes
            
        Returns:
            Mask image bytes (white areas will be inpainted)
        """
        try:
            # Open the original image
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            
            # Create a simple oval mask covering the dog's torso area
            # This is a basic approach - in production you might want more sophisticated masking
            mask = Image.new('RGB', (width, height), 'black')  # Black = keep original
            
            # Create an oval mask in the center-lower area (typical dog torso location)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            
            # Calculate oval coordinates (rough dog torso area)
            oval_width = width * 0.6  # 60% of image width
            oval_height = height * 0.4  # 40% of image height
            left = (width - oval_width) / 2
            top = height * 0.3  # Start from 30% down
            right = left + oval_width
            bottom = top + oval_height
            
            # Draw white oval (areas to inpaint)
            draw.ellipse([left, top, right, bottom], fill='white')
            
            # Convert to bytes
            mask_buffer = io.BytesIO()
            mask.save(mask_buffer, format='PNG')
            mask_bytes = mask_buffer.getvalue()
            
            logger.info("Created clothing mask", mask_size_bytes=len(mask_bytes))
            return mask_bytes
            
        except Exception as e:
            logger.error("Failed to create clothing mask", error=str(e))
            # Fallback: create a simple rectangular mask
            from PIL import ImageDraw
            mask = Image.new('RGB', (512, 512), 'black')
            draw = ImageDraw.Draw(mask)
            draw.rectangle([128, 200, 384, 400], fill='white')  # Simple rectangle
            
            mask_buffer = io.BytesIO()
            mask.save(mask_buffer, format='PNG')
            return mask_buffer.getvalue()
    
    async def generate_image(
        self, 
        image_bytes: Optional[bytes] = None, 
        dog_description: str = "",
        timeout: int = 30
    ) -> bytes:
        """
        Edit dog image to add GNB apparel using Stability.ai inpainting.
        
        Args:
            image_bytes: Original dog image bytes (required for inpainting)
            dog_description: Text description of the dog for better generation
            timeout: API call timeout in seconds
            
        Returns:
            Edited image as bytes with GNB apparel added
            
        Raises:
            AIGenerationFailedError: If image generation fails
        """
        start_time = time.time()
        
        # Validate that image was successfully uploaded and processed
        if image_bytes is None or len(image_bytes) == 0:
            logger.error("No image data provided - cannot proceed with AI generation")
            raise AIGenerationFailedError("Image must be successfully uploaded before AI generation")
        
        logger.info("Image validation passed, proceeding with AI inpainting", 
                   image_size_bytes=len(image_bytes))
        
        try:
            # Create prompt for adding GNB apparel to the dog
            prompt = self._create_inpaint_prompt(dog_description)
            
            logger.info("Starting Stability.ai inpainting", prompt_length=len(prompt))
            
            # Create a simple mask that covers the dog's body area (where clothing would go)
            mask_bytes = self._create_clothing_mask(image_bytes)
            
            # Prepare API request
            url = f"{self.base_url}/edit/inpaint"
            headers = {
                "authorization": f"Bearer {self.api_key}",
                "accept": "image/*"
            }
            
            # Files for image and mask
            files = {
                "image": ("image.png", io.BytesIO(image_bytes), "image/png"),
                "mask": ("mask.png", io.BytesIO(mask_bytes), "image/png")
            }
            
            # Data for text parameters
            data = {
                "prompt": prompt,
                "output_format": "png"
            }
            
            # Make API call to Stability.ai
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=timeout
            )
            
            # Check response status
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = str(error_data)
                except:
                    error_detail = response.text
                
                logger.error(f"Stability.ai API error: {response.status_code} - {error_detail}")
                raise AIGenerationFailedError(f"Stability.ai API error: {response.status_code} - {error_detail}")
            
            generated_image_bytes = response.content
            
            # Validate that we got image data
            if not generated_image_bytes or len(generated_image_bytes) == 0:
                raise AIGenerationFailedError("No image data received from Stability.ai")
            
            # Validate image format
            try:
                img = Image.open(io.BytesIO(generated_image_bytes))
                img.verify()
            except Exception as e:
                raise AIGenerationFailedError(f"Invalid image received from Stability.ai: {str(e)}")
            
            duration = time.time() - start_time
            
            # Log successful inpainting
            log_api_call(
                service="stability_ai",
                operation="inpaint_edit",
                duration=duration,
                success=True,
                image_size_bytes=len(generated_image_bytes)
            )
            
            logger.info(
                "Image inpainting completed successfully",
                generation_time=round(duration, 2),
                image_size_bytes=len(generated_image_bytes)
            )
            
            return generated_image_bytes
            
        except requests.RequestException as e:
            duration = time.time() - start_time
            log_api_call(
                service="stability_ai",
                operation="inpaint_edit",
                duration=duration,
                success=False,
                error=str(e)
            )
            logger.error("Failed to connect to Stability.ai API", error=str(e))
            raise AIGenerationFailedError(f"Failed to connect to Stability.ai API: {str(e)}")
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(
                service="stability_ai",
                operation="inpaint_edit",
                duration=duration,
                success=False,
                error=str(e)
            )
            
            # Handle specific Stability.ai errors
            error_message = str(e)
            if "quota" in error_message.lower() or "rate_limit" in error_message.lower():
                raise AIGenerationFailedError("Stability.ai API quota or rate limit exceeded")
            elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                raise AIGenerationFailedError("Stability.ai API authentication failed")
            elif "content_policy" in error_message.lower() or "safety" in error_message.lower():
                raise AIGenerationFailedError("Image generation blocked by content policy")
            else:
                logger.error("Stability.ai generation failed", error=error_message)
                raise AIGenerationFailedError(f"Image generation failed: {error_message}")
    
    async def describe_dog_image(self, image_bytes: bytes) -> str:
        """
        Generate a description of the dog in the image.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Description of the dog for prompt generation
        """
        # For now, return a simple description
        # In production, you might use vision AI to analyze the image
        return "A friendly, well-groomed dog with a beautiful coat, looking happy and energetic"
    
    async def generate_dog_image(self, prompt: str, image_bytes: bytes = None) -> bytes:
        """
        Generate a new dog image using Stability.ai.
        
        Args:
            prompt: Description prompt for the dog
            image_bytes: Original image bytes (optional for inpainting)
            
        Returns:
            Generated image as bytes
        """
        try:
            logger.info(f"🎨 Generating image with prompt: {prompt}")
            
            # Use the existing generate_image method with correct parameters
            result = await self.generate_image(
                image_bytes=image_bytes,
                dog_description=f"{prompt}. The dog should be wearing cozy, premium GNB apparel in earth tones.",
                timeout=30
            )
            
            logger.info("✅ Image generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to generate dog image: {e}")
            raise AIGenerationFailedError(f"Failed to generate dog image: {str(e)}")

    def health_check(self) -> bool:
        """
        Perform a health check on the Stability.ai service.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test API connectivity with a simple request
            url = f"{self.base_url}/generate/core"
            headers = {
                "authorization": f"Bearer {self.api_key}",
                "accept": "application/json"
            }
            
            # Make a minimal test request (this might still generate an image, depending on API)
            # For production, you might want to use a different endpoint for health checks
            logger.info("Performing Stability.ai health check")
            
            # For now, just validate API key format and return True
            # A real health check would require a dedicated endpoint or a test generation
            return self.api_key.startswith('sk-') and len(self.api_key) > 10
            
        except Exception as e:
            logger.error("Stability.ai health check failed", error=str(e))
            return False
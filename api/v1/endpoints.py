"""FastAPI endpoints for the image generation API - Simplified version using only Supabase."""

import time
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from api.schemas import ImageGenerationResponse, ErrorResponse, HealthResponse
from services.image_processing import (
    validate_and_process_image,
    convert_image_to_base64,
    overlay_logo
)
from services.stability_ai_generation import StabilityAIGenerator
from services.supabase_client import supabase_service
from services.local_storage import LocalStorageService
from utils.exceptions import (
    FileSizeExceededError,
    InvalidFileTypeError,
    ImageProcessingError,
    AIGenerationFailedError
)
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Initialize router
router = APIRouter()

# Initialize services
try:
    from config.settings import settings
    stability_generator = StabilityAIGenerator(api_key=settings.stability_ai_api_key)
    logger.info("✅ Stability.ai generator initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Stability.ai generator: {e}")
    stability_generator = None

# Initialize local storage
try:
    local_storage = LocalStorageService()
    logger.info("✅ Local storage initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize local storage: {e}")
    local_storage = None

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    stability_healthy = stability_generator is not None
    supabase_healthy = supabase_service.is_available()
    
    return {
        "status": "healthy" if (stability_healthy and supabase_healthy) else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "stability_ai": "healthy" if stability_healthy else "unhealthy",
            "supabase": "healthy" if supabase_healthy else "unhealthy"
        }
    }

@router.post("/generate")
async def generate_image(
    image: UploadFile = File(...),
):
    """Generate a new image using Stability.ai based on the uploaded image."""
    start_time = time.time()
    
    try:
        # Validate services
        if not stability_generator:
            error_response = {"success": False, "error": "Stability.ai service is not available"}
            return JSONResponse(content=error_response, status_code=503)
        
        if not supabase_service.is_available():
            error_response = {"success": False, "error": "Database service is not available"}
            return JSONResponse(content=error_response, status_code=503)
        
        # Read file content first
        file_content = await image.read()
        
        # 🔍 TIP KONTROLÜ
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if not image.content_type or image.content_type not in allowed_types:
            error_response = {
                "success": False,
                "error": f"❌ Geçersiz dosya tipi! İzin verilen tipler: JPEG, PNG, WebP. Gönderilen: {image.content_type}"
            }
            return JSONResponse(content=error_response, status_code=400)
        
        # 📏 BOYUT KONTROLÜ (10MB sınırı)
        max_size_mb = 10
        max_size_bytes = max_size_mb * 1024 * 1024  # 10MB = 10 * 1024 * 1024 bytes
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if len(file_content) > max_size_bytes:
            error_response = {
                "success": False,
                "error": f"❌ Dosya çok büyük! Maksimum boyut: {max_size_mb}MB. Gönderilen: {file_size_mb:.1f}MB"
            }
            return JSONResponse(content=error_response, status_code=413)
        
        logger.info(f"✅ Dosya validasyonu başarılı - Tip: {image.content_type}, Boyut: {file_size_mb:.2f}MB")
        
        # Image is already validated, use the file_content directly
        processed_image = file_content
        
        # Create database record with proper parameters
        generation_id = str(uuid.uuid4())
        
        # Get image format from content type
        image_format = image.content_type.split('/')[-1] if image.content_type else 'unknown'
        
        logger.info(f"📝 Creating Supabase record: filename={image.filename}, size={len(file_content)}, format={image_format}")
        
        record = await supabase_service.insert_generation_record(
            original_filename=image.filename,
            original_size=len(file_content),
            original_format=image_format,
            status="processing"
        )
        
        if record:
            generation_id = record.get("id", generation_id)
            logger.info(f"✅ Supabase record created with ID: {generation_id}")
        else:
            logger.warning("⚠️ Failed to create Supabase record, continuing without DB tracking")
        
        try:
            # Generate dog description using AI
            dog_description = await stability_generator.describe_dog_image(processed_image)
            
            # Generate new image using Stability.ai (pass original image for inpainting)
            generated_image = await stability_generator.generate_dog_image(dog_description, processed_image)
            
            # Use generated image as final image
            final_image = generated_image
            logo_applied = False
            
            # Save images to local storage
            original_url = None
            generated_url = None
            
            if local_storage:
                logger.info("💾 Starting local storage save operations...")
                try:
                    # Save original image (bytes)
                    logger.info(f"💾 Saving original image: {image.filename}, size: {len(processed_image)} bytes")
                    original_url = local_storage.save_image(
                        processed_image, 
                        image.filename, 
                        folder="originals"
                    )
                    logger.info(f"✅ Original image saved: {original_url}")
                    
                    # Save generated image (convert PIL Image to bytes first)
                    import io
                    img_bytes = io.BytesIO()
                    final_image.save(img_bytes, format='PNG')
                    generated_bytes = img_bytes.getvalue()
                    
                    logger.info(f"💾 Saving generated image: size: {len(generated_bytes)} bytes")
                    generated_url = local_storage.save_image(
                        generated_bytes, 
                        f"generated_{image.filename.split('.')[0]}.png", 
                        folder="generations"
                    )
                    logger.info(f"✅ Generated image saved: {generated_url}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to save images to storage: {e}")
                    import traceback
                    logger.error(f"🔍 Storage error traceback: {traceback.format_exc()}")
            else:
                logger.warning("⚠️ Local storage not available!")
            
            # Convert to base64
            final_base64 = convert_image_to_base64(final_image)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update database record
            if record:
                logger.info(f"📝 Updating Supabase record {generation_id} to completed")
                # Update with URLs and processing info
                update_result = await supabase_service.update_generation_status(
                    record_id=generation_id,
                    status="completed",
                    processing_time=processing_time
                )
                
                # Update with URLs if we have them
                logger.info(f"🔍 Checking URLs for update: original={original_url}, generated={generated_url}")
                if original_url or generated_url:
                    logger.info(f"📝 Updating Supabase record {generation_id} with URLs")
                    try:
                        update_data = {
                            "prompt_used": dog_description
                        }
                        if original_url:
                            update_data["original_image_url"] = original_url
                        if generated_url:
                            update_data["generated_image_url"] = generated_url
                            
                        logger.info(f"📝 Update data: {update_data}")
                        
                        result = await supabase_service.client.table('image_generations').update(update_data).eq('id', generation_id).execute()
                        logger.info(f"✅ URLs updated in Supabase record {generation_id}: {result.data}")
                    except Exception as url_error:
                        logger.error(f"❌ Failed to update URLs in Supabase: {url_error}")
                        import traceback
                        logger.error(f"🔍 URL update traceback: {traceback.format_exc()}")
                else:
                    logger.warning(f"⚠️ No URLs to update for record {generation_id}")
                if update_result:
                    logger.info(f"✅ Supabase record {generation_id} updated successfully")
                else:
                    logger.warning(f"⚠️ Failed to update Supabase record {generation_id}")
            
            # Standard API response format
            return {
                "success": True,
                "data": {
                    "base64Image": final_base64
                }
            }
            
        except Exception as e:
            # Update database record with error
            if record:
                logger.info(f"📝 Updating Supabase record {generation_id} to failed")
                update_result = await supabase_service.update_generation_status(
                    record_id=generation_id,
                    status="failed",
                    error_message=str(e),
                    processing_time=time.time() - start_time
                )
                if update_result:
                    logger.info(f"✅ Supabase error record {generation_id} updated successfully")
                else:
                    logger.warning(f"⚠️ Failed to update Supabase error record {generation_id}")
            # Standard error response format
            return {
                "success": False,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
                "success": False,
            "error": str(e)
        }

@router.get("/generations")
async def get_generations(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None)
):
    """Get paginated list of image generations."""
    if not supabase_service.is_available():
        raise HTTPException(status_code=503, detail="Database service is not available")
    
    try:
        offset = (page - 1) * limit
        query = supabase_service.client.table("image_generations").select("*")
        
        if status:
            query = query.eq("status", status)
        
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        generations = response.data if response.data else []
        
        return {
            "generations": generations,
                "pagination": {
                    "page": page,
                    "limit": limit,
                "total_count": len(generations)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch generations")

@router.get("/statistics")
async def get_statistics():
    """Get generation statistics."""
    if not supabase_service.is_available():
        raise HTTPException(status_code=503, detail="Database service is not available")
    
    try:
        completed_response = supabase_service.client.table("image_generations").select("*", count="exact").eq("status", "completed").execute()
        failed_response = supabase_service.client.table("image_generations").select("*", count="exact").eq("status", "failed").execute()
        
        status_breakdown = {
            "completed": completed_response.count if hasattr(completed_response, "count") else 0,
            "failed": failed_response.count if hasattr(failed_response, "count") else 0
        }
        
        return {
            "total_generations": sum(status_breakdown.values()),
            "status_breakdown": status_breakdown,
            "services": {
                "stability_ai": "healthy" if stability_generator else "unhealthy",
                "supabase": "healthy" if supabase_service.is_available() else "unhealthy"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")
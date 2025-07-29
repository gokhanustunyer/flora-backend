"""FastAPI endpoints for the image generation API."""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ImageGenerationResponse, ErrorResponse, HealthResponse
from database.connection import get_db, check_database_health
from models.image_generation import ImageGeneration
from services.image_processing import (
    validate_and_process_image,
    convert_image_to_base64,
    overlay_logo,
    resize_image_if_needed
)
from services.stability_ai_generation import StabilityAIGenerator
from services.local_storage import LocalStorageService
from services.supabase_client import supabase_service
from config.settings import settings
from utils.exceptions import (
    FileSizeExceededError,
    InvalidFileTypeError,
    ImageProcessingError,
    LogoOverlayError,
    AIGenerationFailedError
)
from utils.logging_config import get_logger, log_request, log_response, log_error
from sqlalchemy import desc, func, select
from typing import Optional
from fastapi.responses import Response
import io


logger = get_logger(__name__)
router = APIRouter()

# Initialize Stability AI Generator
stability_generator = StabilityAIGenerator(
    api_key=settings.stability_ai_api_key
)

# Initialize storage service - fallback to local storage for development
try:
    if settings.storage_enabled:
        from services.supabase_storage import SupabaseStorageService
        storage_service = SupabaseStorageService()
        logger.info("Supabase storage service initialized successfully")
    else:
        storage_service = None
        logger.info("Storage service disabled")
except Exception as e:
    logger.warning(f"Failed to initialize Supabase storage, using local storage: {e}")
    storage_service = LocalStorageService()
    logger.info("Local storage service initialized as fallback")


@router.post(
    "/generate",
    response_model=ImageGenerationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Generate AI image of dog with GNB apparel",
    description="Upload a dog photo and receive an AI-generated image of a dog wearing GNB-branded apparel"
)
async def generate_dog_image(
    image: UploadFile = File(
        ...,
        description="Dog image file (JPEG, PNG, or WebP)",
        media_type="multipart/form-data"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an AI image of a dog wearing GNB apparel.
    
    This endpoint:
    1. Validates the uploaded dog image
    2. Uses Stability.ai image-to-image to transform the dog with GNB apparel
    3. Overlays the GNB logo on the transformed image
    4. Returns the final image as a base64-encoded string
    """
    start_time = time.time()
    generation_record = None
    
    # Log request
    log_request(
        endpoint="/api/v1/generate",
        method="POST",
        filename=image.filename,
        content_type=image.content_type
    )
    
    try:
        # Create database record if database is enabled
        if db is not None:
            try:
                generation_record = ImageGeneration(
                    original_image_filename=image.filename,
                    original_image_format=image.content_type.split('/')[-1] if image.content_type else None,
                    status="processing",
                    started_at=datetime.now(timezone.utc)
                )
                db.add(generation_record)
                await db.commit()
                await db.refresh(generation_record)
                logger.info(f"Created generation record with ID: {generation_record.id}")
            except Exception as db_error:
                logger.warning(f"Failed to create database record, continuing without DB tracking: {db_error}")
                generation_record = None
                db = None
        
        # Step 1: Validate and process uploaded image
        logger.info("Starting image validation", filename=image.filename)
        
        original_image_bytes = await validate_and_process_image(
            file=image,
            max_size_mb=settings.max_image_size_mb,
            allowed_types=settings.allowed_image_types
        )
        
        # Update database record with original image info
        if generation_record and db:
            try:
                generation_record.original_image_size = len(original_image_bytes)
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Step 2: Resize image if needed to optimize processing
        processed_image_bytes = resize_image_if_needed(
            image_bytes=original_image_bytes,
            max_dimension=settings.max_image_dimension
        )
        
        # Step 3: Edit image using Stability.ai inpainting
        logger.info("Starting AI image inpainting")
        
        # Use a generic dog description for Stability.ai inpainting
        dog_description = "a friendly, well-groomed dog"
        
        # Update database record with prompt
        if generation_record and db:
            try:
                generation_record.dog_description = dog_description
                generation_record.prompt_used = stability_generator._create_dog_prompt(dog_description)
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        generated_image_bytes = await stability_generator.generate_image(
            image_bytes=processed_image_bytes,
            dog_description=dog_description,
            timeout=settings.ai_generation_timeout
        )
        
        # Update database record with generated image info
        if generation_record and db:
            try:
                generation_record.generated_image_size = len(generated_image_bytes)
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Step 4: Overlay GNB logo on generated image
        logger.info("Starting logo overlay")
        
        final_image_bytes = overlay_logo(
            background_image_bytes=generated_image_bytes,
            logo_path=settings.gnb_logo_path
        )
        
        # Update database record with logo overlay success
        if generation_record and db:
            try:
                generation_record.logo_applied = True
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Step 5: Store images to cloud storage if enabled
        original_image_url = None
        generated_image_url = None
        
        if storage_service:
            try:
                logger.info("Uploading images to storage")
                
                # Upload original image
                _, original_image_url = await storage_service.upload_image(
                    image_bytes=original_image_bytes,
                    filename=image.filename or "original.jpg",
                    folder="originals",
                    content_type=image.content_type or "image/jpeg"
                )
                
                # Upload generated image  
                _, generated_image_url = await storage_service.upload_image(
                    image_bytes=final_image_bytes,
                    filename="generated.png",
                    folder="generations",
                    content_type="image/png"
                )
                
                # Update database with storage URLs
                if generation_record and db:
                    try:
                        generation_record.original_image_url = original_image_url
                        generation_record.generated_image_url = generated_image_url
                        await db.commit()
                        logger.info(f"Updated database with storage URLs")
                    except Exception as db_error:
                        logger.warning(f"Failed to update database with URLs: {db_error}")
                        
                logger.info("Images uploaded to storage successfully")
                
            except Exception as storage_error:
                logger.warning(f"Failed to upload images to storage: {storage_error}")
                # Continue without storage - don't fail the whole request
        
        # Step 6: Convert to base64 for response
        logger.info("Converting image to base64")
        
        base64_image = convert_image_to_base64(
            image_bytes=final_image_bytes,
            image_format="PNG"
        )
        
        # Calculate processing time and mark as completed
        duration = time.time() - start_time
        
        if generation_record and db:
            try:
                generation_record.update_status("completed")
                generation_record.processing_time = duration
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Log successful response
        log_response(
            endpoint="/api/v1/generate",
            status_code=200,
            duration=duration,
            processing_time=round(duration, 2)
        )
        
        # Insert record to Supabase using direct client
        supabase_record_id = None
        if supabase_service.is_available():
            try:
                supabase_record = await supabase_service.insert_generation_record(
                    original_filename=image.filename or "unknown.jpg",
                    original_url=original_image_url,
                    original_size=len(original_image_bytes),
                    original_format=image.content_type.split('/')[-1] if image.content_type else None,
                    generated_url=generated_image_url,
                    generated_size=len(final_image_bytes),
                    prompt_used=stability_generator._create_dog_prompt(dog_description),
                    dog_description=dog_description,
                    processing_time=duration,
                    status="completed",
                    logo_applied=True
                )
                if supabase_record:
                    supabase_record_id = supabase_record.get('id')
                    logger.info(f"✅ Supabase record created: {supabase_record_id}")
            except Exception as supabase_error:
                logger.warning(f"⚠️ Failed to create Supabase record: {supabase_error}")
        
        logger.info(
            "Image generation completed successfully",
            total_time=round(duration, 2),
            final_image_size=len(final_image_bytes),
            generation_id=str(generation_record.id) if generation_record else None,
            supabase_record_id=supabase_record_id
        )
        
        return ImageGenerationResponse(
            success=True,
            data={
                "base64Image": base64_image,
                "message": f"Image generated successfully in {round(duration, 2)}s",
                "generation_id": str(generation_record.id) if generation_record else None
            },
            error=None
        )
        
    except FileSizeExceededError as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("failed", str(e))
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 400, duration)
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "FileSizeExceeded",
                "message": e.message,
                "details": e.details
            }
        )
        
    except InvalidFileTypeError as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("failed", str(e))
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 400, duration)
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidFileType",
                "message": e.message,
                "details": f"Allowed types: {settings.allowed_image_types}"
            }
        )
        
    except ImageProcessingError as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("failed", str(e))
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
            
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 400, duration)
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ImageProcessingError",
                "message": e.message,
                "details": e.details
            }
        )
        

        
    except AIGenerationFailedError as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("failed", str(e))
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Insert failed record to Supabase
        if supabase_service.is_available():
            try:
                await supabase_service.insert_generation_record(
                    original_filename=image.filename or "unknown.jpg",
                    original_url=original_image_url if 'original_image_url' in locals() else None,
                    original_size=len(original_image_bytes) if 'original_image_bytes' in locals() else None,
                    original_format=image.content_type.split('/')[-1] if image.content_type else None,
                    prompt_used=stability_generator._create_dog_prompt(dog_description) if 'dog_description' in locals() else None,
                    dog_description=dog_description if 'dog_description' in locals() else None,
                    processing_time=duration,
                    status="failed",
                    logo_applied=False,
                    error_message=f"AI Generation failed: {str(e)}"
                )
                logger.info("✅ Supabase AI generation error record created")
            except Exception as supabase_error:
                logger.warning(f"⚠️ Failed to create Supabase error record: {supabase_error}")
            
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 500, duration)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "AIGenerationFailed",
                "message": e.message,
                "details": e.details
            }
        )
        
    except LogoOverlayError as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("completed", f"Logo overlay failed: {str(e)}")
                generation_record.logo_applied = False
                generation_record.processing_time = duration
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 500, duration)
        
        # Insert record to Supabase even if logo overlay failed
        supabase_record_id = None
        if supabase_service.is_available():
            try:
                supabase_record = await supabase_service.insert_generation_record(
                    original_filename=image.filename or "unknown.jpg",
                    original_url=original_image_url,
                    original_size=len(original_image_bytes),
                    original_format=image.content_type.split('/')[-1] if image.content_type else None,
                    generated_url=generated_image_url,
                    generated_size=len(generated_image_bytes) if 'generated_image_bytes' in locals() else None,
                    prompt_used=stability_generator._create_dog_prompt(dog_description),
                    dog_description=dog_description,
                    processing_time=duration,
                    status="completed",
                    logo_applied=False,
                    error_message=f"Logo overlay failed: {str(e)}"
                )
                if supabase_record:
                    supabase_record_id = supabase_record.get('id')
                    logger.info(f"✅ Supabase record created (logo failed): {supabase_record_id}")
            except Exception as supabase_error:
                logger.warning(f"⚠️ Failed to create Supabase record: {supabase_error}")
        
        # Return generated image without logo if overlay fails
        logger.warning("Logo overlay failed, returning image without logo")
        
        base64_image = convert_image_to_base64(
            image_bytes=generated_image_bytes,
            image_format="PNG"
        )
        
        return ImageGenerationResponse(
            success=True,
            data={
                "base64Image": base64_image,
                "message": f"Image generated successfully in {round(duration, 2)}s (logo overlay failed)",
                "generation_id": str(generation_record.id) if generation_record else None
            },
            error=None
        )
        
    except Exception as e:
        duration = time.time() - start_time
        if generation_record and db:
            try:
                generation_record.update_status("failed", f"Unexpected error: {str(e)}")
                await db.commit()
            except Exception as db_error:
                logger.warning(f"Failed to update database record: {db_error}")
        
        # Insert failed record to Supabase
        if supabase_service.is_available():
            try:
                await supabase_service.insert_generation_record(
                    original_filename=image.filename or "unknown.jpg",
                    original_url=original_image_url if 'original_image_url' in locals() else None,
                    original_size=len(original_image_bytes) if 'original_image_bytes' in locals() else None,
                    original_format=image.content_type.split('/')[-1] if image.content_type else None,
                    processing_time=duration,
                    status="failed",
                    logo_applied=False,
                    error_message=f"Unexpected error: {str(e)}"
                )
                logger.info("✅ Supabase error record created")
            except Exception as supabase_error:
                logger.warning(f"⚠️ Failed to create Supabase error record: {supabase_error}")
            
        log_error(e, {"endpoint": "/api/v1/generate", "duration": duration})
        log_response("/api/v1/generate", 500, duration)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during image generation",
                "details": str(e)
            }
        )


@router.get(
    "/test-supabase",
    summary="Test Supabase connection",
    description="Test the direct Supabase client connection and insert a test record"
)
async def test_supabase_connection():
    """Test Supabase connection and insert a test record."""
    
    if not supabase_service.is_available():
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Supabase client not available. Check your SUPABASE_URL and SUPABASE_KEY environment variables.",
                "data": None
            }
        )
    
    try:
        # Insert a test record
        test_record = await supabase_service.insert_generation_record(
            original_filename=f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            original_url="https://example.com/test-image.jpg",
            original_size=1024000,
            original_format="JPEG",
            prompt_used="Test prompt for dog image generation",
            dog_description="A friendly golden retriever in a park",
            status="completed",
            processing_time=2.5,
            logo_applied=False
        )
        
        if test_record:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "✅ Supabase connection successful! Test record created.",
                    "data": {
                        "test_record_id": test_record.get('id'),
                        "created_at": test_record.get('created_at')
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "❌ Failed to create test record in Supabase",
                    "data": None
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"❌ Supabase connection test failed: {str(e)}",
                "data": None
            }
        )


@router.get(
    "/generations",
    summary="Get generation history",
    description="Get a list of recent image generations with their status and metadata"
)
async def get_generations(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of image generations.
    
    Args:
        page: Page number (1-indexed)
        limit: Number of records per page (max 100)
        status: Filter by status (pending, processing, completed, failed)
        db: Database session
    
    Returns:
        List of generation records with metadata
    """
    if not db:
        raise HTTPException(
            status_code=503,
            detail={"error": "DatabaseNotAvailable", "message": "Database features are disabled"}
        )
    
    # Validate parameters
    if limit > 100:
        limit = 100
    if page < 1:
        page = 1
    
    try:
        # Build base query
        query = select(ImageGeneration)
        
        if status:
            query = query.where(ImageGeneration.status == status)
        
        # Get total count
        count_query = select(func.count(ImageGeneration.id))
        if status:
            count_query = count_query.where(ImageGeneration.status == status)
        
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Get paginated results
        offset = (page - 1) * limit
        paginated_query = query.order_by(desc(ImageGeneration.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(paginated_query)
        generations = result.scalars().all()
        
        # Convert to dict format
        generation_data = [gen.to_dict() for gen in generations]
        
        return {
            "success": True,
            "data": {
                "generations": generation_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit if total_count > 0 else 0
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to retrieve generations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to retrieve generation history",
                "details": str(e)
            }
        )


@router.get(
    "/generations/{generation_id}",
    summary="Get specific generation details",
    description="Get detailed information about a specific image generation"
)
async def get_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific generation.
    
    Args:
        generation_id: UUID of the generation record
        db: Database session
    
    Returns:
        Detailed generation information
    """
    if not db:
        raise HTTPException(
            status_code=503,
            detail={"error": "DatabaseNotAvailable", "message": "Database features are disabled"}
        )
    
    try:
        generation = await db.get(ImageGeneration, generation_id)
        
        if not generation:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "GenerationNotFound",
                    "message": f"Generation with ID {generation_id} not found"
                }
            )
        
        return {
            "success": True,
            "data": generation.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve generation", generation_id=generation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to retrieve generation details",
                "details": str(e)
            }
        )


@router.get(
    "/statistics",
    summary="Get generation statistics",
    description="Get aggregated statistics about image generations"
)
async def get_statistics(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated statistics for image generations.
    
    Args:
        days: Number of days to include in statistics (default: 7)
        db: Database session
    
    Returns:
        Aggregated statistics
    """
    if not db:
        raise HTTPException(
            status_code=503,
            detail={"error": "DatabaseNotAvailable", "message": "Database features are disabled"}
        )
    
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get statistics using async SQLAlchemy
        stats_query = select(
            func.count(ImageGeneration.id).label('total'),
            func.sum(
                func.case((ImageGeneration.status == 'completed', 1), else_=0)
            ).label('completed'),
            func.sum(
                func.case((ImageGeneration.status == 'failed', 1), else_=0)
            ).label('failed'),
            func.avg(ImageGeneration.processing_time).label('avg_processing_time'),
            func.sum(ImageGeneration.generated_image_size).label('total_storage_used')
        ).where(
            ImageGeneration.created_at >= start_date,
            ImageGeneration.created_at <= end_date
        )
        
        result = await db.execute(stats_query)
        stats = result.first()
        
        # Calculate success rate
        success_rate = 0
        if stats.total and stats.total > 0:
            success_rate = (stats.completed / stats.total) * 100
        
        return {
            "success": True,
            "data": {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "totals": {
                    "total_generations": stats.total or 0,
                    "successful_generations": stats.completed or 0,
                    "failed_generations": stats.failed or 0,
                    "success_rate_percent": round(success_rate, 2)
                },
                "performance": {
                    "average_processing_time": round(stats.avg_processing_time or 0, 2),
                    "total_storage_used_bytes": stats.total_storage_used or 0
                }
            }
        }
        
    except Exception as e:
        logger.error("Failed to retrieve statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DatabaseError",
                "message": "Failed to retrieve statistics",
                "details": str(e)
            }
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check the health status of the API and Stability.ai services"
)
async def health_check():
    """
    Perform a health check on the API and external services.
    
    Returns the current status of:
    - API server
    - Stability.ai connection
    - Database connection (if enabled)
    """
    try:
        # Check Stability.ai service health
        stability_healthy = stability_generator.health_check()
        
        # Check database health
        db_status = await check_database_health()
        
        # Determine overall status
        if stability_healthy and db_status["status"] in ["healthy", "disabled"]:
            status = "healthy"
            message = "All services are operational"
            status_code = 200
        elif stability_healthy and db_status["status"] == "error":
            status = "degraded"
            message = "API is running but database is unavailable"
            status_code = 200
        elif not stability_healthy and db_status["status"] in ["healthy", "disabled"]:
            status = "degraded"
            message = "Database is healthy but Stability.ai service is not responding"
            status_code = 503
        else:
            status = "unhealthy"
            message = "Multiple services are experiencing issues"
            status_code = 503
            
        response = HealthResponse(
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            services={
                "stability_ai": "healthy" if stability_healthy else "unhealthy",
                "database": db_status["status"]
            }
        )
        
        logger.info(
            "Health check completed", 
            status=status, 
            stability_healthy=stability_healthy,
            database_status=db_status["status"]
        )
        
        return JSONResponse(
            status_code=status_code,
            content=response.dict()
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Health check failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": str(e)
            }
        ) 


@router.post(
    "/share",
    summary="Prepare content for social sharing",
    description="Generate shareable content for Instagram and Facebook with pre-filled hashtags and mentions"
)
async def prepare_share_content(
    generation_id: str,
    platform: str = "instagram",  # instagram, facebook
    db: AsyncSession = Depends(get_db)
):
    """
    Prepare content for social media sharing.
    
    Args:
        generation_id: ID of the generated image
        platform: Social media platform (instagram, facebook)
        db: Database session
    
    Returns:
        Shareable content with image URL and pre-filled text
    """
    if not db:
        raise HTTPException(
            status_code=503,
            detail={"error": "DatabaseNotAvailable", "message": "Database features are disabled"}
        )
    
    try:
        # Get generation record
        generation = await db.get(ImageGeneration, generation_id)
        
        if not generation:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "GenerationNotFound",
                    "message": f"Generation with ID {generation_id} not found"
                }
            )
        
        # Generate share content based on platform
        if platform.lower() == "instagram":
            share_text = "Look at my furry friend rocking some eco-friendly GNB gear! 🐕✨ #GoodNaturedPup #SustainablePets @goodnaturedbrand"
            hashtags = ["#GoodNaturedPup", "#SustainablePets", "#EcoFriendlyPets", "#GNBStyle"]
        elif platform.lower() == "facebook":
            share_text = "My dog is looking adorable in Good Natured Brand apparel! Check out this AI-generated transformation. #GoodNaturedPup @goodnaturedbrand"
            hashtags = ["#GoodNaturedPup", "#PetFashion", "#SustainablePets"]
        else:
            share_text = "Check out my dog wearing GNB apparel! #GoodNaturedPup @goodnaturedbrand"
            hashtags = ["#GoodNaturedPup"]
        
        return {
            "success": True,
            "data": {
                "generation_id": generation_id,
                "platform": platform,
                "share_text": share_text,
                "hashtags": hashtags,
                "mentions": ["@goodnaturedbrand"],
                "image_url": generation.generated_image_url or f"/api/v1/download/{generation_id}",
                "share_url": f"{settings.app_host}:{settings.app_port}/share/{generation_id}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to prepare share content", generation_id=generation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SharePreparationError",
                "message": "Failed to prepare sharing content",
                "details": str(e)
            }
        )


@router.get(
    "/download/{generation_id}",
    summary="Download generated image",
    description="Download the generated image file directly"
)
async def download_image(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download generated image file.
    
    Args:
        generation_id: ID of the generated image
        db: Database session
    
    Returns:
        Image file as downloadable response
    """
    if not db:
        raise HTTPException(
            status_code=503,
            detail={"error": "DatabaseNotAvailable", "message": "Database features are disabled"}
        )
    
    try:
        generation = await db.get(ImageGeneration, generation_id)
        
        if not generation:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "GenerationNotFound",
                    "message": f"Generation with ID {generation_id} not found"
                }
            )
        
        # For now, return a redirect to the stored image URL
        # In production, you might want to serve the file directly from storage
        if generation.generated_image_url:
            return {"download_url": generation.generated_image_url}
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "ImageNotAvailable",
                    "message": "Generated image file not available for download"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to prepare download", generation_id=generation_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DownloadError",
                "message": "Failed to prepare image download",
                "details": str(e)
            }
        )


@router.post(
    "/validate-image",
    summary="Pre-validate image before upload",
    description="Validate image file without processing to provide immediate feedback"
)
async def validate_image_only(
    image: UploadFile = File(
        ...,
        description="Image file to validate",
        media_type="multipart/form-data"
    )
):
    """
    Validate image file without full processing.
    
    This endpoint allows frontend to validate images before starting
    the full generation process, providing better UX.
    """
    try:
        # Quick validation without processing
        content = await image.read()
        
        # Check file size
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > settings.max_image_size_mb:
            return {
                "valid": False,
                "error": "FileSizeExceeded",
                "message": f"File size {file_size_mb:.2f}MB exceeds limit of {settings.max_image_size_mb}MB",
                "file_size_mb": round(file_size_mb, 2)
            }
        
        # Check file type
        if image.content_type not in settings.allowed_image_types:
            return {
                "valid": False,
                "error": "InvalidFileType",
                "message": f"File type {image.content_type} not allowed",
                "allowed_types": settings.allowed_image_types
            }
        
        # Quick image validation
        try:
            from PIL import Image as PILImage
            img = PILImage.open(io.BytesIO(content))
            img.verify()
            
            return {
                "valid": True,
                "message": "Image validation successful",
                "file_size_mb": round(file_size_mb, 2),
                "dimensions": img.size,
                "format": img.format
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": "InvalidImage",
                "message": f"Invalid image file: {str(e)}"
            }
        
    except Exception as e:
        logger.error("Image validation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ValidationError",
                "message": "Failed to validate image",
                "details": str(e)
            }
        )


@router.get(
    "/gallery",
    summary="Get recent successful generations gallery",
    description="Get a gallery of recent successful generations for showcase"
)
async def get_gallery(
    limit: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent successful generations for gallery display.
    
    Args:
        limit: Number of images to return (max 24)
        db: Database session
    
    Returns:
        List of recent successful generations with image URLs
    """
    if not db:
        return {
            "success": True,
            "data": {
                "images": [],
                "message": "Gallery requires database features"
            }
        }
    
    # Limit the number of results
    if limit > 24:
        limit = 24
    
    try:
        # Get recent successful generations
        query = select(ImageGeneration).where(
            ImageGeneration.status == "completed",
            ImageGeneration.logo_applied == True
        ).order_by(desc(ImageGeneration.completed_at)).limit(limit)
        
        result = await db.execute(query)
        generations = result.scalars().all()
        
        gallery_images = []
        for gen in generations:
            gallery_images.append({
                "id": str(gen.id),
                "image_url": gen.generated_image_url or f"/api/v1/download/{gen.id}",
                "created_at": gen.created_at.isoformat() if gen.created_at else None,
                "processing_time": gen.processing_time
            })
        
        return {
            "success": True,
            "data": {
                "images": gallery_images,
                "count": len(gallery_images)
            }
        }
        
    except Exception as e:
        logger.error("Failed to retrieve gallery", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "GalleryError",
                "message": "Failed to retrieve gallery images",
                "details": str(e)
            }
        ) 
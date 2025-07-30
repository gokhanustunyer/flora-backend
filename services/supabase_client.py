"""Supabase client service for direct database operations."""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from config.settings import settings
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SupabaseClientService:
    """Service for direct Supabase database operations."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client with environment variables."""
        try:
            # Try to get from settings first, then fallback to direct environment variables
            supabase_url = settings.supabase_url or os.getenv("SUPABASE_URL")
            # Use service role key for admin operations, fallback to anon key, then SUPABASE_KEY
            supabase_key = (settings.supabase_service_role_key or 
                          settings.supabase_anon_key or 
                          os.getenv("SUPABASE_KEY"))
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase URL or API key not configured, Supabase client will be disabled")
                logger.info("Make sure SUPABASE_URL and SUPABASE_KEY are set in your .env file")
                return
            
            # Create client with minimal configuration
            self.client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
            # Test connection
            if self._test_connection():
                logger.info("✅ Supabase connection test successful")
            else:
                logger.warning("⚠️ Supabase connection test failed")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.client = None
    
    def _test_connection(self) -> bool:
        """Test Supabase connection."""
        if not self.client:
            return False
            
        try:
            # Try to query image_generations table
            response = self.client.table('image_generations').select("*").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Supabase client is available."""
        return self.client is not None
    
    async def insert_generation_record(self, 
                                     original_filename: str,
                                     original_url: Optional[str] = None,
                                     original_size: Optional[int] = None,
                                     original_format: Optional[str] = None,
                                     generated_url: Optional[str] = None,
                                     generated_size: Optional[int] = None,
                                     prompt_used: Optional[str] = None,
                                     dog_description: Optional[str] = None,
                                     processing_time: Optional[float] = None,
                                     status: str = "completed",
                                     logo_applied: bool = False,
                                     error_message: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Insert a new generation record into Supabase."""
        
        if not self.client:
            logger.warning("Supabase client not available, skipping record insertion")
            return None
        
        try:
            record_data = {
                "original_image_filename": original_filename,
                "original_image_url": original_url,
                "original_image_size": original_size,
                "original_image_format": original_format,
                "generated_image_url": generated_url,
                "generated_image_size": generated_size,
                "prompt_used": prompt_used,
                "dog_description": dog_description,
                "status": status,
                "processing_time": processing_time,
                "logo_applied": logo_applied,
                "error_message": error_message,
                "created_at": datetime.now().isoformat()
            }
            
            # Remove None values
            record_data = {k: v for k, v in record_data.items() if v is not None}
            
            response = self.client.table('image_generations').insert(record_data).execute()
            
            if response.data:
                inserted_record = response.data[0]
                logger.info(f"✅ Supabase record inserted successfully: ID {inserted_record['id']}")
                return inserted_record
            else:
                logger.error("❌ Failed to insert Supabase record: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error inserting Supabase record: {e}")
            return None
    
    async def update_generation_status(self, record_id: str, status: str, 
                                     error_message: Optional[str] = None,
                                     processing_time: Optional[float] = None) -> bool:
        """Update generation record status."""
        
        if not self.client:
            return False
        
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if error_message:
                update_data["error_message"] = error_message
            if processing_time is not None:
                update_data["processing_time"] = processing_time
            
            response = self.client.table('image_generations').update(update_data).eq('id', record_id).execute()
            
            if response.data:
                logger.info(f"✅ Supabase record updated: ID {record_id}")
                return True
            else:
                logger.error(f"❌ Failed to update Supabase record: ID {record_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating Supabase record: {e}")
            return False
    
    async def get_generation_statistics(self, limit: int = 5) -> Optional[list]:
        """Get generation statistics from daily summary view."""
        
        if not self.client:
            return None
        
        try:
            response = self.client.table('daily_generation_summary').select("*").limit(limit).execute()
            
            if response.data:
                logger.info(f"✅ Retrieved {len(response.data)} statistics records")
                return response.data
            else:
                logger.info("📊 No statistics data available")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve statistics (might not be available yet): {e}")
            return None


# Global instance
supabase_service = SupabaseClientService() 
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env file)."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =================================================================
    # STABILITY.AI CONFIGURATION (Required)
    # =================================================================
    stability_ai_api_key: str = Field(..., description="Stability.ai API key")

    # =================================================================
    # SUPABASE DATABASE CONFIGURATION (Optional - for request tracking)
    # =================================================================
    supabase_url: Optional[str] = Field(
        default=None,
        description="Supabase project URL (e.g., https://your-project.supabase.co)"
    )
    supabase_anon_key: Optional[str] = Field(
        default=None,
        description="Supabase anonymous/public API key"
    )
    supabase_service_role_key: Optional[str] = Field(
        default=None,
        description="Supabase service role key (for admin operations)"
    )
    database_url: Optional[str] = Field(
        default=None,
        description="Direct PostgreSQL connection URL (if using Supabase's direct DB access)"
    )
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Database max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL queries (dev only)")

    # =================================================================
    # SUPABASE STORAGE CONFIGURATION (Optional - alternative to Azure Storage)
    # =================================================================
    supabase_storage_bucket: str = Field(
        default="gnb-dog-images",
        description="Supabase Storage bucket name"
    )
    use_supabase_storage: bool = Field(
        default=False,
        description="Use Supabase Storage instead of Azure Storage"
    )

    # =================================================================
    # AZURE STORAGE CONFIGURATION (Optional - for image storage)
    # =================================================================
    azure_storage_account_name: Optional[str] = Field(
        default=None, 
        description="Azure Storage account name"
    )
    azure_storage_account_key: Optional[str] = Field(
        default=None, 
        description="Azure Storage account key"
    )
    azure_storage_container_name: str = Field(
        default="gnb-dog-images", 
        description="Azure Blob container name"
    )
    
    # =================================================================
    # APPLICATION CONFIGURATION
    # =================================================================
    # Server settings
    app_host: str = Field(default="0.0.0.0", description="FastAPI host")
    app_port: int = Field(default=3001, description="FastAPI port")
    
    # Image processing settings
    max_image_size_mb: int = Field(default=10, description="Maximum image size in MB")
    allowed_image_types: List[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Allowed image MIME types"
    )
    gnb_logo_path: str = Field(
        default="static/gnb_logo.png",
        description="Path to GNB logo image"
    )
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS allowed origins"
    )
    
    # =================================================================
    # LOGGING CONFIGURATION
    # =================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    
    # =================================================================
    # PERFORMANCE TUNING (Optional)
    # =================================================================
    ai_generation_timeout: int = Field(
        default=30, 
        description="AI generation timeout in seconds"
    )
    max_image_dimension: int = Field(
        default=1024, 
        description="Maximum image dimension for processing"
    )
    logo_size_percentage: int = Field(
        default=10, 
        description="Logo size as percentage of image width"
    )
    logo_position: str = Field(
        default="bottom-right", 
        description="Logo position (bottom-right, bottom-left, top-right, top-left)"
    )
    sas_url_expiry_hours: int = Field(
        default=24, 
        description="SAS URL expiry time in hours"
    )
    
    # =================================================================
    # DEBUG/DEVELOPMENT SETTINGS
    # =================================================================
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    enable_api_docs: bool = Field(default=True, description="Enable API documentation")
    reload_on_change: bool = Field(default=True, description="Reload on code changes (dev only)")
    
    @field_validator('allowed_image_types', mode='before')
    @classmethod
    def parse_allowed_image_types(cls, v):
        """Parse allowed image types from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(',')
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(',')
        return v

    # =================================================================
    # COMPUTED PROPERTIES
    # =================================================================
    @property
    def supabase_enabled(self) -> bool:
        """Check if Supabase features are enabled."""
        return self.supabase_url is not None and self.supabase_anon_key is not None

    @property
    def database_enabled(self) -> bool:
        """Check if database features are enabled (either Supabase or direct connection)."""
        # Always enable database - will fallback to SQLite for local development
        return True

    @property
    def storage_enabled(self) -> bool:
        """Check if storage features are enabled (Supabase or Azure)."""
        return self.use_supabase_storage and self.supabase_enabled or (
            self.azure_storage_account_name is not None and
            self.azure_storage_account_key is not None
        )

    @property
    def effective_database_url(self) -> Optional[str]:
        """Get the effective database URL (prioritize direct connection over Supabase)."""
        if self.database_url:
            return self.database_url
        elif self.supabase_enabled:
            # Convert Supabase URL to direct PostgreSQL connection
            # Supabase URL format: https://xxx.supabase.co
            # Direct connection: postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres
            project_id = self.supabase_url.split("//")[1].split(".")[0]
            return f"postgresql+asyncpg://postgres:[YOUR_DB_PASSWORD]@db.{project_id}.supabase.co:6543/postgres"
        return None

    def get_feature_status(self) -> dict:
        """Get status of all features for health checks."""
        return {
            "stability_ai": True,  # Always available
            "supabase": self.supabase_enabled,
            "database": self.database_enabled,
            "storage": self.storage_enabled,
            "storage_type": "supabase" if self.use_supabase_storage else "azure"
        }


# Global settings instance
settings = Settings() 
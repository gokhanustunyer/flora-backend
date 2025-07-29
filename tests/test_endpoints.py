"""Tests for API endpoints."""

import pytest
import io
from httpx import AsyncClient


class TestGenerateEndpoint:
    """Tests for the /api/v1/generate endpoint."""
    
    @pytest.mark.asyncio
    async def test_generate_success(
        self, 
        client: AsyncClient, 
        sample_dog_image: bytes, 
        mock_stability_success,
        override_settings
    ):
        """Test successful image generation."""
        files = {"image": ("test_dog.jpg", io.BytesIO(sample_dog_image), "image/jpeg")}
        
        response = await client.post("/api/v1/generate", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "base64Image" in data["data"]
        assert data["data"]["base64Image"].startswith("data:image/png;base64,")
        assert "message" in data["data"]
        assert "successfully" in data["data"]["message"]
    
    @pytest.mark.asyncio
    async def test_generate_file_too_large(
        self, 
        client: AsyncClient, 
        sample_large_image: bytes
    ):
        """Test file size validation."""
        files = {"image": ("large_dog.jpg", io.BytesIO(sample_large_image), "image/jpeg")}
        
        response = await client.post("/api/v1/generate", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "FileSizeExceeded" in data["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_generate_invalid_file_type(
        self, 
        client: AsyncClient, 
        invalid_file: bytes
    ):
        """Test invalid file type."""
        files = {"image": ("test.txt", io.BytesIO(invalid_file), "text/plain")}
        
        response = await client.post("/api/v1/generate", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "InvalidFileType" in data["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_generate_no_file(self, client: AsyncClient):
        """Test missing file."""
        response = await client.post("/api/v1/generate")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_generate_ai_failure(
        self, 
        client: AsyncClient, 
        sample_dog_image: bytes, 
        mock_stability_failure,
        override_settings
    ):
        """Test AI generation failure."""
        files = {"image": ("test_dog.jpg", io.BytesIO(sample_dog_image), "image/jpeg")}
        
        response = await client.post("/api/v1/generate", files=files)
        
        assert response.status_code == 500
        data = response.json()
        assert "AIGenerationFailed" in data["detail"]["error"]


class TestHealthEndpoint:
    """Tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(
        self, 
        client: AsyncClient, 
        mock_stability_success
    ):
        """Test successful health check."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["stability_ai"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(
        self, 
        client: AsyncClient, 
        mock_stability_failure
    ):
        """Test degraded health check."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 503
        data = response.json()
        
        assert data["status"] in ["degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_root_health(self, client: AsyncClient):
        """Test root health endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "GNB Dog Image Generation API"


class TestDatabaseEndpoints:
    """Tests for database-related endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_generations_empty(self, client: AsyncClient):
        """Test getting generations when database is empty."""
        response = await client.get("/api/v1/generations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["generations"] == []
        assert data["data"]["pagination"]["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_generations_pagination(self, client: AsyncClient):
        """Test generations pagination."""
        response = await client.get("/api/v1/generations?page=1&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "pagination" in data["data"]
        assert data["data"]["pagination"]["page"] == 1
        assert data["data"]["pagination"]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_generation_not_found(self, client: AsyncClient):
        """Test getting non-existent generation."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.get(f"/api/v1/generations/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "GenerationNotFound" in data["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, client: AsyncClient):
        """Test getting statistics when database is empty."""
        response = await client.get("/api/v1/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["totals"]["total_generations"] == 0


class TestRootEndpoints:
    """Tests for root endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "GNB Dog Image Generation API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "features" in data


class TestCORSHeaders:
    """Tests for CORS configuration."""
    
    @pytest.mark.asyncio
    async def test_cors_options(self, client: AsyncClient):
        """Test CORS preflight request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = await client.options("/api/v1/generate", headers=headers)
        
        # FastAPI automatically handles CORS preflight
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_404_error(self, client: AsyncClient):
        """Test 404 error handling."""
        response = await client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """Test method not allowed."""
        response = await client.patch("/api/v1/generate")
        
        assert response.status_code == 405
"""Integration tests for FastAPI app"""
import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app import app
from tools.manager import ToolManager, ToolType
from services.base import QueryResult


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "docs" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_tools_endpoint(self, client):
        """Test tools list endpoint"""
        response = client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_query_endpoint_empty_query(self, client):
        """Test query endpoint with empty query"""
        response = client.post(
            "/query",
            json={"query": ""}
        )
        # Should fail with empty query or 503 if no tools
        assert response.status_code in [400, 503]
    
    def test_parse_endpoint(self, client):
        """Test parse endpoint"""
        response = client.post(
            "/parse",
            json={"query": "Show my work items"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "primary_entity" in data
    
    def test_parse_endpoint_with_complex_query(self, client):
        """Test parse endpoint with complex query"""
        response = client.post(
            "/parse",
            json={"query": "Find all open bugs in last 2 weeks sorted by priority"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] in ["search", "list", "count", "analyze"]


class TestQueryValidation:
    """Test query validation"""
    
    def test_query_without_query_field(self, client):
        """Test query request without query field"""
        response = client.post("/query", json={})
        # Should fail validation
        assert response.status_code in [422, 400]
    
    def test_query_with_extra_fields(self, client):
        """Test query request with extra fields (should be ignored)"""
        response = client.post(
            "/query",
            json={
                "query": "test",
                "extra_field": "should be ignored"
            }
        )
        # Should still process query field
        assert response.status_code in [400, 503]  # Either no query or no tools
    
    def test_tool_type_field_optional(self, client):
        """Test that tool_type field is optional"""
        response = client.post(
            "/query",
            json={"query": "test"}
        )
        # Should process even without tool_type
        assert response.status_code in [400, 503]


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for unknown endpoint"""
        response = client.get("/unknown-endpoint")
        assert response.status_code == 404
    
    def test_405_for_wrong_method(self, client):
        """Test 405 for wrong HTTP method"""
        response = client.get("/query")  # /query expects POST
        assert response.status_code == 405


class TestHealthCheckFields:
    """Test health check response fields"""
    
    def test_health_includes_status(self, client):
        """Test health response includes status"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
    
    def test_health_includes_available_tools(self, client):
        """Test health response includes available tools"""
        response = client.get("/health")
        data = response.json()
        assert "available_tools" in data
        assert isinstance(data["available_tools"], list)


class TestParseEndpointResponses:
    """Test parse endpoint response structure"""
    
    def test_parse_response_structure(self, client):
        """Test parse response has correct structure"""
        response = client.post(
            "/parse",
            json={"query": "Show errors"}
        )
        data = response.json()
        
        # Should have main fields
        assert "intent" in data
        assert "primary_entity" in data
        assert "keywords" in data
        assert "confidence" in data
    
    def test_parse_response_has_confidence(self, client):
        """Test parse response includes confidence score"""
        response = client.post(
            "/parse",
            json={"query": "Show my open work items"}
        )
        data = response.json()
        
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert 0 <= data["confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

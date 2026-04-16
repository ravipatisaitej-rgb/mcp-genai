"""Tests for base service classes"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.base import APIResponse, RateLimitInfo, BaseTool, QueryResult
from datetime import datetime, timedelta
import requests


class TestAPIResponse:
    """Test APIResponse class"""
    
    def test_success_response(self):
        """Test successful response"""
        resp = APIResponse(status_code=200, data={"key": "value"})
        assert resp.is_success is True
        assert resp.is_client_error is False
        assert resp.is_server_error is False
    
    def test_client_error(self):
        """Test client error response"""
        resp = APIResponse(status_code=400, error="Bad request")
        assert resp.is_success is False
        assert resp.is_client_error is True
        assert resp.is_server_error is False
    
    def test_server_error(self):
        """Test server error response"""
        resp = APIResponse(status_code=500, error="Internal error")
        assert resp.is_success is False
        assert resp.is_client_error is False
        assert resp.is_server_error is True


class TestRateLimitInfo:
    """Test RateLimitInfo class"""
    
    def test_rate_limit_info_creation(self):
        """Test creating rate limit info"""
        reset_time = datetime.now() + timedelta(seconds=60)
        info = RateLimitInfo(limit=5000, remaining=4999, reset_at=reset_time)
        assert info.limit == 5000
        assert info.remaining == 4999
    
    def test_should_backoff_false(self):
        """Test backoff check when not needed"""
        info = RateLimitInfo(limit=5000, remaining=100)
        assert info.should_backoff() is False
    
    def test_should_backoff_true(self):
        """Test backoff check when needed"""
        reset_time = datetime.now() + timedelta(seconds=60)
        info = RateLimitInfo(limit=5000, remaining=3, reset_at=reset_time)
        assert info.should_backoff() is True
    
    def test_default_values(self):
        """Test default values"""
        info = RateLimitInfo()
        assert info.limit == 0
        assert info.remaining == 0
        assert info.reset_at is None


class MockAPIClient(BaseTool):
    """Mock API client for testing"""
    
    def validate(self):
        return True
    
    def execute(self, query):
        return QueryResult(success=True, data={"test": "data"})
    
    def _get_auth_headers(self):
        return {"Authorization": "Bearer test"}
    
    def _get_base_url(self):
        return "https://api.example.com"


class TestQueryResult:
    """Test QueryResult class"""
    
    def test_query_result_success(self):
        """Test successful query result"""
        result = QueryResult(
            success=True,
            data={"key": "value"},
            metadata={"tool": "test"}
        )
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_query_result_error(self):
        """Test failed query result"""
        result = QueryResult(
            success=False,
            error="Something went wrong"
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None
    
    def test_query_result_to_dict(self):
        """Test converting query result to dict"""
        result = QueryResult(
            success=True,
            data={"key": "value"},
            metadata={"tool": "test"}
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["metadata"] == {"tool": "test"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

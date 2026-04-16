"""Tests for exception classes"""
import pytest
from utils.exceptions import (
    MCPToolException,
    ConfigurationError,
    APIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    QueryParseError,
    DataAggregationError,
    TimeoutError,
)


class TestExceptions:
    """Test custom exception classes"""
    
    def test_mcp_tool_exception(self):
        """Test base exception"""
        with pytest.raises(MCPToolException):
            raise MCPToolException("Test error")
    
    def test_configuration_error(self):
        """Test configuration error"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Missing config")
    
    def test_api_error_basic(self):
        """Test API error with basic message"""
        error = APIError("API failed")
        assert error.message == "API failed"
        assert error.status_code is None
    
    def test_api_error_with_status(self):
        """Test API error with status code"""
        error = APIError("API failed", status_code=500)
        assert error.status_code == 500
    
    def test_api_error_with_response(self):
        """Test API error with response data"""
        response_data = {"error": "Internal server error"}
        error = APIError("API failed", status_code=500, response=response_data)
        assert error.response == response_data
    
    def test_authentication_error(self):
        """Test authentication error"""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Invalid token", status_code=401)
    
    def test_rate_limit_error(self):
        """Test rate limit error"""
        with pytest.raises(RateLimitError):
            raise RateLimitError("Too many requests", status_code=429)
    
    def test_not_found_error(self):
        """Test not found error"""
        with pytest.raises(NotFoundError):
            raise NotFoundError("Resource not found", status_code=404)
    
    def test_query_parse_error(self):
        """Test query parse error"""
        with pytest.raises(QueryParseError):
            raise QueryParseError("Invalid query format")
    
    def test_data_aggregation_error(self):
        """Test data aggregation error"""
        with pytest.raises(DataAggregationError):
            raise DataAggregationError("Failed to aggregate data")
    
    def test_timeout_error(self):
        """Test timeout error"""
        with pytest.raises(TimeoutError):
            raise TimeoutError("Request timed out")
    
    def test_exception_inheritance(self):
        """Test exception hierarchy"""
        # Authentication error should be subclass of APIError
        error = AuthenticationError("test", status_code=401)
        assert isinstance(error, APIError)
        assert isinstance(error, MCPToolException)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

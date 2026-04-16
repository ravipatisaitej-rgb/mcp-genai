"""
Custom exceptions for MCP tools.
Provides specific error types for better error handling.
"""


class MCPToolException(Exception):
    """Base exception for all MCP tools"""
    pass


class ConfigurationError(MCPToolException):
    """Raised when tool configuration is missing or invalid"""
    pass


class APIError(MCPToolException):
    """Raised when API call fails"""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class AuthenticationError(APIError):
    """Raised when authentication fails"""
    pass


class RateLimitError(APIError):
    """Raised when rate limit is exceeded"""
    pass


class NotFoundError(APIError):
    """Raised when resource is not found"""
    pass


class QueryParseError(MCPToolException):
    """Raised when query parsing fails"""
    pass


class DataAggregationError(MCPToolException):
    """Raised when data aggregation fails"""
    pass


class TimeoutError(MCPToolException):
    """Raised when operation times out"""
    pass

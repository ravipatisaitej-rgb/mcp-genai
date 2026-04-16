"""Pytest configuration and shared fixtures"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
import json

from tools.manager import ToolManager, ToolType
from tools.base import BaseTool
from services.base import APIResponse, QueryResult, RateLimitInfo
from utils.query_parser import QueryParser


# ============================================================================
# Mock Tools for Testing
# ============================================================================

class MockConfluenceTool(BaseTool):
    """Mock Confluence tool for testing"""
    
    def __init__(self):
        self.name = "confluence"
        self.description = "Mock Confluence search"
        self.call_count = 0
    
    def execute(self, params: dict) -> QueryResult:
        """Execute mock search"""
        self.call_count += 1
        
        if not params.get("query"):
            return QueryResult(
                success=False,
                error="Query required",
                error_type="ValueError"
            )
        
        return QueryResult(
            success=True,
            data={
                "results": [
                    {"title": "Test Page", "id": "123", "space": "TEST"}
                ],
                "total": 1
            },
            metadata={
                "tool_used": "confluence",
                "query": params.get("query"),
                "space": params.get("space", "all")
            }
        )


class MockAzureBoardsTool(BaseTool):
    """Mock Azure Boards tool for testing"""
    
    def __init__(self):
        self.name = "azure_boards"
        self.description = "Mock Azure DevOps"
        self.call_count = 0
    
    def execute(self, params: dict) -> QueryResult:
        """Execute mock work item query"""
        self.call_count += 1
        
        if not params.get("query"):
            return QueryResult(
                success=False,
                error="Query required",
                error_type="ValueError"
            )
        
        return QueryResult(
            success=True,
            data={
                "workItems": [
                    {"id": 1, "title": "Task 1", "state": "active"}
                ],
                "total": 1
            },
            metadata={
                "tool_used": "azure_boards",
                "query": params.get("query")
            }
        )


class MockCloudWatchTool(BaseTool):
    """Mock CloudWatch tool for testing"""
    
    def __init__(self):
        self.name = "cloudwatch"
        self.description = "Mock CloudWatch logs"
        self.call_count = 0
    
    def execute(self, params: dict) -> QueryResult:
        """Execute mock log query"""
        self.call_count += 1
        
        if not params.get("query"):
            return QueryResult(
                success=False,
                error="Query required",
                error_type="ValueError"
            )
        
        return QueryResult(
            success=True,
            data={
                "events": [
                    {"message": "ERROR: Something failed", "timestamp": 1000}
                ],
                "total": 1
            },
            metadata={
                "tool_used": "cloudwatch",
                "query": params.get("query")
            }
        )


class MockGitHubTool(BaseTool):
    """Mock GitHub Actions tool for testing"""
    
    def __init__(self):
        self.name = "github_actions"
        self.description = "Mock GitHub Actions"
        self.call_count = 0
    
    def execute(self, params: dict) -> QueryResult:
        """Execute mock action query"""
        self.call_count += 1
        
        if not params.get("query"):
            return QueryResult(
                success=False,
                error="Query required",
                error_type="ValueError"
            )
        
        return QueryResult(
            success=True,
            data={
                "runs": [
                    {"id": 1, "name": "CI", "conclusion": "failure"}
                ],
                "total": 1
            },
            metadata={
                "tool_used": "github_actions",
                "query": params.get("query")
            }
        )


class MockSnowflakeTool(BaseTool):
    """Mock Snowflake tool for testing"""
    
    def __init__(self):
        self.name = "snowflake"
        self.description = "Mock Snowflake queries"
        self.call_count = 0
    
    def execute(self, params: dict) -> QueryResult:
        """Execute mock data query"""
        self.call_count += 1
        
        if not params.get("query"):
            return QueryResult(
                success=False,
                error="Query required",
                error_type="ValueError"
            )
        
        return QueryResult(
            success=True,
            data={
                "rows": [{"id": 1, "data": "sample"}],
                "total": 1
            },
            metadata={
                "tool_used": "snowflake",
                "query": params.get("query")
            }
        )


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def query_parser():
    """Provide QueryParser instance"""
    return QueryParser()


@pytest.fixture
def tool_manager():
    """Provide ToolManager with mock tools registered"""
    manager = ToolManager()
    
    # Register all mock tools
    manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
    manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
    manager.register_tool(ToolType.CLOUDWATCH, MockCloudWatchTool())
    manager.register_tool(ToolType.GITHUB_ACTIONS, MockGitHubTool())
    manager.register_tool(ToolType.SNOWFLAKE, MockSnowflakeTool())
    
    return manager


@pytest.fixture
def mock_api_response():
    """Provide mock API response"""
    return APIResponse(
        status_code=200,
        headers={"X-RateLimit-Remaining": "100"},
        body={"data": "test"}
    )


@pytest.fixture
def mock_rate_limit_info():
    """Provide mock rate limit info"""
    return RateLimitInfo(
        limit=100,
        remaining=50,
        reset_at=datetime.now() + timedelta(hours=1)
    )


@pytest.fixture
def sample_queries():
    """Provide sample queries for testing"""
    return {
        "simple_search": "find documentation",
        "complex_query": "Find all open bugs assigned to john in last 2 weeks sorted by priority",
        "list_query": "list my work items",
        "count_query": "how many errors in last hour",
        "analyze_query": "analyze build failures",
        "with_filters": "find pages status:published space:WIKI",
        "time_range": "errors in last 3 days",
        "multi_filter": "work items state:active assignee:john priority:high"
    }


@pytest.fixture
def mock_http_session():
    """Provide mock HTTP session"""
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    session.headers = {}
    return session


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "mock_api: mark test as using mocked API"
    )


# ============================================================================
# Test Utilities
# ============================================================================

def create_mock_tool(name: str, execute_fn=None) -> BaseTool:
    """Create a mock tool with optional execute function"""
    tool = Mock(spec=BaseTool)
    tool.name = name
    tool.description = f"Mock {name} tool"
    
    if execute_fn:
        tool.execute = execute_fn
    else:
        tool.execute = Mock(return_value=QueryResult(
            success=True,
            data={"mock": "data"}
        ))
    
    return tool


def assert_query_result_valid(result: QueryResult):
    """Assert QueryResult has valid structure"""
    assert isinstance(result, QueryResult)
    assert hasattr(result, 'success')
    assert hasattr(result, 'data')
    assert isinstance(result.success, bool)
    
    if result.success:
        assert result.data is not None
        assert result.error is None
    else:
        assert result.error is not None


def assert_parsed_query_valid(parsed):
    """Assert ParsedQuery has valid structure"""
    assert hasattr(parsed, 'intent')
    assert hasattr(parsed, 'primary_entity')
    assert hasattr(parsed, 'keywords')
    assert hasattr(parsed, 'confidence')
    
    assert parsed.intent in [
        "search", "list", "count", "analyze", "execute", "unknown"
    ]
    assert 0 <= parsed.confidence <= 1


# ============================================================================
# Setup/Teardown Hooks
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton state between tests"""
    yield
    # Add cleanup code here if needed


@pytest.fixture
def temp_config(monkeypatch, tmp_path):
    """Provide temporary config directory"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("CONFIG_DIR", str(config_dir))
    return config_dir


if __name__ == "__main__":
    pytest.main(["-v", "--collect-only"])

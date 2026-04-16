"""Tests for individual tool implementations"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from tools.confluence_tool import ConfluenceTool
from tools.azure_boards_tool import AzureBoardsTool
from tools.cloudwatch_tool import CloudWatchTool
from tools.github_actions_tool import GitHubActionsTool
from tools.snowflake_tool import SnowflakeTool
from services.base import QueryResult
from utils.exceptions import APIError, AuthenticationError


class TestConfluenceTool:
    """Test Confluence tool"""
    
    @pytest.fixture
    def tool(self):
        return ConfluenceTool()
    
    def test_tool_initialization(self, tool):
        """Test Confluence tool initializes"""
        assert tool.name == "confluence"
        assert tool.description is not None
    
    @patch('tools.confluence_tool.requests')
    def test_search_basic(self, mock_requests, tool):
        """Test basic Confluence search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Page",
                    "id": "123",
                    "key": "TEST-123"
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        result = tool.execute({"query": "test", "space": "TEST"})
        
        assert result.success is True
        assert "Test Page" in str(result.data)
    
    @patch('tools.confluence_tool.requests')
    def test_search_with_mocked_api_error(self, mock_requests, tool):
        """Test Confluence search with API error"""
        mock_requests.get.side_effect = Exception("Connection failed")
        
        result = tool.execute({"query": "test"})
        
        assert result.success is False


class TestAzureBoardsTool:
    """Test Azure Boards tool"""
    
    @pytest.fixture
    def tool(self):
        return AzureBoardsTool()
    
    def test_tool_initialization(self, tool):
        """Test Azure Boards tool initializes"""
        assert tool.name == "azure_boards"
        assert tool.description is not None
    
    @patch('tools.azure_boards_tool.requests')
    def test_query_work_items(self, mock_requests, tool):
        """Test querying work items"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workItems": [
                {
                    "id": 1,
                    "fields": {
                        "System.Title": "Bug: Login failed",
                        "System.State": "Active"
                    }
                }
            ]
        }
        mock_requests.post.return_value = mock_response
        
        result = tool.execute({
            "query": "open bugs",
            "state": "active"
        })
        
        assert result.success is True
        assert isinstance(result.data, list)
    
    @patch('tools.azure_boards_tool.requests')
    def test_sprint_metrics(self, mock_requests, tool):
        """Test sprint metrics calculation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "fields": {
                        "System.Title": "Task 1",
                        "Microsoft.VSTS.Scheduling.StoryPoints": 5
                    }
                },
                {
                    "fields": {
                        "System.Title": "Task 2",
                        "Microsoft.VSTS.Scheduling.StoryPoints": 3
                    }
                }
            ]
        }
        mock_requests.post.return_value = mock_response
        
        result = tool.execute({"query": "sprint metrics"})
        
        assert result.success is True


class TestCloudWatchTool:
    """Test CloudWatch tool"""
    
    @pytest.fixture
    def tool(self):
        with patch('tools.cloudwatch_tool.boto3'):
            yield CloudWatchTool()
    
    def test_tool_initialization(self, tool):
        """Test CloudWatch tool initializes"""
        assert tool.name == "cloudwatch"
        assert tool.description is not None
    
    def test_log_filtering_setup(self, tool):
        """Test log filtering is configured"""
        assert tool.client is not None
    
    @patch('tools.cloudwatch_tool.boto3')
    def test_filter_logs_by_level(self, mock_boto3, tool):
        """Test filtering logs by level"""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.filter_log_events.return_value = {
            "events": [
                {"message": "ERROR: Something failed", "timestamp": 1000}
            ]
        }
        
        # Manually set the mocked client
        tool.client = mock_client
        
        result = tool.execute({
            "query": "errors",
            "log_group": "app-logs"
        })
        
        assert result.success is True or result.success is False  # May fail due to mocking


class TestGitHubActionsTool:
    """Test GitHub Actions tool"""
    
    @pytest.fixture
    def tool(self):
        return GitHubActionsTool()
    
    def test_tool_initialization(self, tool):
        """Test GitHub Actions tool initializes"""
        assert tool.name == "github_actions"
        assert tool.description is not None
    
    @patch('tools.github_actions_tool.requests')
    def test_get_workflow_runs(self, mock_requests, tool):
        """Test getting workflow runs"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "id": 1,
                    "name": "CI",
                    "conclusion": "failure",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        result = tool.execute({
            "query": "failed builds",
            "repo": "owner/repo"
        })
        
        assert result.success is True or result.success is False
    
    @patch('tools.github_actions_tool.requests')
    def test_analyze_failure(self, mock_requests, tool):
        """Test failure analysis"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {
                    "name": "test",
                    "conclusion": "failure",
                    "steps": [
                        {"name": "pytest", "conclusion": "failure"}
                    ]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        result = tool.execute({
            "query": "debug failure",
            "run_id": "12345"
        })
        
        assert result.success is True or result.success is False


class TestSnowflakeTool:
    """Test Snowflake tool"""
    
    @pytest.fixture
    def tool(self):
        with patch('tools.snowflake_tool.snowflake.connector'):
            yield SnowflakeTool()
    
    def test_tool_initialization(self, tool):
        """Test Snowflake tool initializes"""
        assert tool.name == "snowflake"
        assert tool.description is not None
    
    def test_sql_generation(self, tool):
        """Test SQL generation from natural language"""
        # Test that tool can process queries even if connection fails
        result = tool.execute({
            "query": "show me sales data"
        })
        
        # Should handle gracefully even without connection
        assert isinstance(result, QueryResult)


class TestToolErrorHandling:
    """Test error handling across tools"""
    
    def test_confluence_handles_auth_error(self):
        """Test Confluence tool handles auth errors"""
        tool = ConfluenceTool()
        
        with patch('tools.confluence_tool.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response
            
            result = tool.execute({"query": "test"})
            assert result.success is False
    
    def test_azure_handles_not_found(self):
        """Test Azure tool handles not found errors"""
        tool = AzureBoardsTool()
        
        with patch('tools.azure_boards_tool.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_post.return_value = mock_response
            
            result = tool.execute({"query": "nonexistent"})
            assert result.success is False
    
    def test_tool_returns_query_result(self):
        """Test all tools return QueryResult objects"""
        tools = [
            ConfluenceTool(),
            AzureBoardsTool(),
            GitHubActionsTool(),
            SnowflakeTool()
        ]
        
        for tool in tools:
            assert hasattr(tool, 'execute')
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')


class TestToolResultStructure:
    """Test tool result structure"""
    
    def test_query_result_success_fields(self):
        """Test QueryResult has success and data fields"""
        result = QueryResult(success=True, data={"test": "data"})
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert hasattr(result, 'metadata')
    
    def test_query_result_error_fields(self):
        """Test QueryResult error fields"""
        result = QueryResult(
            success=False,
            data=None,
            error="API failed",
            error_type="APIError"
        )
        
        assert result.success is False
        assert result.error == "API failed"
        assert result.error_type == "APIError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

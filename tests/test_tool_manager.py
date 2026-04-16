"""Tests for tool manager"""
import pytest
from unittest.mock import Mock, MagicMock
from tools.manager import ToolManager, ToolType
from services.base import QueryResult


class MockTool:
    """Mock tool for testing"""
    def __init__(self, name, should_validate=True):
        self.name = name
        self._should_validate = should_validate
    
    def validate(self):
        return self._should_validate
    
    def execute(self, query):
        return QueryResult(
            success=True,
            data={"mock": "data"},
            metadata={"tool": self.name}
        )


class TestToolManager:
    """Test ToolManager class"""
    
    @pytest.fixture
    def manager(self):
        return ToolManager()
    
    def test_register_tool(self, manager):
        """Test registering a tool"""
        tool = MockTool("test")
        result = manager.register_tool(ToolType.CONFLUENCE, tool)
        assert result is True
        assert ToolType.CONFLUENCE in manager.tools
        
    def test_register_tool_validation_fails(self, manager):
        """Test registering a tool that fails validation"""
        tool = MockTool("test", should_validate=False)
        result = manager.register_tool(ToolType.CONFLUENCE, tool)
        assert result is False
        
    def test_list_available_tools_empty(self, manager):
        """Test listing tools when none registered"""
        tools = manager.list_available_tools()
        assert len(tools) == 0
        
    def test_list_available_tools(self, manager):
        """Test listing registered tools"""
        tool = MockTool("confluence")
        manager.register_tool(ToolType.CONFLUENCE, tool)
        
        tools = manager.list_available_tools()
        assert len(tools) == 1
        assert "confluence" in tools
        
    def test_get_tool_for_query_confluence(self, manager):
        """Test tool selection for Confluence query"""
        manager.tools[ToolType.CONFLUENCE] = MockTool("confluence")
        
        tool_type = manager.get_tool_for_query("Find documentation")
        assert tool_type == ToolType.CONFLUENCE
        
    def test_get_tool_for_query_azure(self, manager):
        """Test tool selection for Azure Boards query"""
        manager.tools[ToolType.AZURE_BOARDS] = MockTool("azure")
        
        tool_type = manager.get_tool_for_query("Show my work items")
        assert tool_type == ToolType.AZURE_BOARDS
        
    def test_get_tool_for_query_cloudwatch(self, manager):
        """Test tool selection for CloudWatch query"""
        manager.tools[ToolType.CLOUDWATCH] = MockTool("cloudwatch")
        
        tool_type = manager.get_tool_for_query("Show errors in logs")
        assert tool_type == ToolType.CLOUDWATCH
        
    def test_get_tool_for_query_github(self, manager):
        """Test tool selection for GitHub Actions query"""
        manager.tools[ToolType.GITHUB_ACTIONS] = MockTool("github")
        
        tool_type = manager.get_tool_for_query("Why did build fail")
        assert tool_type == ToolType.GITHUB_ACTIONS
        
    def test_get_tool_for_query_snowflake(self, manager):
        """Test tool selection for Snowflake query"""
        manager.tools[ToolType.SNOWFLAKE] = MockTool("snowflake")
        
        tool_type = manager.get_tool_for_query("Get row count for data")
        assert tool_type == ToolType.SNOWFLAKE
        
    def test_get_tool_for_query_no_match(self, manager):
        """Test tool selection when no tool matches"""
        tool_type = manager.get_tool_for_query("xyz abc xyz")
        assert tool_type is None
        
    def test_execute_query_empty(self, manager):
        """Test executing empty query"""
        result = manager.execute_query("")
        assert result.success is False
        assert result.error is not None
        
    def test_execute_query_auto_detect(self, manager):
        """Test executing query with auto-detection"""
        tool = MockTool("confluence")
        manager.register_tool(ToolType.CONFLUENCE, tool)
        
        result = manager.execute_query("Find documentation")
        assert result.success is True
        assert result.metadata.get("tool_used") == "confluence"
        
    def test_execute_query_explicit_tool(self, manager):
        """Test executing query with explicit tool"""
        tool = MockTool("confluence")
        manager.register_tool(ToolType.CONFLUENCE, tool)
        
        result = manager.execute_query("Any query", ToolType.CONFLUENCE)
        assert result.success is True
        
    def test_execute_query_tool_not_registered(self, manager):
        """Test executing query with unregistered tool"""
        result = manager.execute_query("query", ToolType.CONFLUENCE)
        assert result.success is False
        assert "not registered" in result.error
        
    def test_batch_execute(self, manager):
        """Test batch query execution"""
        tool = MockTool("confluence")
        manager.register_tool(ToolType.CONFLUENCE, tool)
        
        queries = [
            {"query": "Find docs", "tool_type": "confluence"},
            {"query": "Find docs again", "tool_type": "confluence"},
        ]
        
        results = manager.batch_execute(queries)
        assert len(results) == 2
        assert all(r.success for r in results)
        
    def test_get_tool_info(self, manager):
        """Test getting tool info"""
        tool = MockTool("confluence")
        manager.register_tool(ToolType.CONFLUENCE, tool)
        
        info = manager.get_tool_info(ToolType.CONFLUENCE)
        assert info["available"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

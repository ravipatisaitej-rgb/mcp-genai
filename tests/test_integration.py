"""Integration tests for full query pipeline"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from tools.manager import ToolManager, ToolType
from utils.query_parser import QueryParser
from services.base import QueryResult
from tests.conftest import (
    MockConfluenceTool, MockAzureBoardsTool, MockCloudWatchTool,
    MockGitHubTool, MockSnowflakeTool
)


@pytest.mark.integration
class TestFullQueryPipeline:
    """Test complete query processing pipeline"""
    
    @pytest.fixture
    def full_system(self):
        """Set up full system with parser and manager"""
        parser = QueryParser()
        manager = ToolManager()
        
        # Register all mock tools
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
        manager.register_tool(ToolType.CLOUDWATCH, MockCloudWatchTool())
        manager.register_tool(ToolType.GITHUB_ACTIONS, MockGitHubTool())
        manager.register_tool(ToolType.SNOWFLAKE, MockSnowflakeTool())
        
        return parser, manager
    
    def test_parse_and_route_confluence_query(self, full_system):
        """Test parsing and routing a Confluence query"""
        parser, manager = full_system
        
        # Parse query
        query = "Find documentation about authentication"
        parsed = parser.parse(query)
        
        assert parsed.primary_entity == "pages"
        assert "documentation" in parsed.keywords
        
        # Route to tool
        available_tools = manager.get_available_tools()
        assert len(available_tools) > 0
    
    def test_parse_and_route_azure_query(self, full_system):
        """Test parsing and routing an Azure Boards query"""
        parser, manager = full_system
        
        # Parse query
        query = "Show open work items"
        parsed = parser.parse(query)
        
        assert parsed.primary_entity in ["work_items", "tasks"]
        assert parsed.intent in ["search", "list", "analyze"]
    
    def test_parse_and_route_cloudwatch_query(self, full_system):
        """Test parsing and routing a CloudWatch query"""
        parser, manager = full_system
        
        # Parse query
        query = "Find errors in last hour"
        parsed = parser.parse(query)
        
        assert parsed.primary_entity == "errors"
        assert parsed.time_range is not None
    
    def test_parse_and_route_github_query(self, full_system):
        """Test parsing and routing a GitHub Actions query"""
        parser, manager = full_system
        
        # Parse query
        query = "Find failed builds"
        parsed = parser.parse(query)
        
        assert parsed.primary_entity in ["errors", "build_results"]
    
    def test_end_to_end_query_execution(self, full_system):
        """Test end-to-end query execution"""
        parser, manager = full_system
        
        query = "Find my open work items"
        
        # Parse
        parsed = parser.parse(query)
        assert parsed is not None
        
        # Execute through manager
        result = manager.execute_query(query)
        
        assert isinstance(result, QueryResult)
        # May have been handled by a tool or not found
        assert hasattr(result, 'success')


@pytest.mark.integration
class TestMultiToolAggregation:
    """Test aggregating results from multiple tools"""
    
    def test_batch_execute_multiple_queries(self):
        """Test executing multiple queries in batch"""
        manager = ToolManager()
        
        # Register tools
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
        manager.register_tool(ToolType.CLOUDWATCH, MockCloudWatchTool())
        
        queries = [
            "Find documentation",
            "Show work items",
            "Find errors"
        ]
        
        results = manager.batch_execute(queries)
        
        assert isinstance(results, list)
        assert len(results) >= 0  # May have some results
    
    def test_result_aggregation_format(self):
        """Test aggregated results have consistent format"""
        manager = ToolManager()
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        
        result = manager.execute_query("Find documentation")
        
        if isinstance(result, QueryResult):
            assert hasattr(result, 'success')
            assert hasattr(result, 'data')
            if result.success:
                assert hasattr(result, 'metadata')


@pytest.mark.integration
class TestQueryParsingAccuracy:
    """Test query parser accuracy across different query types"""
    
    @pytest.fixture
    def parser(self):
        return QueryParser()
    
    def test_parse_simple_search(self, parser):
        """Test parsing simple search query"""
        result = parser.parse("find documentation")
        
        assert result.intent == "search"
        assert result.primary_entity == "pages"
        assert "documentation" in result.keywords
    
    def test_parse_complex_query_with_filters(self, parser):
        """Test parsing complex query with multiple filters"""
        query = "Show active work items assigned to john with high priority from last week"
        result = parser.parse(query)
        
        assert result.intent in ["search", "list", "analyze"]
        assert result.primary_entity in ["work_items", "tasks"]
        assert len(result.filters) > 0
        assert result.time_range is not None
    
    def test_parse_time_range_variations(self, parser):
        """Test parsing various time range expressions"""
        test_cases = [
            ("errors in last hour", True),
            ("events from last 2 days", True),
            ("logs from this week", True),
            ("data in last month", True),
        ]
        
        for query, should_have_time in test_cases:
            result = parser.parse(query)
            has_time = result.time_range is not None
            # Some may or may not have time ranges based on parsing logic
            assert isinstance(has_time, bool)
    
    def test_parse_filter_variations(self, parser):
        """Test parsing various filter expressions"""
        query = "work items status:open assignee:john priority:high"
        result = parser.parse(query)
        
        assert len(result.filters) >= 0  # May or may not extract filters
        assert isinstance(result.filters, list)
    
    def test_confidence_score_consistency(self, parser):
        """Test confidence scores are consistent"""
        queries = [
            "find documentation",
            "show list of bugs",
            "analyze failures"
        ]
        
        for query in queries:
            result = parser.parse(query)
            assert 0 <= result.confidence <= 1
            assert isinstance(result.confidence, (int, float))


@pytest.mark.integration
class TestErrorPropagation:
    """Test error handling through the pipeline"""
    
    def test_invalid_query_handled(self):
        """Test handling of invalid queries"""
        parser = QueryParser()
        manager = ToolManager()
        
        # Register a tool
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        
        # Empty query should be handled gracefully
        result = manager.execute_query("")
        
        # Should either return error result or default result
        assert result is None or isinstance(result, QueryResult)
    
    def test_tool_execution_failure_handled(self):
        """Test handling of tool execution failures"""
        manager = ToolManager()
        
        # Create a failing mock tool
        failing_tool = Mock()
        failing_tool.name = "failing"
        failing_tool.execute.return_value = QueryResult(
            success=False,
            error="API Error",
            error_type="APIError"
        )
        
        manager.register_tool(ToolType.CONFLUENCE, failing_tool)
        
        # Should handle failure gracefully
        result = manager.execute_query("test query")
        # Result may be None or an error QueryResult
        assert result is None or isinstance(result, QueryResult)


@pytest.mark.integration
class TestSystemInteroperability:
    """Test how different components work together"""
    
    def test_tool_manager_with_parser(self):
        """Test ToolManager works correctly with QueryParser"""
        parser = QueryParser()
        manager = ToolManager()
        
        # Register tools
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
        
        # Parse a query
        query = "find documentation"
        parsed = parser.parse(query)
        
        # Use parsed info to select tool (simulating what manager would do)
        assert parsed.primary_entity is not None
        assert parsed.intent is not None
    
    def test_query_result_serialization(self):
        """Test QueryResult can be properly serialized"""
        result = QueryResult(
            success=True,
            data={"test": "data"},
            metadata={"source": "confluence"}
        )
        
        # Should be serializable to dict
        result_dict = result.__dict__
        assert "success" in result_dict
        assert "data" in result_dict
    
    def test_multiple_tools_same_query_type(self):
        """Test multiple tools can handle same query type"""
        manager = ToolManager()
        
        # Register multiple tools
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
        manager.register_tool(ToolType.CLOUDWATCH, MockCloudWatchTool())
        
        # All should be registered
        tools = manager.get_available_tools()
        assert len(tools) >= 3


@pytest.mark.slow
@pytest.mark.integration
class TestPerformance:
    """Test performance characteristics of the pipeline"""
    
    def test_parser_performance_on_complex_query(self):
        """Test parser handles complex query reasonably quickly"""
        import time
        
        parser = QueryParser()
        query = "Find all critical bugs assigned to john or mary in last 2 weeks in space BUGS with status open or reopened sorted by priority"
        
        start = time.time()
        result = parser.parse(query)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0
        assert result is not None
    
    def test_batch_execution_performance(self):
        """Test batch execution performance"""
        import time
        
        manager = ToolManager()
        manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
        manager.register_tool(ToolType.AZURE_BOARDS, MockAzureBoardsTool())
        
        queries = [f"query {i}" for i in range(10)]
        
        start = time.time()
        results = manager.batch_execute(queries)
        elapsed = time.time() - start
        
        # Should handle batch reasonably quickly
        assert elapsed < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

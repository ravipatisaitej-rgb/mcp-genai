"""Tests for query parser"""
import pytest
from datetime import datetime, timedelta
from utils.query_parser import QueryParser, parse_query, TimeRange, Filter, FilterOperator


class TestTimeRange:
    """Test TimeRange class"""
    
    def test_from_lookback(self):
        """Test creating time range from lookback days"""
        tr = TimeRange.from_lookback(7)
        assert tr.lookback_days == 7
        assert tr.start is not None
        assert tr.end is not None
        
    def test_to_dict(self):
        """Test converting time range to dict"""
        tr = TimeRange.from_lookback(1)
        result = tr.to_dict()
        assert "start" in result
        assert "end" in result
        assert result["start"] is not None
        assert result["end"] is not None


class TestFilter:
    """Test Filter class"""
    
    def test_filter_creation(self):
        """Test creating a filter"""
        f = Filter(field="status", operator=FilterOperator.EQUALS, value="open")
        assert f.field == "status"
        assert f.value == "open"
        
    def test_filter_to_dict(self):
        """Test converting filter to dict"""
        f = Filter(field="status", operator=FilterOperator.EQUALS, value="open")
        result = f.to_dict()
        assert result["field"] == "status"
        assert result["operator"] == "eq"
        assert result["value"] == "open"


class TestQueryParser:
    """Test QueryParser class"""
    
    @pytest.fixture
    def parser(self):
        return QueryParser()
    
    def test_intent_detection_search(self, parser):
        """Test search intent detection"""
        result = parser.parse("Find all errors")
        assert result.intent == "search"
        
    def test_intent_detection_list(self, parser):
        """Test list intent detection"""
        result = parser.parse("List all work items")
        assert result.intent == "list"
        
    def test_intent_detection_count(self, parser):
        """Test count intent detection"""
        result = parser.parse("How many failed builds")
        assert result.intent == "count"
        
    def test_entity_extraction_errors(self, parser):
        """Test entity extraction for errors"""
        result = parser.parse("Show errors in logs")
        assert result.primary_entity == "errors"
        
    def test_entity_extraction_work_items(self, parser):
        """Test entity extraction for work items"""
        result = parser.parse("List my tasks")
        assert result.primary_entity == "work_items"
        
    def test_time_range_last_hours(self, parser):
        """Test time range parsing for hours"""
        result = parser.parse("errors in last 2 hours")
        assert result.time_range is not None
        assert result.time_range.lookback_days == 2 / 24  # 2 hours
        
    def test_time_range_last_days(self, parser):
        """Test time range parsing for days"""
        result = parser.parse("errors in last 3 days")
        assert result.time_range is not None
        assert result.time_range.lookback_days == 3
        
    def test_status_filter_open(self, parser):
        """Test status filter extraction"""
        result = parser.parse("show open items")
        assert any(f.field == "status" for f in result.filters)
        
    def test_limit_extraction(self, parser):
        """Test limit extraction"""
        result = parser.parse("show top 10 results")
        assert result.limit == 10
        
    def test_sorting_extraction(self, parser):
        """Test sorting extraction"""
        result = parser.parse("sort by date"),
        assert result.sort_by is not None
        
    def test_aggregation_count(self, parser):
        """Test aggregation extraction"""
        result = parser.parse("count total errors")
        assert result.aggregation == "count"
        
    def test_aggregation_sum(self, parser):
        """Test sum aggregation"""
        result = parser.parse("sum all amounts")
        assert result.aggregation == "sum"
        
    def test_keywords_extraction(self, parser):
        """Test keywords extraction"""
        result = parser.parse("find database migration errors")
        assert len(result.keywords) > 0
        assert "database" in result.keywords or "migration" in result.keywords or "error" in result.keywords
        
    def test_confidence_scoring(self, parser):
        """Test confidence scoring"""
        result = parser.parse("show open work items")
        assert 0 <= result.confidence <= 1
        assert result.confidence > 0.7
        
    def test_complex_query(self, parser):
        """Test parsing complex query"""
        result = parser.parse(
            "Find all open bugs assigned to john in last 2 weeks sorted by priority"
        )
        assert result.intent == "search"
        assert result.primary_entity == "errors"
        assert result.time_range is not None
        assert len(result.filters) > 0


class TestParseQueryFunction:
    """Test the convenience parse_query function"""
    
    def test_parse_query_returns_parsed_query(self):
        """Test that parse_query returns a ParsedQuery object"""
        result = parse_query("Show open items")
        assert result is not None
        assert hasattr(result, 'intent')
        assert hasattr(result, 'primary_entity')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

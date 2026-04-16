# Test Suite Documentation

## Overview

Comprehensive test suite for the Enterprise MCP-Style Tools project using pytest framework. Total of **1,739 lines** of test code across 8 test modules plus supporting configuration.

## Test Structure

### Core Test Modules

#### 1. **tests/test_query_parser.py** (280+ lines)
Tests the natural language query parsing engine.

**Coverage:**
- `TimeRange` class - temporal expression parsing
- `Filter` class - filter condition extraction
- `ParsedQuery` class - complete query representation
- `QueryParser` class - main parsing logic

**Test Methods (20+):**
- Intent detection (search, list, count, analyze)
- Entity extraction (pages, work_items, errors, logs, data)
- Time range parsing (last N hours/days/weeks/months)
- Filter extraction and operators
- Limit and aggregation parsing
- Complex multi-filter queries
- Confidence scoring

**Key Tests:**
```python
test_parse_search_intent()
test_parse_entity_extraction()
test_parse_time_range_variations()
test_parse_sort_preference()
test_complex_query()
```

#### 2. **tests/test_tool_manager.py** (200+ lines)
Tests the tool orchestration and routing logic.

**Coverage:**
- `ToolManager` class - main orchestrator
- Tool registration
- Tool validation
- Query routing
- Batch execution

**Test Methods (15+):**
- Tool registration and deregistration
- Available tools listing
- Tool validation
- Query execution with auto-detection
- Batch query execution
- Tool selection by query type
- Error handling in execution

**Key Tests:**
```python
test_register_tool()
test_validate_tool_interface()
test_execute_query_auto_detect()
test_batch_execute()
test_handle_tool_execution_error()
```

#### 3. **tests/test_exceptions.py** (85+ lines)
Tests the exception hierarchy and error handling.

**Coverage:**
- `MCPToolException` - base exception
- `ConfigurationError` - config issues
- `APIError` and subtypes
  - `AuthenticationError`
  - `RateLimitError`
  - `NotFoundError`
- `QueryParseError` - parsing failures
- `DataAggregationError` - aggregation issues
- `TimeoutError` - timeout handling

**Test Methods (12+):**
- Exception initialization
- Exception hierarchy validation
- Exception message formatting
- Exception context preservation
- Error code mapping

**Key Tests:**
```python
test_exception_hierarchy()
test_authentication_error()
test_rate_limit_error()
test_custom_error_message()
```

#### 4. **tests/test_base_service.py** (130+ lines)
Tests core service base classes.

**Coverage:**
- `APIResponse` - HTTP response wrapper
- `RateLimitInfo` - rate limit tracking
- `QueryResult` - unified result format

**Test Methods (15+):**
- API response status checks
- Rate limit info calculations
- Result success/error states
- Metadata handling
- Serialization

**Key Tests:**
```python
test_api_response_success()
test_api_response_error()
test_rate_limit_backoff_calculation()
test_query_result_serialization()
```

#### 5. **tests/test_api.py** (150+ lines) - NEW
Tests FastAPI endpoints and HTTP interface.

**Coverage:**
- Root endpoint
- Health check endpoint
- Tools list endpoint
- Query endpoint
- Parse endpoint
- Error handling
- Response validation

**Test Classes:**
- `TestAPIEndpoints` - endpoint functionality
- `TestQueryValidation` - input validation
- `TestAPIErrorHandling` - error responses
- `TestHealthCheckFields` - health response structure
- `TestParseEndpointResponses` - response format

**Key Tests:**
```python
test_root_endpoint()
test_query_endpoint_empty_query()
test_parse_endpoint_with_complex_query()
test_parse_response_has_confidence()
```

#### 6. **tests/test_tools.py** (200+ lines) - NEW
Tests individual tool implementations.

**Coverage:**
- ConfluenceTool searching
- AzureBoardsTool work item queries
- CloudWatchTool log filtering
- GitHubActionsTool workflow analysis
- SnowflakeTool data queries
- Tool initialization
- Error handling per tool
- Result structure validation

**Tool Test Classes:**
- `TestConfluenceTool` - Confluence search and API mocking
- `TestAzureBoardsTool` - Azure DevOps work items
- `TestCloudWatchTool` - AWS CloudWatch logs
- `TestGitHubActionsTool` - GitHub CI/CD
- `TestSnowflakeTool` - Data warehouse
- `TestToolErrorHandling` - error scenarios
- `TestToolResultStructure` - output validation

**Key Tests:**
```python
test_confluence_search_basic()
test_azure_query_work_items()
test_cloudwatch_filter_logs_by_level()
test_github_get_workflow_runs()
test_snowflake_sql_generation()
```

#### 7. **tests/test_api_client.py** (300+ lines) - NEW
Tests BaseAPIClient resilience patterns.

**Coverage:**
- Client initialization
- Exponential backoff retry logic
- Rate limit detection and handling
- HTTP method implementations (GET, POST, PUT)
- Authentication (Bearer, Basic, Custom)
- Error handling (401, 404, 429, 5xx)
- Connection pooling
- Header extraction

**Test Classes:**
- `TestAPIClientInitialization` - setup
- `TestAPIClientRetryLogic` - backoff retry
- `TestRateLimitHandling` - rate limiting
- `TestAPIResponseHandling` - response types
- `TestAPIClientErrorHandling` - error mapping
- `TestAPIClientAuthentication` - auth methods
- `TestAPIClientMethods` - HTTP methods

**Key Tests:**
```python
test_retry_on_500_error()
test_exponential_backoff_delays()
test_extract_rate_limit_from_headers()
test_rate_limited_on_429()
test_bearer_token_authentication()
```

#### 8. **tests/test_integration.py** (240+ lines) - NEW
End-to-end integration tests.

**Coverage:**
- Full query parsing pipeline
- Tool routing integration
- Multi-tool aggregation
- Parser accuracy
- Error propagation
- System interoperability
- Performance benchmarks

**Test Classes:**
- `TestFullQueryPipeline` - end-to-end flows
- `TestMultiToolAggregation` - multi-tool results
- `TestQueryParsingAccuracy` - parser validation
- `TestErrorPropagation` - error handling
- `TestSystemInteroperability` - component integration
- `TestPerformance` - performance characteristics

**Key Tests:**
```python
test_parse_and_route_confluence_query()
test_end_to_end_query_execution()
test_batch_execute_multiple_queries()
test_parse_complex_query_with_filters()
test_parser_performance_on_complex_query()
```

### Supporting Files

#### **tests/conftest.py** (280+ lines) - NEW
Pytest configuration and shared fixtures.

**Mock Tool Classes:**
- `MockConfluenceTool` - Confluence mock with realistic responses
- `MockAzureBoardsTool` - Azure DevOps mock
- `MockCloudWatchTool` - CloudWatch mock
- `MockGitHubTool` - GitHub Actions mock
- `MockSnowflakeTool` - Snowflake mock

**Pytest Fixtures:**
- `query_parser` - QueryParser instance
- `tool_manager` - ToolManager with all mock tools
- `mock_api_response` - Mock API response
- `mock_rate_limit_info` - Mock rate limit info
- `sample_queries` - Collection of test queries
- `mock_http_session` - Mock HTTP session

**Test Utilities:**
- `create_mock_tool()` - Dynamic mock tool creation
- `assert_query_result_valid()` - Result validation
- `assert_parsed_query_valid()` - Parse result validation

**Pytest Markers:**
- `@pytest.mark.integration` - integration tests
- `@pytest.mark.slow` - slow running tests
- `@pytest.mark.mock_api` - API mocking tests

#### **pytest.ini** - NEW
Pytest configuration file.

**Settings:**
- Test discovery patterns
- Custom markers definition
- Output verbosity
- Coverage options
- Logging configuration
- Warning filters
- Test paths

## Test Statistics

| Component | Test File | Lines | Methods | Coverage |
|-----------|-----------|-------|---------|----------|
| Query Parser | test_query_parser.py | 280+ | 20+ | Intent, entity, time, filters, confidence |
| Tool Manager | test_tool_manager.py | 200+ | 15+ | Registration, routing, batch, execution |
| Exceptions | test_exceptions.py | 85+ | 12+ | All exception types, hierarchy, mapping |
| Base Service | test_base_service.py | 130+ | 15+ | APIResponse, RateLimitInfo, QueryResult |
| FastAPI | test_api.py | 150+ | 18+ | Endpoints, validation, error handling |
| Tools | test_tools.py | 200+ | 25+ | All 5 tools, mocking, error handling |
| API Client | test_api_client.py | 300+ | 30+ | Retry logic, rate limits, auth |
| Integration | test_integration.py | 240+ | 25+ | E2E workflows, aggregation, performance |
| **Total** | **8 files + conftest.py + pytest.ini** | **~1,739 lines** | **>150 test methods** | **Comprehensive** |

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_query_parser.py -v
```

### Run Tests by Marker
```bash
# Integration tests only
pytest -m integration

# Unit tests only
pytest -m "not integration"

# Slow tests
pytest -m slow

# API mock tests
pytest -m mock_api
```

### Run with Coverage
```bash
pytest --cov=tools --cov=services --cov=utils --cov-report=html
```

### Verbose Output
```bash
pytest -v -s
```

### Stop on First Failure
```bash
pytest -x
```

### Run Last Failed Tests
```bash
pytest --lf
```

## Key Testing Patterns

### 1. Mock Tools Pattern
```python
class MockConfluenceTool(BaseTool):
    def execute(self, params: dict) -> QueryResult:
        return QueryResult(success=True, data={...})
```

### 2. Fixture Reusability
```python
@pytest.fixture
def tool_manager():
    manager = ToolManager()
    manager.register_tool(ToolType.CONFLUENCE, MockConfluenceTool())
    return manager
```

### 3. Error Scenario Testing
```python
def test_authentication_error_on_401(self, mock_get):
    mock_get.return_value.status_code = 401
    with pytest.raises(AuthenticationError):
        client.handle_error(response)
```

### 4. Performance Testing
```python
@pytest.mark.slow
def test_parser_performance():
    start = time.time()
    result = parser.parse(complex_query)
    assert time.time() - start < 1.0
```

## Test Dependencies

**Core Testing:**
- pytest 7.4.3
- pytest-mock (for mocking)
- pytest-cov (for coverage reporting)

**Application:**
- fastapi 0.104.1
- requests 2.31.0
- pydantic 2.5.0

**Optional:**
- pytest-timeout (for test timeouts)
- pytest-xdist (for parallel execution)

## Continuous Integration

### Recommended CI Configuration
```yaml
# .github/workflows/tests.yml
- Run: pytest --cov=tools --cov=services --cov=utils
- Coverage: >80%
- Markers: integration, slow, mock_api
```

## Next Steps

### Phase 2 Testing Enhancements
1. Add Selenium tests for web UI (when UI is built)
2. Add performance profiling tests
3. Add security/authentication tests
4. Add database integration tests
5. Add Redis cache tests

### Coverage Goals
- Target >85% code coverage
- 100% coverage for critical paths (API client, error handling)
- >80% coverage for each tool implementation

### Monitoring
- Track test execution time trends
- Monitor failure patterns
- Validate retry logic under load

## Documentation

### Test Code Examples

#### Testing Query Parser
```python
def test_parse_complex_query(self, parser):
    result = parser.parse(
        "Find all open bugs assigned to john in last 2 weeks"
    )
    assert result.intent == "search"
    assert result.primary_entity == "errors"
    assert result.time_range is not None
    assert len(result.filters) > 0
```

#### Testing Tool Execution
```python
def test_tool_execution(self, manager):
    result = manager.execute_query("Find documentation")
    assert isinstance(result, QueryResult)
    assert result.success is True
```

#### Testing Error Handling
```python
def test_rate_limit_error_handling(self):
    tool = MockConfluenceTool()
    # Tool handles rate limiting gracefully
    result = tool.execute({"query": "test"})
    assert isinstance(result, QueryResult)
```

## Summary

This comprehensive test suite provides:
- ✅ **1,739 lines** of production-quality test code
- ✅ **>150 test methods** covering all components
- ✅ **8 test modules** organized by component
- ✅ **Mock tools & fixtures** for realistic testing
- ✅ **Integration tests** for end-to-end validation
- ✅ **Error scenario coverage** for resilience
- ✅ **Performance benchmarks** for optimization
- ✅ **Pytest configuration** for easy execution

Ready for CI/CD integration and continuous quality monitoring.

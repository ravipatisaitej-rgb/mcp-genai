# MCP Tools Architecture

## Overview

This document describes the architecture and design patterns of the MCP Enterprise Tools project.

## Design Philosophy

The project follows these core principles:

1. **Modularity** - Each tool is independent and can be used standalone
2. **Extensibility** - New tools can be added without modifying existing code
3. **Maintainability** - Clean code, clear separation of concerns
4. **Reliability** - Proper error handling, retries, and logging
5. **Performance** - Efficient API calls, connection pooling, caching-ready

## Component Architecture

### Layer 1: API Server (FastAPI)

**File:** `app.py`

Provides REST endpoints for tool access:

- `/query` - Execute queries with auto-tool selection
- `/query/batch` - Batch multiple queries
- `/parse` - Parse queries without execution
- Tool-specific endpoints (`/confluence/search`, `/azure/work-items`, etc.)
- Health checks and tool registration

**Key responsibilities:**
- Request validation and routing
- Response formatting
- Error handling and HTTP status codes
- Tool lifecycle management

### Layer 2: Tool Manager (Orchestration)

**File:** `tools/manager.py`

Routes queries to appropriate tools based on content:

```python
# Query routing logic
manager.execute_query("Show my open work items")
# → Routes to: AzureBoardsTool
```

**Key components:**
- Tool registration and validation
- Automatic tool selection
- Batch execution coordination

### Layer 3: Individual Tools

**Files:** `tools/{name}_tool.py`

Each tool inherits from `BaseTool` and implements:

- `validate()` - Test connection to external service
- `execute(query)` - Process natural language query

**Tools:**

| Tool | Service | Purpose |
|------|---------|---------|
| ConfluenceTool | Confluence | Documentation search & aggregation |
| AzureBoardsTool | Azure DevOps | Work item tracking |
| CloudWatchTool | AWS | Log analysis & error detection |
| GitHubActionsTool | GitHub | CI/CD pipeline analysis |
| SnowflakeTool | Snowflake | Data warehouse queries |

### Layer 4: API Clients

**File:** `services/base.py` (BaseAPIClient)

Base class providing common HTTP functionality:

```python
class ConfluenceAPIClient(BaseAPIClient):
    def search_pages(self, cql: str) -> APIResponse:
        return self._make_request("GET", "/search", params={"cql": cql})
```

**Features:**
- Automatic retries with exponential backoff
- Rate limit detection and handling
- Session management with connection pooling
- Request logging and debugging

### Layer 5: Query Parser

**File:** `utils/query_parser.py`

Converts natural language to structured parameters:

```
Input:  "Show me errors in the last 2 hours"
        ↓
Output: {
  "intent": "search",
  "entity": "errors",
  "time_range": TimeRange(start: ..., end: ...),
  "keywords": ["error"],
  "filters": [],
  "confidence": 0.95
}
```

**Parsing stages:**
1. Intent detection (search, list, count, analyze)
2. Entity extraction (logs, errors, work items, etc.)
3. Time range parsing (last 2 hours, this week, etc.)
4. Filter extraction (status, user, priority, etc.)
5. Sorting preference
6. Aggregation type
7. Confidence scoring

### Layer 6: Configuration

**File:** `config/settings.py`

Centralized configuration management:

```python
config = get_app_config()
confluence = config.confluence  # ConfluenceConfig
azure = config.azure_boards     # AzureBoardsConfig
```

**Features:**
- Environment variable loading
- Type validation with Pydantic dataclasses
- LRU caching for performance
- Optional service configuration

## Data Flow

### Successful Query Execution

```
User Request
    ↓
FastAPI Endpoint (/query)
    ↓
Request Validation
    ↓
Tool Manager.execute_query()
    ├─ Auto-detect tool (via keyword matching)
    └─ or use specified tool
    ↓
Selected Tool.execute()
    ├─ Parse query via QueryParser
    ├─ Build service-specific query (WIQL, CQL, etc.)
    └─ Execute via API Client
    ↓
API Client._make_request()
    ├─ Check rate limits
    ├─ Build auth headers
    ├─ Execute HTTP request with retries
    └─ Return APIResponse
    ↓
Tool processes response
    ├─ Parse and validate data
    ├─ Aggregate results
    └─ Generate summary
    ↓
QueryResult object
    ├─ success: True
    ├─ data: {...}
    └─ metadata: {...}
    ↓
FastAPI response JSON
    ↓
User receives result
```

## Error Handling

### Exception Hierarchy

```
Exception
├─ MCPToolException (base)
│  ├─ ConfigurationError
│  ├─ APIError
│  │  ├─ AuthenticationError
│  │  ├─ RateLimitError
│  │  └─ NotFoundError
│  ├─ QueryParseError
│  ├─ DataAggregationError
│  └─ TimeoutError
```

### Retry Strategy

```python
@backoff.on_exception(
    backoff.expo,
    requests.exceptions.RequestException,
    max_tries=3,
    jitter=backoff.full_jitter
)
def _make_request(self, method, endpoint, **kwargs):
    # HTTP request with automatic retry
```

**Backoff formula:**
- Attempt 1: immediate
- Attempt 2: 1 second + jitter
- Attempt 3: 2-4 seconds + jitter

## Query Parsing Logic

### Intent Detection

```python
Intent patterns:
- search: ["search for", "find", "show", "get"]
- list: ["list all", "show all"]
- count: ["how many", "count"]
- analyze: ["analyze", "pattern", "why"]
- filter: ["with", "where", "filtered by"]
```

### Entity Recognition

```python
Entities:
- errors/logs: error patterns
- work_items: Jira/Azure patterns
- builds: CI/CD patterns
- pages: documentation patterns
- data: warehouse patterns
```

### Time Range Parsing

```python
Patterns:
- "last 2 hours" → lookback_hours=2
- "past 3 days" → lookback_days=3
- "this week" → lookback_days=7
- "today" → lookback_days=0
```

## API Response Format

All API endpoints return a consistent JSON structure:

```json
{
  "success": true,
  "data": {
    "results": [...],
    "summary": "...",
    "aggregation": {...}
  },
  "metadata": {
    "tool_used": "azure_boards",
    "query_confidence": 0.95,
    "execution_time_ms": 1250
  }
}
```

## Rate Limiting & Performance

### Rate Limit Handling

Tools extract rate limit info from response headers:

```python
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1234567890
```

When approaching limit:
```python
if remaining < 5:
    sleep(time_until_reset)
    retry_request()
```

### Connection Pooling

HTTP sessions reuse connections:

```python
session = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

Benefits:
- Reduced latency for repeated requests
- Lower memory usage
- Fewer TCP handshakes

## Extensibility Points

### Adding a New Tool

1. Create `tools/new_tool.py`:
```python
class NewTool(BaseTool):
    def __init__(self, config):
        super().__init__("new_tool")
        self.client = NewAPIClient(config)
    
    def validate(self) -> bool:
        # Test connection
        pass
    
    def execute(self, query: str) -> QueryResult:
        # Process query
        pass
```

2. Register in `app.py`:
```python
if config.new_tool:
    tool = NewTool(config.new_tool)
    manager.register_tool(ToolType.NEW_TOOL, tool)
```

3. Add environment variables:
```bash
NEW_TOOL_URL=...
NEW_TOOL_API_KEY=...
```

### Query Parser Extensions

Add new patterns:

```python
INTENT_PATTERNS = {
    "export": [r"export\s+", r"download\s+"],  # new intent
}

STATUS_PATTERNS = {
    "in_review": ["in review", "under review"],  # new status
}
```

## Performance Characteristics

### Latency Profile

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Query parse | 10-50ms | Regex matching |
| API call | 200-1000ms | Network I/O |
| Data aggregation | 50-200ms | Parsing & processing |
| **Total** | **~500-1500ms** | Network |

### Concurrency

The app can handle multiple concurrent requests:

```python
# FastAPI is async-capable via Uvicorn
# Default workers ≈ CPU count
# Can scale horizontally with multiple instances
```

### Memory Usage

Typical resident set size:
- Idle: ~100-150 MB
- Running query: ~150-250 MB (depends on result size)

## Security Considerations

### Credential Management

✅ **Correct:**
```python
token = os.getenv("GITHUB_TOKEN")  # Load from env
```

❌ **Wrong:**
```python
token = "ghp_xxxxxxxxxxxx"  # Never hardcode
```

### Request Validation

```python
@app.post("/query")
async def execute_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query empty")
```

### HTTPS Only (Production)

```python
# In production, enforce HTTPS
CONFLUENCE_URL = "https://..."  # Always HTTPS
verify_ssl=True  # Verify SSL certificates
```

## Future Enhancements

### Phase 2 Features

1. **LLM Integration**
   - OpenAI/Claude for query understanding
   - Semantic parsing of complex queries

2. **Caching Layer**
   - Redis cache for repeated queries
   - Cache invalidation strategies

3. **Web UI**
   - React-based frontend
   - Query history and saved queries
   - Visualization of results

4. **Async Tool Execution**
   - Concurrent tool queries
   - Parallel data aggregation
   - WebSocket support for streaming

5. **Advanced Analytics**
   - Anomaly detection models
   - Trend analysis
   - Predictive insights

## References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Requests Library](https://docs.python-requests.org/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [Design Patterns](https://refactoring.guru/design-patterns)


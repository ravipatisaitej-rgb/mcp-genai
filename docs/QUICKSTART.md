# Quick Start Guide

Get up and running in 5 minutes.

## Installation

```bash
# Clone repo
git clone <repo>
cd mcp-genai

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Configuration

Edit `.env` with your API credentials:

```bash
# Minimal config: just enable one tool
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-token-here
```

## Run the Server

```bash
# Method 1: Direct Python
python app.py

# Method 2: Uvicorn (with auto-reload)
uvicorn app:app --reload --port 8000

# Method 3: Docker (optional)
docker build -t mcp-tools .
docker run -p 8000:8000 --env-file .env mcp-tools
```

API available at: **http://localhost:8000**

## Using the API

### 1. Check Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "available_tools": ["confluence", "azure_boards"],
  "config_status": {"confluence": true, "azure_boards": true}
}
```

### 2. Execute Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find onboarding guide"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "pages": [
      {"title": "Onboarding Guide", "url": "..."}
    ],
    "summary": "Found 1 page(s)..."
  },
  "metadata": {"tool_used": "confluence"}
}
```

### 3. Auto-Generated Docs

Open browser to: **http://localhost:8000/docs**

Interactive Swagger UI with all endpoints.

## Common Queries

### Confluence
```bash
"Find documentation about database schema"
"Search for deployment guide in OPS space"
"Get onboarding materials"
```

### Azure Boards
```bash
"Show my open work items"
"What did I complete last sprint"
"List all bugs in current sprint"
```

### CloudWatch
```bash
"Show errors in last 2 hours"
"Find logs related to API failure"
"What went wrong with /api/users"
```

### GitHub Actions
```bash
"Why did my last build fail?"
"Show recent pipeline runs"
"What's the status of main branch builds?"
```

### Snowflake
```bash
"Get row count for sales table"
"Show top 10 customers by revenue"
"Find data anomalies in products table"
```

## Troubleshooting

### 401 Unauthorized
```
Error: AuthenticationError
Fix: Check API tokens are correct and not expired
```

### No Tools Available
```
Error: No tools are configured
Fix: Add at least one service to .env file
```

### Rate Limit Exceeded
```
Error: RateLimitError
Fix: Wait or increase API token quota
API automatically backs off when limits approached
```

### Connection Timeout
```
Error: TimeoutError
Fix: Check network connectivity to service
Increase CONFLUENCE_TIMEOUT, etc. in .env
```

## Next Steps

1. **Read Full Docs:** See [README.md](../README.md)
2. **Understand Architecture:** See [ARCHITECTURE.md](./ARCHITECTURE.md)
3. **View Examples:** See [examples.py](../examples.py)
4. **Deploy:** Run in Docker/K8s for production
5. **Extend:** Add custom tools following the patterns

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI server entry point |
| `tools/manager.py` | Tool orchestrator |
| `tools/*_tool.py` | Individual tool implementations |
| `utils/query_parser.py` | Natural language processing |
| `config/settings.py` | Configuration management |
| `.env` | API credentials (gitignored) |

## Production Deployment

### Environment Variables

```bash
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
HOST=0.0.0.0
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    restart: unless-stopped
```

### Health Checks

```bash
# Kubernetes liveness probe
curl http://localhost:8000/health

# Expected response (healthy):
{"status": "healthy", ...}
```

## Performance Tuning

### Uvicorn Workers

```bash
# For CPU-bound workloads (query parsing):
uvicorn app:app --workers 4

# For I/O-bound workloads (API calls):
# Default is fine (async handles I/O)
```

### Caching (Future)

Enable Redis caching:
```python
from functools import lru_cache
@lru_cache(maxsize=100)
def get_cached_result(query):
    ...
```

## Getting Help

Check the following in order:

1. **Error message** - Likely explains the issue
2. **logs** - `LOG_LEVEL=DEBUG` for detailed output
3. **config** - Verify .env file has correct credentials
4. **API docs** - http://localhost:8000/docs
5. **Architecture** - docs/ARCHITECTURE.md
6. **Examples** - examples.py

---

**Ready to query?** Start the server and hit the `/docs` endpoint!

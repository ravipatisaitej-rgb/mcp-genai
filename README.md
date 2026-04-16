# MCP Enterprise Tools

Query Confluence, Azure Boards, CloudWatch, GitHub Actions, and Snowflake using natural language — exposed as a REST API.

## Setup

```bash
git clone <repo-url>
cd mcp-genai

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill in credentials for whichever tools you use
```

## Run

```bash
python app.py
# or
uvicorn app:app --reload
```

API at http://localhost:8000 — interactive docs at http://localhost:8000/docs

## Configuration

You only need to configure the tools you actually use. Leave the rest blank and they'll be skipped at startup.

| Tool | Required env vars |
|------|-------------------|
| Confluence | `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN` |
| Azure Boards | `AZURE_ORGANIZATION`, `AZURE_PROJECT`, `AZURE_PAT_TOKEN` |
| CloudWatch | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| GitHub Actions | `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` |
| Snowflake | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_ROLE` |

## Usage

```bash
# Check which tools loaded
curl http://localhost:8000/health

# Run a query (tool is auto-selected based on content)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show errors in last 2 hours"}'

# Parse a query without executing it
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "Find onboarding docs in Confluence"}'
```

## Example queries

| Intent | Query |
|--------|-------|
| Confluence | `"Find the deployment runbook"` |
| Azure Boards | `"List my open work items"` |
| CloudWatch | `"Show errors in the last hour"` |
| GitHub Actions | `"Why did my last build fail?"` |
| Snowflake | `"Get row count for the orders table"` |

## Tests

```bash
pytest
```

## Project layout

```
app.py              — FastAPI entry point
config/settings.py  — env var loading
tools/              — one file per integration
services/base.py    — shared HTTP client + retry logic
utils/              — query parser, logging, exceptions
tests/              — pytest test suite
```

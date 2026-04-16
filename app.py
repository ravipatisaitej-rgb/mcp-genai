import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from config.settings import get_app_config
from tools.manager import ToolManager, ToolType
from tools import ConfluenceTool, AzureBoardsTool, CloudWatchTool, GitHubActionsTool, SnowflakeTool
from utils.logging_config import setup_logging
from utils.query_parser import parse_query

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Enterprise Tools", version="1.0.0")
manager = ToolManager()


class QueryRequest(BaseModel):
    query: str
    tool_type: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    config = get_app_config()

    if config.confluence:
        try:
            tool = ConfluenceTool(config.confluence.url, config.confluence.username, config.confluence.api_token)
            manager.register_tool(ToolType.CONFLUENCE, tool)
        except Exception as e:
            logger.warning("Confluence init failed: %s", e)

    if config.azure_boards:
        try:
            tool = AzureBoardsTool(config.azure_boards.organization, config.azure_boards.project, config.azure_boards.pat_token)
            manager.register_tool(ToolType.AZURE_BOARDS, tool)
        except Exception as e:
            logger.warning("Azure Boards init failed: %s", e)

    if config.aws:
        try:
            tool = CloudWatchTool(config.aws.region, config.aws.access_key_id, config.aws.secret_access_key)
            manager.register_tool(ToolType.CLOUDWATCH, tool)
        except Exception as e:
            logger.warning("CloudWatch init failed: %s", e)

    if config.github:
        try:
            tool = GitHubActionsTool(config.github.token, config.github.owner, config.github.repo)
            manager.register_tool(ToolType.GITHUB_ACTIONS, tool)
        except Exception as e:
            logger.warning("GitHub init failed: %s", e)

    if config.snowflake:
        try:
            tool = SnowflakeTool(
                config.snowflake.account, config.snowflake.user, config.snowflake.password,
                config.snowflake.database, config.snowflake.schema,
                config.snowflake.warehouse, config.snowflake.role
            )
            manager.register_tool(ToolType.SNOWFLAKE, tool)
        except Exception as e:
            logger.warning("Snowflake init failed: %s", e)


@app.get("/")
async def root():
    return {
        "service": "MCP Enterprise Tools",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {"health": "GET /health", "tools": "GET /tools", "query": "POST /query"}
    }


@app.get("/health")
async def health():
    tools = manager.list_available_tools()
    return {"status": "healthy" if tools else "degraded", "available_tools": tools}


@app.get("/tools")
async def list_tools():
    return manager.list_available_tools()


@app.post("/query")
async def execute_query(request: QueryRequest):
    if not manager.list_available_tools():
        raise HTTPException(status_code=503, detail="No tools configured")

    result = manager.execute_query(request.query, None)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"success": result.success, "data": result.data, "metadata": result.metadata}


@app.post("/parse")
async def parse_query_endpoint(request: QueryRequest):
    parsed = parse_query(request.query)
    return parsed.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

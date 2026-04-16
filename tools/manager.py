from typing import Dict, Optional, List, Any
from enum import Enum
from utils.logging_config import ToolLogger
from services.base import BaseTool, QueryResult
from utils.exceptions import ConfigurationError


class ToolType(Enum):
    CONFLUENCE = "confluence"
    AZURE_BOARDS = "azure_boards"
    CLOUDWATCH = "cloudwatch"
    GITHUB_ACTIONS = "github_actions"
    SNOWFLAKE = "snowflake"


class ToolManager:
    def __init__(self):
        self.logger = ToolLogger("ToolManager")
        self.tools: Dict[ToolType, Optional[BaseTool]] = {t: None for t in ToolType}

    def register_tool(self, tool_type: ToolType, tool: BaseTool) -> bool:
        try:
            if tool.validate():
                self.tools[tool_type] = tool
                self.logger.info(f"Registered tool: {tool_type.value}")
                return True
            self.logger.warning(f"Tool validation failed: {tool_type.value}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to register {tool_type.value}: {e}")
            return False

    def list_available_tools(self) -> List[str]:
        return [t.value for t, tool in self.tools.items() if tool is not None]

    def get_tool_for_query(self, query: str) -> Optional[ToolType]:
        query_lower = query.lower()
        routing_rules = {
            ToolType.CONFLUENCE: ["confluence", "documentation", "wiki", "onboarding", "guide", "process"],
            ToolType.AZURE_BOARDS: ["work item", "sprint", "task", "bug", "story", "velocity"],
            ToolType.CLOUDWATCH: ["error", "log", "exception", "failure", "fatal", "warn"],
            ToolType.GITHUB_ACTIONS: ["build", "pipeline", "workflow", "deploy", "ci/cd", "github"],
            ToolType.SNOWFLAKE: ["data", "table", "query", "row count", "anomal", "revenue", "database"],
        }

        for tool_type, keywords in routing_rules.items():
            if any(k in query_lower for k in keywords):
                if self.tools[tool_type] is not None:
                    return tool_type

        return None

    def execute_query(self, query: str, tool_type: Optional[ToolType] = None) -> QueryResult:
        if not query.strip():
            return QueryResult(success=False, error="Query cannot be empty")

        if tool_type is None:
            tool_type = self.get_tool_for_query(query)

        if tool_type is None:
            available = ", ".join(self.list_available_tools())
            return QueryResult(
                success=False,
                error=f"Could not determine appropriate tool for query. Available tools: {available}"
            )

        tool = self.tools.get(tool_type)
        if tool is None:
            return QueryResult(success=False, error=f"Tool '{tool_type.value}' is not registered")

        self.logger.info(f"Executing query with {tool_type.value}: '{query[:100]}'")
        try:
            result = tool.execute(query)
            result.metadata["tool_used"] = tool_type.value
            return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            return QueryResult(success=False, error=f"Execution error in {tool_type.value}: {e}")

    def batch_execute(self, queries: List[Dict[str, Any]]) -> List[QueryResult]:
        results = []
        for q in queries:
            tool_type = None
            if q.get("tool_type"):
                try:
                    tool_type = ToolType[q["tool_type"].upper()]
                except KeyError:
                    self.logger.warning(f"Unknown tool type: {q['tool_type']}")
            results.append(self.execute_query(q.get("query"), tool_type))
        return results

    def get_tool_info(self, tool_type: ToolType) -> Dict[str, Any]:
        tool = self.tools.get(tool_type)
        if not tool:
            return {"available": False}
        return {"available": True, "name": tool.name, "type": tool_type.value}

"""Snowflake MCP Tool - Data warehouse queries"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from services.base import BaseTool, QueryResult
from utils.query_parser import parse_query, ParsedQuery
from utils.logging_config import ToolLogger
from utils.exceptions import ConfigurationError

@dataclass
class SnowflakeQueryResult:
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float

class SnowflakeTool(BaseTool):
    """Snowflake tool for data warehouse queries"""
    
    def __init__(self, account: str, user: str, password: str,
                 database: str, schema: str, warehouse: str, role: str):
        super().__init__("snowflake")
        try:
            import snowflake.connector
            self.snowflake = snowflake.connector
        except ImportError:
            raise ConfigurationError("Install: pip install snowflake-connector-python")
        
        self.account = account
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self.role = role
        self.connection = None
    
    def _get_connection(self):
        if not self.connection:
            self.connection = self.snowflake.connect(
                user=self.user,
                password=self.password,
                account=self.account,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
                role=self.role
            )
        return self.connection
    
    def validate(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False
    
    def execute(self, query: str) -> QueryResult:
        """Execute a natural language query on Snowflake"""
        try:
            parsed = parse_query(query)
            self.logger.info(f"Parsed query: {parsed.intent}")
            
            sql = self._build_sql(parsed)
            if not sql:
                return QueryResult(success=False, error="Could not parse query into SQL")
            
            result = self._execute_sql(sql)
            
            return QueryResult(
                success=True,
                data={
                    "query_result": self._serialize_result(result),
                    "summary": f"Query returned {result.row_count} rows"
                },
                metadata={"sql_executed": sql, "execution_time_ms": result.execution_time_ms}
            )
        except Exception as e:
            self.logger.error(f"Execution failed: {str(e)}")
            return QueryResult(success=False, error=str(e))
    
    def _build_sql(self, parsed: ParsedQuery) -> Optional[str]:
        """Build SQL from parsed query"""
        keywords = parsed.keywords
        if parsed.aggregation == "count" or "count" in parsed.raw_query.lower():
            return f"SELECT COUNT(*) as row_count FROM {self.schema}.{parsed.primary_entity}"
        
        limit = parsed.limit or 10
        return f"SELECT * FROM {self.schema}.{parsed.primary_entity} LIMIT {limit}"
    
    def _execute_sql(self, sql: str) -> SnowflakeQueryResult:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        start = datetime.now()
        cursor.execute(sql)
        end = datetime.now()
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        
        return SnowflakeQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=(end-start).total_seconds()*1000
        )
    
    def _serialize_result(self, result: SnowflakeQueryResult) -> Dict[str, Any]:
        return {
            "columns": result.columns,
            "rows": result.rows[:100],
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms
        }

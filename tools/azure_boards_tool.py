"""
Azure Boards MCP Tool
Tracks work items, sprints, and provides productivity metrics.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from services.base import BaseTool, BaseAPIClient, QueryResult, APIResponse
from utils.query_parser import parse_query, ParsedQuery, FilterOperator
from utils.logging_config import ToolLogger


@dataclass
class WorkItem:
    """Azure Boards work item"""
    id: int
    title: str
    type: str
    state: str
    assigned_to: Optional[str] = None
    created_date: Optional[str] = None
    closed_date: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    effort: Optional[float] = None
    priority: Optional[int] = None
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "state": self.state,
            "assigned_to": self.assigned_to,
            "created_date": self.created_date,
            "closed_date": self.closed_date,
            "tags": self.tags,
            "effort": self.effort,
            "priority": self.priority,
        }


class AzureBoardsAPIClient(BaseAPIClient):
    """Azure Boards REST API client"""
    
    def __init__(self, organization: str, project: str, pat_token: str):
        super().__init__("azure_boards")
        self.organization = organization
        self.project = project
        self.pat_token = pat_token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        import base64
        credentials = base64.b64encode(f":{self.pat_token}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    
    def _get_base_url(self) -> str:
        return f"https://dev.azure.com/{self.organization}/{self.project}/_apis"
    
    def query_work_items(
        self,
        wiql: str,
        top: int = 100
    ) -> APIResponse:
        """Execute a WIQL query (Work Item Query Language)"""
        return self._make_request(
            "POST",
            "/wit/wiql",
            json={"query": wiql},
            params={"$top": top}
        )
    
    def get_work_item(self, id: int) -> APIResponse:
        """Get details of a specific work item"""
        return self._make_request(
            "GET",
            f"/wit/workitems/{id}",
            params={"$expand": "all"}
        )
    
    def get_sprints(self, team_name: Optional[str] = None) -> APIResponse:
        """Get all sprints for the project"""
        path = f"/teams/{team_name or 'DefaultTeam'}/iterations" if team_name else "/projects/iterations"
        return self._make_request("GET", path)
    
    def get_team_velocity(self, team_name: str, sprint_id: str) -> APIResponse:
        """Get team velocity metrics"""
        return self._make_request(
            "GET",
            f"/teams/{team_name}/iterations/{sprint_id}/capacities"
        )


class AzureBoardsTool(BaseTool):
    """
    Azure Boards tool for work item tracking and sprint management.
    """
    
    def __init__(self, organization: str, project: str, pat_token: str):
        super().__init__("azure_boards")
        self.client = AzureBoardsAPIClient(organization, project, pat_token)
        self.organization = organization
        self.project = project
    
    def validate(self) -> bool:
        """Test Azure Boards connection"""
        try:
            response = self.client.get_sprints()
            return response.is_success
        except Exception as e:
            self.logger.error(f"Azure Boards validation failed: {str(e)}")
            return False
    
    def execute(self, query: str) -> QueryResult:
        """
        Execute an Azure Boards query.
        
        Examples:
            - "Show my open work items"
            - "What did I complete last sprint?"
            - "List all bugs in current sprint"
        """
        try:
            parsed_query = parse_query(query)
            self.logger.info(f"Parsed query: intent={parsed_query.intent}, entity={parsed_query.primary_entity}")
            
            # Determine what user is asking for
            if "sprint" in query.lower() or "velocity" in query.lower():
                return self._handle_sprint_query(parsed_query)
            else:
                return self._handle_work_item_query(parsed_query)
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    def _handle_work_item_query(self, parsed_query: ParsedQuery) -> QueryResult:
        """Handle work item queries"""
        wiql = self._build_wiql(parsed_query)
        
        response = self.client.query_work_items(
            wiql,
            top=parsed_query.limit or 50
        )
        
        if not response.is_success:
            return QueryResult(success=False, error="Failed to query work items")
        
        work_items = []
        if response.data and "workItems" in response.data:
            for item_ref in response.data["workItems"][:10]:  # Fetch details for top 10
                item_response = self.client.get_work_item(item_ref["id"])
                if item_response.is_success:
                    item = self._parse_work_item(item_response.data)
                    if item:
                        work_items.append(item)
        
        # Calculate metrics
        metrics = self._calculate_work_item_metrics(work_items, parsed_query)
        
        return QueryResult(
            success=True,
            data={
                "work_items": [item.to_dict() for item in work_items],
                "metrics": metrics,
                "summary": self._create_work_item_summary(work_items, metrics)
            },
            metadata={
                "query_confidence": parsed_query.confidence,
                "items_found": len(work_items),
                "wiql_used": wiql
            }
        )
    
    def _handle_sprint_query(self, parsed_query: ParsedQuery) -> QueryResult:
        """Handle sprint-related queries"""
        try:
            sprints_response = self.client.get_sprints()
            
            if not sprints_response.is_success:
                return QueryResult(success=False, error="Failed to fetch sprints")
            
            sprints = sprints_response.data.get("value", []) if sprints_response.data else []
            
            # Filter to current/active sprint
            current_sprint = self._find_current_sprint(sprints)
            
            if not current_sprint:
                return QueryResult(
                    success=True,
                    data={"sprints": sprints, "message": "No active sprint found"}
                )
            
            # Get sprint metrics
            sprint_id = current_sprint["id"]
            velocity_response = self.client.get_team_velocity("DefaultTeam", sprint_id)
            
            sprint_data = {
                "name": current_sprint.get("name"),
                "start_date": current_sprint.get("attributes", {}).get("startDate"),
                "end_date": current_sprint.get("attributes", {}).get("finishDate"),
                "state": current_sprint.get("attributes", {}).get("timeFrame"),
            }
            
            # Query sprint work items
            wiql = f'''
                SELECT [System.Id], [System.Title], [System.State]
                FROM workitems
                WHERE [System.TeamProject] = '{self.project}'
                    AND [System.IterationPath] UNDER '{sprint_id}'
                ORDER BY [System.Id]
            '''
            
            items_response = self.client.query_work_items(wiql, top=100)
            work_items = []
            if items_response.is_success and items_response.data:
                for item_ref in items_response.data.get("workItems", [])[:10]:
                    item_response = self.client.get_work_item(item_ref["id"])
                    if item_response.is_success:
                        item = self._parse_work_item(item_response.data)
                        if item:
                            work_items.append(item)
            
            return QueryResult(
                success=True,
                data={
                    "sprint": sprint_data,
                    "work_items": [item.to_dict() for item in work_items],
                    "summary": self._create_sprint_summary(sprint_data, work_items)
                }
            )
        
        except Exception as e:
            self.logger.error(f"Sprint query failed: {str(e)}")
            return QueryResult(success=False, error=str(e))
    
    def _build_wiql(self, parsed_query: ParsedQuery) -> str:
        """Build WIQL (Work Item Query Language) query"""
        conditions = [f"[System.TeamProject] = '{self.project}'"]
        
        # Handle different query intents
        if "complete" in parsed_query.raw_query.lower() or "done" in parsed_query.raw_query.lower():
            conditions.append("[System.State] = 'Closed'")
        elif "open" in parsed_query.raw_query.lower():
            conditions.append("[System.State] IN ('New', 'Active')")
        
        # Apply time filter
        if parsed_query.time_range:
            if parsed_query.time_range.start:
                start_date = parsed_query.time_range.start.strftime("%Y-%m-%d")
                conditions.append(f"[System.ChangedDate] >= '{start_date}'")
        
        # Apply filters
        for f in parsed_query.filters:
            if f.field == "assignee":
                conditions.append(f"[System.AssignedTo] = '{f.value}'")
            elif f.field == "status":
                conditions.append(f"[System.State] = '{f.value.capitalize()}'")
        
        wiql = f"SELECT [System.Id], [System.Title], [System.State] FROM workitems WHERE {' AND '.join(conditions)}"
        return wiql
    
    def _parse_work_item(self, item_data: Dict[str, Any]) -> Optional[WorkItem]:
        """Parse work item from API response"""
        try:
            fields = item_data.get("fields", {})
            return WorkItem(
                id=item_data.get("id"),
                title=fields.get("System.Title", ""),
                type=fields.get("System.WorkItemType", ""),
                state=fields.get("System.State", ""),
                assigned_to=fields.get("System.AssignedTo", {}).get("displayName"),
                created_date=fields.get("System.CreatedDate"),
                closed_date=fields.get("Microsoft.VSTS.Common.ClosedDate"),
                tags=fields.get("System.Tags", "").split(";") if fields.get("System.Tags") else [],
                effort=fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
                priority=fields.get("Microsoft.VSTS.Common.Priority"),
                url=item_data.get("url")
            )
        except Exception as e:
            self.logger.debug(f"Failed to parse work item: {str(e)}")
            return None
    
    def _calculate_work_item_metrics(self, items: List[WorkItem], query: ParsedQuery) -> Dict[str, Any]:
        """Calculate metrics from work items"""
        total_effort = sum(item.effort or 0 for item in items)
        metrics = {
            "total_items": len(items),
            "by_state": {},
            "by_type": {},
            "total_effort": total_effort,
        }
        
        # Count by state
        for item in items:
            state = item.state
            metrics["by_state"][state] = metrics["by_state"].get(state, 0) + 1
            
            type_ = item.type
            metrics["by_type"][type_] = metrics["by_type"].get(type_, 0) + 1
        
        return metrics
    
    def _create_work_item_summary(self, items: List[WorkItem], metrics: Dict[str, Any]) -> str:
        """Create summary text"""
        if not items:
            return "No work items found."
        
        summary = f"Found {metrics['total_items']} work item(s)."
        
        if metrics["by_state"]:
            states = ", ".join([f"{count} {state}" for state, count in metrics["by_state"].items()])
            summary += f" Status: {states}."
        
        if metrics["total_effort"] > 0:
            summary += f" Total effort: {metrics['total_effort']} points."
        
        return summary
    
    def _find_current_sprint(self, sprints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the current or most recent active sprint"""
        for sprint in sprints:
            state = sprint.get("attributes", {}).get("timeFrame")
            if state in ["current", "inProgress"]:
                return sprint
        
        # Fallback to most recent
        return sprints[0] if sprints else None
    
    def _create_sprint_summary(self, sprint: Dict[str, Any], items: List[WorkItem]) -> str:
        """Create sprint summary"""
        summary = f"Sprint: {sprint.get('name', 'Unknown')}\n"
        summary += f"Status: {sprint.get('state', 'Unknown')}\n"
        summary += f"Work Items: {len(items)}\n"
        
        completed = sum(1 for item in items if item.state == "Closed")
        summary += f"Completed: {completed}/{len(items)}"
        
        return summary

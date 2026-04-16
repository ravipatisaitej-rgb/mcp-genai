"""
Confluence MCP Tool
Searches and aggregates content from Confluence pages with intelligent summarization.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from html.parser import HTMLParser
import re

from services.base import BaseTool, BaseAPIClient, QueryResult, APIResponse
from utils.query_parser import parse_query, ParsedQuery
from utils.logging_config import ToolLogger
from utils.exceptions import ConfigurationError


@dataclass
class ConfluencePage:
    """Confluence page representation"""
    id: str
    title: str
    url: str
    space_key: str
    content: str
    version: int
    updated_by: str
    last_updated: str
    labels: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "space_key": self.space_key,
            "updated_by": self.updated_by,
            "last_updated": self.last_updated,
            "labels": self.labels,
        }


class HTMLStripper(HTMLParser):
    """Strip HTML tags from content"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_data(self):
        return ''.join(self.text).strip()


class ConfluenceAPIClient(BaseAPIClient):
    """Confluence API client"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        super().__init__("confluence")
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        import base64
        credentials = base64.b64encode(f"{self.username}:{self.api_token}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    
    def _get_base_url(self) -> str:
        return f"{self.base_url}/rest/api/2"
    
    def search_pages(self, cql: str, limit: int = 25) -> APIResponse:
        """Search for pages using CQL (Confluence Query Language)"""
        params = {
            "cql": cql,
            "limit": min(limit, 100),
            "expand": "body.storage,metadata.labels"
        }
        return self._make_request("GET", "/search", params=params)
    
    def get_page_content(self, page_id: str) -> APIResponse:
        """Get full content of a page"""
        return self._make_request(
            "GET",
            f"/content/{page_id}",
            params={"expand": "body.storage,children.page,metadata.labels"}
        )
    
    def get_space_pages(self, space_key: str, limit: int = 25) -> APIResponse:
        """Get pages in a specific space"""
        cql = f'space = "{space_key}" ORDER BY updated DESC'
        return self.search_pages(cql, limit)


class ConfluenceTool(BaseTool):
    """
    Confluence tool for searching and aggregating documentation.
    """
    
    def __init__(self, base_url: str, username: str, api_token: str):
        super().__init__("confluence")
        self.client = ConfluenceAPIClient(base_url, username, api_token)
        self.base_url = base_url.rstrip('/')
    
    def validate(self) -> bool:
        """Test Confluence connection"""
        try:
            response = self.client._make_request("GET", "/space")
            return response.is_success
        except Exception as e:
            self.logger.error(f"Confluence validation failed: {str(e)}")
            return False
    
    def execute(self, query: str) -> QueryResult:
        """
        Execute a Confluence search query.
        
        Args:
            query: Natural language query (e.g., "Find onboarding steps for data pipeline")
        
        Returns:
            QueryResult with aggregated content
        """
        try:
            parsed_query = parse_query(query)
            self.logger.info(f"Parsed query: intent={parsed_query.intent}, entity={parsed_query.primary_entity}")
            
            # Build CQL query
            cql = self._build_cql(parsed_query)
            
            # Search for pages
            result = self._search_and_aggregate(cql, parsed_query)
            
            return QueryResult(
                success=True,
                data=result,
                metadata={
                    "query_confidence": parsed_query.confidence,
                    "pages_found": len(result.get("pages", [])),
                    "cql_used": cql
                }
            )
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    def _build_cql(self, parsed_query: ParsedQuery) -> str:
        """Build Confluence Query Language (CQL) from parsed query"""
        conditions = []
        
        # Text search
        if parsed_query.keywords:
            keyword_search = " OR ".join(f'text ~ "{k}"' for k in parsed_query.keywords)
            conditions.append(f"({keyword_search})")
        
        # Space filter if specified
        if len(parsed_query.keywords) > 0:
            # Try to infer space from keywords (common pattern: space:KEY)
            space_match = next((k for k in parsed_query.keywords if k.isupper()), None)
            if space_match:
                conditions.append(f'space = "{space_match}"')
        
        # Add ordering
        cql = " AND ".join(conditions) if conditions else "type = page"
        cql += " ORDER BY updated DESC"
        
        return cql
    
    def _search_and_aggregate(self, cql: str, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Search and aggregate content from multiple pages"""
        try:
            # Execute search
            response = self.client.search_pages(
                cql,
                limit=parsed_query.limit or 10
            )
            
            if not response.is_success or not response.data:
                return {
                    "pages": [],
                    "summary": "No results found",
                    "aggregation": None
                }
            
            search_results = response.data.get("results", [])
            pages = []
            
            for page_data in search_results:
                page = self._parse_page_result(page_data)
                if page:
                    pages.append(page)
            
            # Aggregate results
            aggregation = self._aggregate_pages(pages, parsed_query) if pages else None
            
            return {
                "pages": [p.to_dict() for p in pages],
                "summary": self._create_summary(pages, parsed_query),
                "aggregation": aggregation
            }
        
        except Exception as e:
            self.logger.error(f"Search and aggregation failed: {str(e)}")
            return {
                "pages": [],
                "summary": f"Error during search: {str(e)}",
                "aggregation": None
            }
    
    def _parse_page_result(self, page_data: Dict[str, Any]) -> Optional[ConfluencePage]:
        """Parse a page from search results"""
        try:
            content_data = page_data.get("content", {})
            metadata = page_data.get("metadata", {})
            
            # Extract text content
            storage = content_data.get("storage", {})
            html_content = storage.get("value", "")
            text_content = self._strip_html(html_content)
            text_content = text_content[:500]  # Limit to first 500 chars
            
            return ConfluencePage(
                id=content_data.get("id"),
                title=content_data.get("title", "Untitled"),
                url=content_data.get("_links", {}).get("webui", ""),
                space_key=content_data.get("space", {}).get("key", ""),
                content=text_content,
                version=content_data.get("version", {}).get("number", 0),
                updated_by=content_data.get("version", {}).get("by", {}).get("displayName", "Unknown"),
                last_updated=content_data.get("version", {}).get("when", ""),
                labels=[l.get("name") for l in metadata.get("labels", [])]
            )
        except Exception as e:
            self.logger.debug(f"Failed to parse page: {str(e)}")
            return None
    
    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content"""
        try:
            stripper = HTMLStripper()
            stripper.feed(html)
            return stripper.get_data()
        except:
            # Fallback regex approach
            clean = re.sub(r'<[^>]+>', '', html)
            clean = re.sub(r'&nbsp;', ' ', clean)
            clean = re.sub(r'&quot;', '"', clean)
            return clean
    
    def _aggregate_pages(self, pages: List[ConfluencePage], parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Aggregate information from multiple pages"""
        aggregation = {
            "total_pages": len(pages),
            "unique_labels": list(set(l for p in pages for l in p.labels)),
            "most_recent": pages[0].last_updated if pages else None,
            "unique_updaters": list(set(p.updated_by for p in pages)),
        }
        
        if parsed_query.aggregation == "count":
            aggregation["count"] = len(pages)
        
        return aggregation
    
    def _create_summary(self, pages: List[ConfluencePage], parsed_query: ParsedQuery) -> str:
        """Create a natural language summary of results"""
        if not pages:
            return "No matching pages found."
        
        summary = f"Found {len(pages)} page(s). "
        
        titles = [f'"{p.title}"' for p in pages[:3]]
        summary += f"Top results: {', '.join(titles)}"
        
        if len(pages) > 3:
            summary += f", and {len(pages) - 3} more."
        
        return summary

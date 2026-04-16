"""
AWS CloudWatch Logs MCP Tool
Queries logs, identifies errors, and performs pattern analysis.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter
import re

from services.base import BaseTool, QueryResult
from utils.query_parser import parse_query, ParsedQuery, TimeRange
from utils.logging_config import ToolLogger
from utils.exceptions import ConfigurationError


@dataclass
class LogEvent:
    """CloudWatch log event"""
    timestamp: int
    message: str
    log_stream: str
    log_group: str
    level: Optional[str] = None  # ERROR, WARN, INFO, DEBUG
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp/1000).isoformat(),
            "message": self.message,
            "log_stream": self.log_stream,
            "log_group": self.log_group,
            "level": self.level,
        }


@dataclass
class LogAnalysis:
    """Analysis results from logs"""
    total_events: int
    log_level_distribution: Dict[str, int] = field(default_factory=dict)
    error_patterns: List[Dict[str, Any]] = field(default_factory=list)
    top_errors: List[str] = field(default_factory=list)
    time_range: Dict[str, str] = field(default_factory=dict)
    affected_streams: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "log_level_distribution": self.log_level_distribution,
            "error_patterns": self.error_patterns,
            "top_errors": self.top_errors[:5],
            "affected_streams": list(set(self.affected_streams)),
        }


class CloudWatchTool(BaseTool):
    """
    CloudWatch Logs tool for error analysis and log queries.
    """
    
    def __init__(self, region: str, access_key_id: str, secret_access_key: str):
        super().__init__("cloudwatch")
        
        try:
            import boto3
            self.boto3 = boto3
        except ImportError:
            raise ConfigurationError("boto3 is required for CloudWatch tool. Install with: pip install boto3")
        
        self.region = region
        self.client = boto3.client(
            "logs",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        self.cloudwatch = boto3.client(
            "cloudwatch",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
    
    def validate(self) -> bool:
        """Test CloudWatch connection"""
        try:
            self.client.describe_log_groups(limit=1)
            return True
        except Exception as e:
            self.logger.error(f"CloudWatch validation failed: {str(e)}")
            return False
    
    def execute(self, query: str) -> QueryResult:
        """
        Execute a CloudWatch logs query.
        
        Examples:
            - "Show errors in last 2 hours"
            - "Find logs related to API failure"
            - "Analyze error patterns in /aws/lambda/function_name"
        """
        try:
            parsed_query = parse_query(query)
            self.logger.info(f"Parsed query: intent={parsed_query.intent}, entity={parsed_query.primary_entity}")
            
            # Determine log group(s)
            log_groups = self._find_log_groups(parsed_query)
            
            if not log_groups:
                return QueryResult(
                    success=False,
                    error="No log groups found matching the query"
                )
            
            if not parsed_query.time_range:
                parsed_query.time_range = TimeRange.from_lookback(1)
            
            # Query logs
            events = self._query_logs(log_groups, parsed_query)
            
            # Analyze events
            analysis = self._analyze_logs(events, parsed_query)
            
            return QueryResult(
                success=True,
                data={
                    "analysis": analysis.to_dict(),
                    "sample_events": [e.to_dict() for e in events[:10]],
                    "log_groups": log_groups,
                    "summary": self._create_summary(analysis)
                },
                metadata={
                    "query_confidence": parsed_query.confidence,
                    "events_analyzed": len(events),
                    "time_range": parsed_query.time_range.to_dict()
                }
            )
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    def _find_log_groups(self, parsed_query: ParsedQuery) -> List[str]:
        """Find relevant log groups based on query"""
        try:
            response = self.client.describe_log_groups()
            all_groups = [g["logGroupName"] for g in response.get("logGroups", [])]
            
            # Filter based on keywords
            if parsed_query.keywords:
                filtered = []
                for keyword in parsed_query.keywords:
                    matching = [
                        g for g in all_groups 
                        if keyword.lower() in g.lower()
                    ]
                    filtered.extend(matching)
                return list(set(filtered)) or all_groups[:5]
            
            return all_groups[:5]  # Default to first 5
        except Exception as e:
            self.logger.error(f"Failed to find log groups: {str(e)}")
            return []
    
    def _query_logs(self, log_groups: List[str], parsed_query: ParsedQuery) -> List[LogEvent]:
        """Query logs from CloudWatch"""
        try:
            events = []
            end_time = int(datetime.utcnow().timestamp() * 1000)
            
            if parsed_query.time_range and parsed_query.time_range.start:
                start_time = int(parsed_query.time_range.start.timestamp() * 1000)
            else:
                start_time = end_time - (24 * 60 * 60 * 1000)  # Last 24 hours
            
            # Build filter pattern based on parsed query
            filter_pattern = self._build_filter_pattern(parsed_query)
            
            for log_group in log_groups[:3]:  # Limit to 3 log groups per query
                try:
                    response = self.client.filter_log_events(
                        logGroupName=log_group,
                        startTime=start_time,
                        endTime=end_time,
                        filterPattern=filter_pattern,
                        limit=min(parsed_query.limit or 100, 1000)
                    )
                    
                    for event in response.get("events", []):
                        level = self._extract_log_level(event["message"])
                        events.append(LogEvent(
                            timestamp=event["timestamp"],
                            message=event["message"],
                            log_stream=event["logStreamName"],
                            log_group=log_group,
                            level=level
                        ))
                
                except Exception as e:
                    self.logger.debug(f"Error querying {log_group}: {str(e)}")
            
            # Sort by timestamp, most recent first
            events.sort(key=lambda x: x.timestamp, reverse=True)
            return events[:parsed_query.limit or 100]
        
        except Exception as e:
            self.logger.error(f"Log query failed: {str(e)}")
            return []
    
    def _build_filter_pattern(self, parsed_query: ParsedQuery) -> str:
        """Build CloudWatch filter pattern"""
        patterns = []
        
        # Add error/warning level patterns
        if "error" in parsed_query.primary_entity or "error" in parsed_query.raw_query.lower():
            patterns.append('[... level = ERROR ...]')
            patterns.append('[msg="*Error*"]')
            patterns.append('[msg="*Exception*"]')
        elif "warn" in parsed_query.raw_query.lower():
            patterns.append('[... level = WARN ...]')
        
        # Add keyword patterns
        for keyword in parsed_query.keywords[:3]:
            patterns.append(f'[... msg="*{keyword}*" ...]')
        
        if patterns:
            return '{' + ', '.join(patterns) + '}'
        
        return ''  # Empty pattern matches all
    
    def _extract_log_level(self, message: str) -> Optional[str]:
        """Extract log level from message"""
        level_patterns = {
            "ERROR": r"\bERROR\b|\bFATAL\b",
            "WARN": r"\bWARN\b|\bWARNING\b",
            "INFO": r"\bINFO\b",
            "DEBUG": r"\bDEBUG\b",
        }
        
        for level, pattern in level_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                return level
        
        return None
    
    def _analyze_logs(self, events: List[LogEvent], parsed_query: ParsedQuery) -> LogAnalysis:
        """Analyze logs for patterns and anomalies"""
        analysis = LogAnalysis(total_events=len(events))
        
        if not events:
            return analysis
        
        # Count by log level
        levels = Counter(e.level for e in events if e.level)
        analysis.log_level_distribution = dict(levels)
        
        # Extract affected streams
        analysis.affected_streams = list(set(e.log_stream for e in events))
        
        # Find error patterns
        error_events = [e for e in events if e.level == "ERROR"]
        error_messages = [e.message for e in error_events]
        analysis.top_errors = self._extract_top_errors(error_messages)
        
        # Find patterns
        analysis.error_patterns = self._find_error_patterns(error_events)
        
        # Time range
        if events:
            analysis.time_range = {
                "earliest": datetime.fromtimestamp(events[-1].timestamp/1000).isoformat(),
                "latest": datetime.fromtimestamp(events[0].timestamp/1000).isoformat(),
            }
        
        return analysis
    
    def _extract_top_errors(self, messages: List[str]) -> List[str]:
        """Extract unique error message patterns"""
        # Normalize messages (remove IDs, timestamps, etc.)
        patterns = []
        for msg in messages:
            # Remove common variable parts
            normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', msg)
            normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}', '[ID]', normalized)
            normalized = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', normalized)
            patterns.append(normalized[:100])  # First 100 chars
        
        # Count occurrences
        pattern_counts = Counter(patterns)
        return [pattern for pattern, _ in pattern_counts.most_common(10)]
    
    def _find_error_patterns(self, errors: List[LogEvent]) -> List[Dict[str, Any]]:
        """Find recurring error patterns and their frequency"""
        patterns = []
        
        # Group by error type
        error_types = {}
        for event in errors:
            # Extract first line which usually has the error type
            first_line = event.message.split('\n')[0]
            if first_line not in error_types:
                error_types[first_line] = []
            error_types[first_line].append(event)
        
        # Create pattern summaries
        for error_type, events in sorted(
            error_types.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]:
            patterns.append({
                "error_type": error_type[:200],
                "count": len(events),
                "affected_streams": list(set(e.log_stream for e in events)),
                "latest_occurrence": datetime.fromtimestamp(events[0].timestamp/1000).isoformat()
            })
        
        return patterns
    
    def _create_summary(self, analysis: LogAnalysis) -> str:
        """Create human-readable summary"""
        if analysis.total_events == 0:
            return "No log events found in the specified time range."
        
        summary = f"Found {analysis.total_events} log event(s) "
        
        if analysis.log_level_distribution:
            levels = ", ".join([
                f"{count} {level}" 
                for level, count in analysis.log_level_distribution.items()
            ])
            summary += f"({levels})."
        
        if analysis.top_errors:
            summary += f" Top error: {analysis.top_errors[0][:150]}"
            if len(analysis.top_errors) > 1:
                summary += f"... and {len(analysis.top_errors)-1} more patterns."
        
        return summary

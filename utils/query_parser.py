from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
import re
from utils.exceptions import QueryParseError
from utils.logging_config import ToolLogger


class TimeUnit(Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


class FilterOperator(Enum):
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    CONTAINS = "contains"
    STARTS_WITH = "startswith"
    IN = "in"


@dataclass
class TimeRange:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    lookback_days: Optional[int] = None

    @classmethod
    def from_lookback(cls, days: int) -> "TimeRange":
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        return cls(start=start, end=end, lookback_days=days)

    def to_dict(self) -> Dict[str, str]:
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None
        }


@dataclass
class Filter:
    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "case_sensitive": self.case_sensitive
        }


@dataclass
class ParsedQuery:
    raw_query: str
    intent: str
    primary_entity: str
    filters: List[Filter] = field(default_factory=list)
    time_range: Optional[TimeRange] = None
    limit: Optional[int] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    aggregation: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "primary_entity": self.primary_entity,
            "filters": [f.to_dict() for f in self.filters],
            "time_range": self.time_range.to_dict() if self.time_range else None,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "aggregation": self.aggregation,
            "keywords": self.keywords,
            "confidence": self.confidence
        }


class QueryParser:
    INTENT_PATTERNS = {
        "search": [r"search\s+for", r"find", r"show", r"get", r"retrieve"],
        "list": [r"list\s+all", r"show\s+all", r"list", r"all\s+\w+"],
        "count": [r"how\s+many", r"count\s+", r"total\s+\w+"],
        "analyze": [r"analyze", r"what\s+\w+about", r"why", r"pattern"],
        "filter": [r"with\s+", r"that\s+(?:are|is)", r"where", r"filtered\s+by"],
        "group": [r"group\s+by", r"grouped\s+by"],
        "sort": [r"sort\s+by", r"ordered\s+by", r"sorted\s+by"],
    }

    TIME_PATTERNS = {
        r"last\s+(\d+)\s+(hour|hours)": (TimeUnit.HOURS, 1),
        r"last\s+(\d+)\s+(day|days)": (TimeUnit.DAYS, 1),
        r"last\s+(\d+)\s+(week|weeks)": (TimeUnit.WEEKS, 7),
        r"last\s+(\d+)\s+(month|months)": (TimeUnit.MONTHS, 30),
        r"past\s+(\d+)\s+(hour|hours)": (TimeUnit.HOURS, 1),
        r"past\s+(\d+)\s+(day|days)": (TimeUnit.DAYS, 1),
        r"(\d+)\s+(hour|hours)\s+ago": (TimeUnit.HOURS, 1),
        r"(\d+)\s+(day|days)\s+ago": (TimeUnit.DAYS, 1),
        r"today": (TimeUnit.DAYS, 0),
        r"this\s+week": (TimeUnit.WEEKS, 7),
        r"this\s+month": (TimeUnit.MONTHS, 30),
    }

    STATUS_PATTERNS = {
        "open": ["open", "active", "pending", "todo"],
        "closed": ["closed", "done", "complete", "resolved"],
        "failed": ["failed", "failure", "error"],
        "success": ["success", "succeeded", "passed"],
        "in_progress": ["in progress", "running", "in-progress"],
    }

    def __init__(self):
        self.logger = ToolLogger("QueryParser")

    def parse(self, query: str) -> ParsedQuery:
        clean = query.lower().strip()

        intent = self._detect_intent(clean)
        primary_entity = self._extract_primary_entity(clean)
        time_range = self._extract_time_range(clean)
        filters = self._extract_filters(clean)
        sort_by, sort_order = self._extract_sorting(clean)
        limit = self._extract_limit(clean)
        aggregation = self._extract_aggregation(clean)
        keywords = self._extract_keywords(clean, filters, time_range)
        confidence = self._calculate_confidence(intent, primary_entity, filters)

        return ParsedQuery(
            raw_query=query,
            intent=intent,
            primary_entity=primary_entity,
            filters=filters,
            time_range=time_range,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            aggregation=aggregation,
            keywords=keywords,
            confidence=confidence
        )

    def _detect_intent(self, query: str) -> str:
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(re.search(p, query) for p in patterns):
                return intent
        return "search"

    def _extract_primary_entity(self, query: str) -> str:
        entities = {
            r"\b(error|errors|failures|logs)\b": "errors",
            r"\b(log|logs)\b": "logs",
            r"\b(work\s+item|work\s+items|task|tasks|issue|issues)\b": "work_items",
            r"\b(build|builds|pipeline|pipelines|workflow|workflows)\b": "builds",
            r"\b(page|pages|document|documents)\b": "pages",
            r"\b(table|tables|data|query|queries)\b": "data",
            r"\b(metric|metrics|anomal|anomalies)\b": "metrics",
        }
        for pattern, entity in entities.items():
            if re.search(pattern, query):
                return entity
        return "items"

    def _extract_time_range(self, query: str) -> Optional[TimeRange]:
        for pattern, (unit, multiplier) in self.TIME_PATTERNS.items():
            match = re.search(pattern, query)
            if match:
                if match.groups():
                    return TimeRange.from_lookback(int(match.group(1)) * multiplier)
                else:
                    return TimeRange.from_lookback(multiplier)
        return None

    def _extract_filters(self, query: str) -> List[Filter]:
        filters = []

        for status_value, keywords in self.STATUS_PATTERNS.items():
            for keyword in keywords:
                if keyword in query:
                    filters.append(Filter(field="status", operator=FilterOperator.EQUALS, value=status_value))
                    break

        user_match = re.search(r"(?:by|for|from)\s+(?:@)?(\w+)", query)
        if user_match:
            filters.append(Filter(field="assignee", operator=FilterOperator.EQUALS, value=user_match.group(1)))

        for comp, number in re.findall(r"(more|less|over|under|greater|fewer)\s+than\s+(\d+)", query):
            op = FilterOperator.GREATER_THAN if comp in ["more", "over", "greater"] else FilterOperator.LESS_THAN
            filters.append(Filter(field="count", operator=op, value=int(number)))

        return filters

    def _extract_sorting(self, query: str) -> Tuple[Optional[str], str]:
        sort_by = None
        sort_order = "desc"

        sort_match = re.search(r"(?:sort|order)\s+by\s+(\w+)\s+(?:asc|ascending|desc|descending)?", query)
        if sort_match:
            sort_by = sort_match.group(1)
            if "asc" in query:
                sort_order = "asc"

        if "oldest" in query:
            sort_order = "asc"
        elif "newest" in query:
            sort_order = "desc"

        return sort_by, sort_order

    def _extract_limit(self, query: str) -> Optional[int]:
        match = re.search(r"(?:top|first|last|limit|show)\s+(\d+)", query)
        if match:
            return int(match.group(1))
        match = re.search(r"top\s+(\d+)", query)
        if match:
            return int(match.group(1))
        return None

    def _extract_aggregation(self, query: str) -> Optional[str]:
        aggregations = {
            r"\bcount\b": "count",
            r"\bsum\b": "sum",
            r"\baverage\b": "average",
            r"\bavg\b": "average",
            r"\bmax\b": "max",
            r"\bmin\b": "min",
            r"\btotal\b": "sum",
        }
        for pattern, agg in aggregations.items():
            if re.search(pattern, query):
                return agg
        return None

    def _extract_keywords(self, query: str, filters: List[Filter], time_range: Optional[TimeRange]) -> List[str]:
        stop_words = {"show", "get", "find", "search", "for", "the", "a", "an", "last", "this", "that"}
        cleaned = re.sub(r"(?:last|past|ago|today|this)\s+\w+", "", query)
        cleaned = re.sub(r"(?:sort|order)\s+by\s+\w+", "", cleaned)
        cleaned = re.sub(r"(?:with|where|by|from)\s+\w+", "", cleaned)
        words = [w for w in re.findall(r"\w+", cleaned.lower()) if w not in stop_words and len(w) > 3]
        return list(dict.fromkeys(words))[:5]

    def _calculate_confidence(self, intent: str, entity: str, filters: List[Filter]) -> float:
        confidence = 0.7
        if intent != "search":
            confidence += 0.1
        if entity != "items":
            confidence += 0.1
        confidence += min(0.1, len(filters) * 0.05)
        return min(1.0, confidence)


def parse_query(query: str) -> ParsedQuery:
    return QueryParser().parse(query)

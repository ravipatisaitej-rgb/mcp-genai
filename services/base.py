from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
import time
import backoff
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from utils.exceptions import APIError, AuthenticationError, RateLimitError, TimeoutError as MCPTimeoutError
from utils.logging_config import ToolLogger

T = TypeVar("T")


@dataclass
class APIResponse:
    status_code: int
    data: Any = None
    error: Optional[str] = None
    raw_response: Optional[requests.Response] = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600


@dataclass
class RateLimitInfo:
    limit: int = 0
    remaining: int = 0
    reset_at: Optional[datetime] = None

    def should_backoff(self) -> bool:
        return self.remaining < 5 and self.reset_at is not None


class BaseAPIClient(ABC):
    def __init__(self, service_name: str, logger: Optional[ToolLogger] = None):
        self.service_name = service_name
        self.logger = logger or ToolLogger(service_name)
        self.session = self._create_session()
        self._rate_limit_info: Dict[str, RateLimitInfo] = {}

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def _get_base_url(self) -> str:
        pass

    def _get_default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": f"mcp-tools/{self.service_name}",
            "Accept": "application/json",
            **self._get_auth_headers()
        }

    def _extract_rate_limit_info(self, response: requests.Response, endpoint: str = "default") -> None:
        limit = response.headers.get("X-RateLimit-Limit") or response.headers.get("ratelimit-limit")
        remaining = response.headers.get("X-RateLimit-Remaining") or response.headers.get("ratelimit-remaining")
        reset = response.headers.get("X-RateLimit-Reset") or response.headers.get("ratelimit-reset")

        if limit and remaining:
            try:
                reset_at = None
                if reset:
                    reset_at = datetime.fromtimestamp(int(reset)) if reset.isdigit() else datetime.fromisoformat(reset)
                self._rate_limit_info[endpoint] = RateLimitInfo(
                    limit=int(limit),
                    remaining=int(remaining),
                    reset_at=reset_at
                )
            except (ValueError, TypeError):
                pass

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3, jitter=backoff.full_jitter)
    def _make_request(self, method: str, endpoint: str, timeout: int = 30, **kwargs) -> APIResponse:
        url = f"{self._get_base_url()}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._get_default_headers())

        rate_limit = self._rate_limit_info.get("default")
        if rate_limit and rate_limit.should_backoff():
            sleep_time = (rate_limit.reset_at - datetime.now()).total_seconds() + 1
            self.logger.warning(f"Rate limit approaching, backing off for {sleep_time:.0f}s")
            time.sleep(max(1, sleep_time))

        try:
            self.logger.debug(f"{method} {endpoint}")
            response = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
            self._extract_rate_limit_info(response, endpoint)

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed",
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )
            elif response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded",
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )
            elif response.status_code >= 400:
                raise APIError(
                    f"API error: {response.status_code}",
                    status_code=response.status_code,
                    response=response.json() if response.text else None
                )

            return APIResponse(
                status_code=response.status_code,
                data=response.json() if response.text else None,
                raw_response=response
            )

        except requests.exceptions.Timeout:
            raise MCPTimeoutError(f"Request to {endpoint} timed out after {timeout}s")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}", response=str(e))

    def close(self):
        self.session.close()


@dataclass
class QueryResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    raw_api_response: Optional[APIResponse] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = ToolLogger(name)

    @abstractmethod
    def validate(self) -> bool:
        pass

    @abstractmethod
    def execute(self, query: str) -> QueryResult:
        pass

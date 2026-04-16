import os
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ConfluenceConfig:
    url: str
    username: str
    api_token: str
    verify_ssl: bool = True
    timeout: int = 10


@dataclass
class AzureBoardsConfig:
    organization: str
    project: str
    pat_token: str
    verify_ssl: bool = True
    timeout: int = 10


@dataclass
class AWSConfig:
    region: str
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None


@dataclass
class GitHubConfig:
    token: str
    owner: str
    repo: str
    verify_ssl: bool = True
    timeout: int = 10


@dataclass
class SnowflakeConfig:
    account: str
    user: str
    password: str
    database: str
    schema: str
    warehouse: str
    role: str


@dataclass
class AppConfig:
    debug: bool = False
    log_level: str = "INFO"
    confluence: Optional[ConfluenceConfig] = None
    azure_boards: Optional[AzureBoardsConfig] = None
    aws: Optional[AWSConfig] = None
    github: Optional[GitHubConfig] = None
    snowflake: Optional[SnowflakeConfig] = None


def _load_confluence() -> Optional[ConfluenceConfig]:
    if not os.getenv("CONFLUENCE_URL"):
        return None
    return ConfluenceConfig(
        url=os.getenv("CONFLUENCE_URL"),
        username=os.getenv("CONFLUENCE_USERNAME"),
        api_token=os.getenv("CONFLUENCE_API_TOKEN"),
        verify_ssl=os.getenv("CONFLUENCE_VERIFY_SSL", "true").lower() == "true",
        timeout=int(os.getenv("CONFLUENCE_TIMEOUT", "10"))
    )


def _load_azure_boards() -> Optional[AzureBoardsConfig]:
    if not os.getenv("AZURE_ORGANIZATION"):
        return None
    return AzureBoardsConfig(
        organization=os.getenv("AZURE_ORGANIZATION"),
        project=os.getenv("AZURE_PROJECT"),
        pat_token=os.getenv("AZURE_PAT_TOKEN"),
        verify_ssl=os.getenv("AZURE_VERIFY_SSL", "true").lower() == "true",
        timeout=int(os.getenv("AZURE_TIMEOUT", "10"))
    )


def _load_aws() -> Optional[AWSConfig]:
    if not os.getenv("AWS_REGION"):
        return None
    return AWSConfig(
        region=os.getenv("AWS_REGION"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        session_token=os.getenv("AWS_SESSION_TOKEN")
    )


def _load_github() -> Optional[GitHubConfig]:
    if not os.getenv("GITHUB_TOKEN"):
        return None
    return GitHubConfig(
        token=os.getenv("GITHUB_TOKEN"),
        owner=os.getenv("GITHUB_OWNER"),
        repo=os.getenv("GITHUB_REPO"),
        verify_ssl=os.getenv("GITHUB_VERIFY_SSL", "true").lower() == "true",
        timeout=int(os.getenv("GITHUB_TIMEOUT", "10"))
    )


def _load_snowflake() -> Optional[SnowflakeConfig]:
    if not os.getenv("SNOWFLAKE_ACCOUNT"):
        return None
    return SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    return AppConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        confluence=_load_confluence(),
        azure_boards=_load_azure_boards(),
        aws=_load_aws(),
        github=_load_github(),
        snowflake=_load_snowflake()
    )

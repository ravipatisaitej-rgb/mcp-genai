"""
GitHub Actions MCP Tool
Analyzes workflow runs, identifies failures, and provides debugging insights.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import re

from services.base import BaseTool, BaseAPIClient, QueryResult, APIResponse
from utils.query_parser import parse_query, ParsedQuery
from utils.logging_config import ToolLogger


@dataclass
class WorkflowRun:
    """GitHub workflow run"""
    id: int
    name: str
    status: str
    conclusion: Optional[str]  # success, failure, skipped, cancelled
    branch: str
    commit_sha: str
    commit_message: Optional[str]
    author: str
    created_at: str
    updated_at: str
    html_url: str
    duration_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "branch": self.branch,
            "commit_sha": self.commit_sha[:8],
            "author": self.author,
            "created_at": self.created_at,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class JobDetail:
    """GitHub Actions job details"""
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    started_at: str
    completed_at: Optional[str]
    steps: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_steps": [s for s in self.steps if s.get("conclusion") == "failure"] if self.steps else []
        }


class GitHubAPIClient(BaseAPIClient):
    """GitHub API client"""
    
    def __init__(self, token: str, owner: str, repo: str):
        super().__init__("github_actions")
        self.token = token
        self.owner = owner
        self.repo = repo
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _get_base_url(self) -> str:
        return "https://api.github.com"
    
    def list_workflow_runs(self, workflow_id: str = None, limit: int = 10) -> APIResponse:
        """List recent workflow runs"""
        endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs"
        if workflow_id:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
        
        return self._make_request("GET", endpoint, params={"per_page": limit})
    
    def get_run_details(self, run_id: int) -> APIResponse:
        """Get details of a specific run"""
        return self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}"
        )
    
    def get_run_jobs(self, run_id: int) -> APIResponse:
        """Get jobs for a run"""
        return self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs",
            params={"per_page": 100}
        )
    
    def get_run_logs(self, run_id: int, job_id: int) -> APIResponse:
        """Get logs for a job"""
        return self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/actions/jobs/{job_id}/logs"
        )


class GitHubActionsTool(BaseTool):
    """
    GitHub Actions tool for CI/CD pipeline analysis.
    """
    
    def __init__(self, token: str, owner: str, repo: str):
        super().__init__("github_actions")
        self.client = GitHubAPIClient(token, owner, repo)
        self.owner = owner
        self.repo = repo
    
    def validate(self) -> bool:
        """Test GitHub connection"""
        try:
            response = self.client.list_workflow_runs(limit=1)
            return response.is_success
        except Exception as e:
            self.logger.error(f"GitHub validation failed: {str(e)}")
            return False
    
    def execute(self, query: str) -> QueryResult:
        """
        Execute a GitHub Actions query.
        
        Examples:
            - "Why did my last build fail?"
            - "Show recent pipeline runs"
            - "List failed builds on main branch"
        """
        try:
            parsed_query = parse_query(query)
            self.logger.info(f"Parsed query: intent={parsed_query.intent}")
            
            # Get recent runs
            runs_response = self.client.list_workflow_runs(limit=parsed_query.limit or 10)
            
            if not runs_response.is_success:
                return QueryResult(success=False, error="Failed to fetch workflow runs")
            
            runs = self._parse_runs(runs_response.data)
            
            # Filter based on query
            if "failed" in parsed_query.raw_query.lower():
                runs = [r for r in runs if r.conclusion == "failure"]
            elif "success" in parsed_query.raw_query.lower():
                runs = [r for r in runs if r.conclusion == "success"]
            
            # If looking for specific run details (last/latest)
            if "last" in parsed_query.raw_query.lower() and runs:
                target_run = runs[0]
                
                # Get jobs and logs
                jobs_response = self.client.get_run_jobs(target_run.id)
                jobs = self._parse_jobs(jobs_response.data) if jobs_response.is_success else []
                
                # Extract failure details
                failure_info = self._analyze_failures(target_run, jobs)
                
                return QueryResult(
                    success=True,
                    data={
                        "run": target_run.to_dict(),
                        "jobs": [j.to_dict() for j in jobs],
                        "failure_analysis": failure_info,
                        "summary": self._create_failure_summary(target_run, failure_info)
                    }
                )
            else:
                # Return list of recent runs
                return QueryResult(
                    success=True,
                    data={
                        "runs": [r.to_dict() for r in runs],
                        "summary": self._create_runs_summary(runs)
                    },
                    metadata={
                        "runs_found": len(runs),
                        "failures": sum(1 for r in runs if r.conclusion == "failure")
                    }
                )
        
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return QueryResult(success=False, error=str(e))
    
    def _parse_runs(self, data: Dict[str, Any]) -> List[WorkflowRun]:
        """Parse workflow runs from API response"""
        runs = []
        for run in data.get("workflow_runs", []):
            try:
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                duration = None
                if updated and created:
                    duration = int((updated - created).total_seconds())
                
                runs.append(WorkflowRun(
                    id=run["id"],
                    name=run["name"],
                    status=run["status"],
                    conclusion=run.get("conclusion"),
                    branch=run.get("head_branch", "unknown"),
                    commit_sha=run["head_commit"]["id"],
                    commit_message=run["head_commit"].get("message"),
                    author=run["actor"]["login"],
                    created_at=run["created_at"],
                    updated_at=run["updated_at"],
                    html_url=run["html_url"],
                    duration_seconds=duration
                ))
            except Exception as e:
                self.logger.debug(f"Failed to parse run: {str(e)}")
        
        return runs
    
    def _parse_jobs(self, data: Dict[str, Any]) -> List[JobDetail]:
        """Parse job details from API response"""
        jobs = []
        for job in data.get("jobs", []):
            try:
                steps = job.get("steps", [])
                job_detail = JobDetail(
                    id=job["id"],
                    name=job["name"],
                    status=job["status"],
                    conclusion=job.get("conclusion"),
                    started_at=job.get("started_at", ""),
                    completed_at=job.get("completed_at"),
                    steps=[{
                        "name": s["name"],
                        "number": s["number"],
                        "status": s["status"],
                        "conclusion": s.get("conclusion")
                    } for s in steps]
                )
                jobs.append(job_detail)
            except Exception as e:
                self.logger.debug(f"Failed to parse job: {str(e)}")
        
        return jobs
    
    def _analyze_failures(self, run: WorkflowRun, jobs: List[JobDetail]) -> Dict[str, Any]:
        """Analyze failure reasons"""
        analysis = {
            "failed_jobs": [],
            "root_causes": [],
            "recommendation": None
        }
        
        if run.conclusion != "failure":
            return analysis
        
        # Find failed jobs
        failed_jobs = [j for j in jobs if j.conclusion == "failure"]
        analysis["failed_jobs"] = [j.name for j in failed_jobs]
        
        # Analyze failure patterns
        for job in failed_jobs:
            failed_steps = [s for s in job.steps if s.get("conclusion") == "failure"]
            for step in failed_steps:
                cause = self._infer_failure_cause(step["name"])
                if cause:
                    analysis["root_causes"].append(cause)
        
        # Provide recommendation
        if analysis["root_causes"]:
            common_causes = list(set(analysis["root_causes"]))
            analysis["recommendation"] = f"Common issues: {', '.join(common_causes[:3])}"
        
        return analysis
    
    def _infer_failure_cause(self, step_name: str) -> Optional[str]:
        """Infer the likely cause of failure from step name"""
        patterns = {
            "test": "Test failures - check test output",
            "lint": "Linting errors - fix code style",
            "build": "Build failure - check compilation errors",
            "deploy": "Deployment failure - check permissions/resources",
            "auth": "Authentication failure - verify credentials",
            "security": "Security scan failure - address vulnerabilities",
        }
        
        for keyword, cause in patterns.items():
            if keyword.lower() in step_name.lower():
                return cause
        
        return None
    
    def _create_failure_summary(self, run: WorkflowRun, analysis: Dict[str, Any]) -> str:
        """Create summary of failure"""
        summary = f"Run '{run.name}' on {run.branch} failed.\n"
        
        if analysis["failed_jobs"]:
            jobs_str = ", ".join(analysis["failed_jobs"])
            summary += f"Failed jobs: {jobs_str}\n"
        
        if analysis["recommendation"]:
            summary += f"Recommendation: {analysis['recommendation']}"
        
        return summary
    
    def _create_runs_summary(self, runs: List[WorkflowRun]) -> str:
        """Create summary of recent runs"""
        if not runs:
            return "No workflow runs found."
        
        total = len(runs)
        success_count = sum(1 for r in runs if r.conclusion == "success")
        failure_count = sum(1 for r in runs if r.conclusion == "failure")
        
        summary = f"Found {total} run(s): {success_count} successful, {failure_count} failed."
        
        if failure_count > 0:
            latest_failure = next((r for r in runs if r.conclusion == "failure"), None)
            if latest_failure:
                summary += f" Latest failure: {latest_failure.name}"
        
        return summary

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from ..core.filters import Filter, should_include_key
from ..core.source import Source


@dataclass
class _GitHubContext:
    owner: str
    repo: str
    environment: str
    token: str


class GitHubEnvSource(Source):
    """GitHub Environment variables source (read/write variables; secrets are excluded).

    URI format: github://owner/repo#environment
    Token: from env var GITHUB_TOKEN unless provided explicitly via `token` arg.
    """

    def __init__(self, uri: str, name: Optional[str] = None, token: Optional[str] = None):
        self.uri = uri
        self.ctx = self._parse_uri(uri, token)
        self.name = name or f"github:{self.ctx.owner}/{self.ctx.repo}#{self.ctx.environment}"
        self.id = f"{self.ctx.owner}/{self.ctx.repo}#{self.ctx.environment}"
        self.extension = None
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.ctx.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    def _parse_uri(self, uri: str, token: Optional[str]) -> _GitHubContext:
        if not uri.startswith("github://"):
            raise ValueError("GitHubEnvSource requires URI starting with github://")
        rest = uri[len("github://") :]
        if "#" in rest:
            path, env = rest.split("#", 1)
        else:
            raise ValueError("GitHub URI must include #environment suffix, e.g., github://owner/repo#production")
        if "/" not in path:
            raise ValueError("GitHub URI path must be owner/repo")
        owner, repo = path.split("/", 1)
        token_val = token or os.getenv("GITHUB_TOKEN")
        if not token_val:
            raise EnvironmentError("GITHUB_TOKEN not set and token not provided for GitHubEnvSource")
        return _GitHubContext(owner=owner, repo=repo, environment=env, token=token_val)

    # ---- API helpers ----
    def _list_env_variables(self) -> Dict[str, str]:
        # Pagination support (simple loop)
        vars_all: Dict[str, str] = {}
        url = f"/repos/{self.ctx.owner}/{self.ctx.repo}/environments/{self.ctx.environment}/variables"
        page = 1
        while True:
            resp = self._client.get(url, params={"per_page": 100, "page": page})
            resp.raise_for_status()
            data = resp.json()
            for v in data.get("variables", []):
                vars_all[v["name"]] = v.get("value")
            if len(data.get("variables", [])) < 100:
                break
            page += 1
        return vars_all

    def _upsert_env_variable(self, name: str, value: str) -> None:
        url = f"/repos/{self.ctx.owner}/{self.ctx.repo}/environments/{self.ctx.environment}/variables/{name}"
        # Use PUT to create or update
        resp = self._client.put(url, json={"name": name, "value": value})
        if resp.status_code not in (200, 201):
            resp.raise_for_status()

    def _delete_env_variable(self, name: str) -> None:
        url = f"/repos/{self.ctx.owner}/{self.ctx.repo}/environments/{self.ctx.environment}/variables/{name}"
        resp = self._client.delete(url)
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    # ---- Source interface ----
    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        kv = self._list_env_variables()
        self._cache = kv
        if filter:
            return {k: v for k, v in self._cache.items() if should_include_key(k, filter)}
        return dict(self._cache)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._staged[key] = str(value)

    def unset(self, key: str) -> None:
        self._staged[key] = None

    def save(self) -> None:
        for k, v in self._staged.items():
            if v is None:
                self._delete_env_variable(k)
            else:
                self._upsert_env_variable(k, v)
        self._staged.clear()
        self.reload()

    def reload(self) -> None:
        self.load()

    def exists(self, key: str) -> bool:
        return key in self._cache

    def keys(self) -> List[str]:
        return list(self._cache.keys())

    def values(self) -> Dict[str, Any]:
        return dict(self._cache)

    def clear(self) -> None:
        for key in list(self._cache.keys()):
            self.unset(key)

    def size(self) -> int:
        return len(self._cache)

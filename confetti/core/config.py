from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .merge import merge_sources
from .source import RegisteredSource, Source
from .types import ConfigChange, ProvenanceRecord


@dataclass
class Config:
    registered_sources: List[RegisteredSource]
    _effective: Dict[str, Any] = field(default_factory=dict)
    _provenance: Dict[str, ProvenanceRecord] = field(default_factory=dict)
    _staged: List[ConfigChange] = field(default_factory=list)

    def materialize(self) -> None:
        self._effective, self._provenance = merge_sources(self.registered_sources)

    def values(self) -> Dict[str, Any]:
        if not self._effective:
            self.materialize()
        return dict(self._effective)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        if not self._effective:
            self.materialize()
        return self._effective.get(key, default)

    def provenance(self, key: str) -> Optional[ProvenanceRecord]:
        if not self._effective:
            self.materialize()
        return self._provenance.get(key)

    def set(self, key: str, value: Any, source: Optional[str] = None) -> None:
        if not self._effective:
            self.materialize()
        target_source_id = self._resolve_target_source_id(key, source)
        self._effective[key] = value
        self._staged.append(
            ConfigChange(op="set", key=key, value=value, target_source_id=target_source_id)
        )

    def unset(self, key: str) -> None:
        if not self._effective:
            self.materialize()
        prov = self._provenance.get(key)
        if prov is None:
            # no-op on provenance, but remove from effective if present
            self._effective.pop(key, None)
            return
        self._effective.pop(key, None)
        self._staged.append(
            ConfigChange(op="unset", key=key, value=None, target_source_id=prov.source_id)
        )

    def _resolve_target_source_id(self, key: str, preferred: Optional[str]) -> str:
        if preferred:
            return preferred
        prov = self._provenance.get(key)
        if prov:
            return prov.source_id
        # default source is first registered
        if not self.registered_sources:
            raise ValueError("No sources registered")
        return self.registered_sources[0].source.id

    def remove_source(self, id_or_uri: str) -> None:
        self.registered_sources = [
            rs for rs in self.registered_sources if rs.source.id != id_or_uri
        ]
        # drop related staged changes
        self._staged = [c for c in self._staged if c.target_source_id != id_or_uri]
        self.materialize()

    def reload(self) -> None:
        for rs in self.registered_sources:
            rs.source.reload()
        self.materialize()

    def save(self) -> None:
        # group changes by source id
        by_source: Dict[str, List[ConfigChange]] = {}
        for ch in self._staged:
            by_source.setdefault(ch.target_source_id, []).append(ch)

        for rs in self.registered_sources:
            changes = by_source.get(rs.source.id)
            if not changes:
                continue
            if not rs.is_writable:
                raise PermissionError(f"Source {rs.source.id} is not writable")
            for ch in changes:
                if ch.op == "set":
                    rs.source.set(ch.key, ch.value)
                elif ch.op == "unset":
                    rs.source.unset(ch.key)
            rs.source.save()

        # clear and re-materialize for accurate provenance/fallback
        self._staged.clear()
        self.materialize()

    def save_to_github(self, github_uri: str, token: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Push the merged config values into a GitHub environment variables source.

        Returns a summary dict with keys: set (dict) and delete (list) when dry_run=True; empty dict otherwise.
        """
        # Lazy import to avoid hard dependency at import time
        from ..sources.github_env import GitHubEnvSource

        merged = self.values()
        gh = GitHubEnvSource(github_uri, token=token)
        gh.load()
        if dry_run:
            to_set = {k: v for k, v in merged.items() if gh.get(k) != v}
            to_del = [k for k in gh.keys() if k not in merged]
            return {"set": to_set, "delete": to_del}
        for k, v in merged.items():
            gh.set(k, str(v))
        gh.save()
        return {}

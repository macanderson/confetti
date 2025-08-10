from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern, TypedDict


class FlattenedConfig(TypedDict, total=False):
    # Flat key -> scalar/JSON-serializable value
    pass


@dataclass(frozen=True)
class ProvenanceRecord:
    key: str
    source_id: str
    source_key: str
    timestamp_loaded: datetime


@dataclass(frozen=True)
class ConfigChange:
    op: str  # "set" | "unset"
    key: str
    value: Optional[Any]
    target_source_id: str


@dataclass(frozen=True)
class HierarchicalFilter:
    # A hierarchical include spec for structured sources
    spec: Dict[str, Any]


@dataclass(frozen=True)
class FilterSpec:
    include_regex: Optional[Pattern[str]] = None
    hierarchical_spec: Optional[HierarchicalFilter] = None
    depth: Optional[int] = None

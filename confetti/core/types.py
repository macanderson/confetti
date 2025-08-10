"""Type definitions for the Confetti configuration system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern, TypedDict


class FlattenedConfig(TypedDict, total=False):
    """Type definition for flattened configuration dictionaries."""
    
    # Flat key -> scalar/JSON-serializable value
    pass


@dataclass(frozen=True)
class ProvenanceRecord:
    """Record tracking the source of a configuration value.
    
    Attributes:
        key: Configuration key.
        source_id: ID of the source this value came from.
        source_key: Original key in the source.
        timestamp_loaded: When this value was loaded.
    """
    
    key: str
    source_id: str
    source_key: str
    timestamp_loaded: datetime


@dataclass(frozen=True)
class ConfigChange:
    """Represents a pending change to configuration.
    
    Attributes:
        op: Operation type ('set' or 'unset').
        key: Configuration key being changed.
        value: New value (None for unset operations).
        target_source_id: ID of source to save change to.
    """
    
    op: str  # "set" | "unset"
    key: str
    value: Optional[Any]
    target_source_id: str


@dataclass(frozen=True)
class HierarchicalFilter:
    """Filter specification for hierarchical data structures.
    
    Attributes:
        spec: Dictionary specifying which nested keys to include.
    """
    
    # A hierarchical include spec for structured sources
    spec: Dict[str, Any]


@dataclass(frozen=True)
class FilterSpec:
    """Complete filter specification for configuration sources.
    
    Attributes:
        include_regex: Pattern for regex-based key filtering.
        hierarchical_spec: Specification for hierarchical filtering.
        depth: Maximum depth for hierarchical flattening.
    """
    
    include_regex: Optional[Pattern[str]] = None
    hierarchical_spec: Optional[HierarchicalFilter] = None
    depth: Optional[int] = None

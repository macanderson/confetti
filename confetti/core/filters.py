"""Filtering mechanisms for configuration keys."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, Optional, Pattern, Tuple


@dataclass(frozen=True)
class Filter:
    """Filter for including/excluding configuration keys.
    
    Attributes:
        include_regex: Regular expression pattern for key inclusion.
        hierarchical_spec: Hierarchical specification for nested sources.
        depth: Maximum depth for hierarchical flattening.
    """
    
    include_regex: Optional[Pattern[str]] = None
    hierarchical_spec: Optional[Dict[str, Any]] = None
    depth: Optional[int] = None

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> Optional["Filter"]:
        """Create a Filter from a dictionary specification.
        
        Args:
            d: Dictionary with filter specification.
            
        Returns:
            Filter instance or None if d is None/empty.
        """
        if not d:
            return None
        regex = d.get("include_regex")
        compiled: Optional[Pattern[str]] = (
            re.compile(regex) if isinstance(regex, str) else None
        )
        hierarchical = d.get("hierarchical_spec")
        depth = d.get("depth")
        return Filter(
            include_regex=compiled, 
            hierarchical_spec=hierarchical, 
            depth=depth
        )


def should_include_key(flat_key: str, flt: Optional[Filter]) -> bool:
    """Check if a key should be included based on filter.
    
    Args:
        flat_key: Flattened configuration key.
        flt: Filter to apply (None means include all).
        
    Returns:
        True if key should be included, False otherwise.
    """
    if flt is None:
        return True
    if flt.include_regex and not flt.include_regex.search(flat_key):
        return False
    return True


def iter_hierarchical(
    data: Dict[str, Any],
    parent: str = "",
    depth: Optional[int] = None,
) -> Iterator[Tuple[str, Any]]:
    """Flatten nested dictionaries using dot-notation.

    Lists are emitted as-is for caller serialization.
    Scalars are emitted directly.
    
    Args:
        data: Dictionary to flatten.
        parent: Parent key prefix for recursion.
        depth: Maximum depth to flatten (None for unlimited).
        
    Yields:
        Tuples of (flattened_key, value).
    """
    if depth is not None and depth < 0:
        return

    for key, value in data.items():
        full_key = key if not parent else f"{parent}.{key}"
        if isinstance(value, dict) and (depth is None or depth > 0):
            next_depth = None if depth is None else depth - 1
            yield from iter_hierarchical(value, full_key, next_depth)
        else:
            yield full_key, value


def filter_hierarchical(
    data: Dict[str, Any],
    spec: Optional[Dict[str, Any]],
    depth: Optional[int],
) -> Dict[str, Any]:
    """Filter hierarchical data based on specification and depth.
    
    Args:
        data: Dictionary to filter.
        spec: Hierarchical specification for filtering.
        depth: Maximum depth for flattening.
        
    Returns:
        Filtered and flattened dictionary.
    """
    if spec is None:
        # just depth-limit flatten
        return {k: v for k, v in iter_hierarchical(data, depth=depth)}

    def include_path(path: str) -> bool:
        """Check if a path should be included based on spec."""
        # Simple prefix-based inclusion according to spec keys
        parts = path.split(".")
        node = spec
        for i, part in enumerate(parts):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
            if node is True:
                return True
        return node is True

    flattened = {k: v for k, v in iter_hierarchical(data, depth=depth)}
    return {k: v for k, v in flattened.items() if include_path(k)}

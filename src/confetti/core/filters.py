from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, Optional, Pattern, Tuple


@dataclass(frozen=True)
class Filter:
    include_regex: Optional[Pattern[str]] = None
    hierarchical_spec: Optional[Dict[str, Any]] = None
    depth: Optional[int] = None

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> Optional["Filter"]:
        if not d:
            return None
        regex = d.get("include_regex")
        compiled: Optional[Pattern[str]] = re.compile(regex) if isinstance(regex, str) else None
        hierarchical = d.get("hierarchical_spec")
        depth = d.get("depth")
        return Filter(include_regex=compiled, hierarchical_spec=hierarchical, depth=depth)


def should_include_key(flat_key: str, flt: Optional[Filter]) -> bool:
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
    """Flatten nested dictionaries using dot-notation up to optional depth.

    - Lists are emitted as-is (caller can serialize when needed).
    - Scalars are emitted directly.
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
    if spec is None:
        # just depth-limit flatten
        return {k: v for k, v in iter_hierarchical(data, depth=depth)}

    def include_path(path: str) -> bool:
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

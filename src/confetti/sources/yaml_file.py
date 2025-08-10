from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core.filters import Filter, filter_hierarchical, iter_hierarchical, should_include_key
from ..core.source import Source
import yaml

class YamlFileSource(Source):
    def __init__(self, path: Path, name: Optional[str] = None):
        self.path = Path(path)
        self.name = name or f"yaml:{self.path.name}"
        self.id = str(self.path.resolve())
        self.extension = ".yaml"
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data

    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        data = self._read()
        if filter and (filter.hierarchical_spec is not None or filter.depth is not None):
            flattened = filter_hierarchical(data, filter.hierarchical_spec, filter.depth)
        else:
            flattened = {k: v for k, v in iter_hierarchical(data, depth=depth)}
        # serialize lists and dict leaves to JSON strings for stability
        normalized: Dict[str, Any] = {}
        for k, v in flattened.items():
            if isinstance(v, (dict, list)):
                normalized[k] = json.dumps(v, separators=(",", ":"))
            else:
                normalized[k] = v
        self._cache = normalized
        if filter:
            return {k: v for k, v in self._cache.items() if should_include_key(k, filter)}
        return dict(self._cache)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._staged[key] = value

    def unset(self, key: str) -> None:
        self._staged[key] = None

    def save(self) -> None:
        # For YAML, we only support staging flat keys; we will reconstruct a nested dict
        nested: Dict[str, Any] = {}
        # start from current
        existing = self._read()
        nested.update(existing)

        def set_nested(d: Dict[str, Any], path: List[str], value: Any) -> None:
            for part in path[:-1]:
                if part not in d or not isinstance(d[part], dict):
                    d[part] = {}
                d = d[part]
            d[path[-1]] = value

        def unset_nested(d: Dict[str, Any], path: List[str]) -> None:
            for part in path[:-1]:
                if part not in d or not isinstance(d[part], dict):
                    return
                d = d[part]
            d.pop(path[-1], None)

        for k, v in self._staged.items():
            parts = k.split(".")
            if v is None:
                unset_nested(nested, parts)
            else:
                set_nested(nested, parts, v)

        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(nested, f, sort_keys=False)
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

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.filters import Filter, should_include_key
from ..core.source import Source


class IniFileSource(Source):
    def __init__(self, path: Path, name: Optional[str] = None):
        self.path = Path(path)
        self.name = name or f"ini:{self.path.name}"
        self.id = str(self.path.resolve())
        self.extension = ".ini"
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}

    def _flatten(self, parser: configparser.ConfigParser) -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        for section in parser.sections():
            for key, value in parser.items(section):
                flat[f"{section}.{key}"] = value
        return flat

    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        parser = configparser.ConfigParser()
        if self.path.exists():
            parser.read(self.path)
        self._cache = self._flatten(parser)
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
        # We reconstruct sections
        parser = configparser.ConfigParser()
        if self.path.exists():
            parser.read(self.path)
        # apply staged
        for k, v in self._staged.items():
            if "." not in k:
                section, subkey = "DEFAULT", k
            else:
                section, subkey = k.split(".", 1)
            if v is None:
                if parser.has_option(section, subkey):
                    parser.remove_option(section, subkey)
            else:
                if not parser.has_section(section) and section != "DEFAULT":
                    parser.add_section(section)
                parser.set(section, subkey, str(v))
        with open(self.path, "w", encoding="utf-8") as f:
            parser.write(f)
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

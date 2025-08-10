from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.filters import Filter, should_include_key
from ..core.source import Source
from ..dotenv import DotEnv, set_key as dotenv_set_key, unset_key as dotenv_unset_key


class EnvFileSource(Source):
    def __init__(self, path: Path, name: Optional[str] = None):
        self.path = Path(path)
        self._dotenv = DotEnv(self.path)
        self.name = name or f"env:{self.path.name}"
        self.id = str(self.path.resolve())
        self.extension = ".env"
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}

    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        self._dotenv.load_dotenv(override=False)
        self._cache = self._dotenv.values()
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
        for k, v in self._staged.items():
            if v is None:
                dotenv_unset_key(self.path, k)
            else:
                dotenv_set_key(self.path, k, str(v))
        self._staged.clear()
        self.reload()

    def reload(self) -> None:
        self._dotenv = DotEnv(self.path)
        self._dotenv.load_dotenv(override=False)
        self._cache = self._dotenv.values()

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

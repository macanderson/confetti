from __future__ import annotations

from typing import Any, Dict, List, Optional

import redis

from ..core.filters import Filter, should_include_key
from ..core.source import Source


class RedisKeyValueSource(Source):
    def __init__(self, uri: str, name: Optional[str] = None, prefix: str = ""):
        self.uri = uri
        self.client = redis.Redis.from_url(uri, decode_responses=True)
        self.name = name or f"redis:{uri}"
        self.id = uri
        self.extension = None
        self.prefix = prefix
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}

    def _prefixed(self, key: str) -> str:
        return f"{self.prefix}{key}" if self.prefix else key

    def _unprefixed(self, key: str) -> str:
        if self.prefix and key.startswith(self.prefix):
            return key[len(self.prefix) :]
        return key

    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        keys = self.client.keys(self._prefixed("*"))
        kv: Dict[str, Any] = {}
        if keys:
            values = self.client.mget(keys)
            for k, v in zip(keys, values):
                flat_key = self._unprefixed(k)
                kv[flat_key] = v
        self._cache = kv
        if filter:
            return {k: v for k, v in self._cache.items() if should_include_key(k, filter)}
        return dict(self._cache)

    def get(self, key: str) -> Optional[Any]:
        return self.client.get(self._prefixed(key))

    def set(self, key: str, value: Any) -> None:
        self._staged[key] = value

    def unset(self, key: str) -> None:
        self._staged[key] = None

    def save(self) -> None:
        pipe = self.client.pipeline()
        for k, v in self._staged.items():
            pk = self._prefixed(k)
            if v is None:
                pipe.delete(pk)
            else:
                pipe.set(pk, str(v))
        pipe.execute()
        self._staged.clear()
        self.reload()

    def reload(self) -> None:
        self.load()

    def exists(self, key: str) -> bool:
        return bool(self.client.exists(self._prefixed(key)))

    def keys(self) -> List[str]:
        return list(self._cache.keys())

    def values(self) -> Dict[str, Any]:
        return dict(self._cache)

    def clear(self) -> None:
        if not self.prefix:
            for k in list(self._cache.keys()):
                self.unset(k)
        else:
            # delete by prefix
            keys = self.client.keys(self._prefixed("*"))
            if keys:
                self.client.delete(*keys)

    def size(self) -> int:
        return len(self._cache)

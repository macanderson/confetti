from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from .filters import Filter


class Source(Protocol):
    id: str
    name: str
    extension: Optional[str]

    def load(self, filter: Optional[Filter] = None, depth: Optional[int] = None) -> Dict[str, Any]:
        ...

    def get(self, key: str) -> Optional[Any]:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def unset(self, key: str) -> None:
        ...

    def save(self) -> None:
        ...

    def reload(self) -> None:
        ...

    def exists(self, key: str) -> bool:
        ...

    def keys(self) -> List[str]:
        ...

    def values(self) -> Dict[str, Any]:
        ...

    def clear(self) -> None:
        ...

    def size(self) -> int:
        ...


@dataclass
class RegisteredSource:
    source: Source
    filter: Optional[Filter] = None
    depth: Optional[int] = None
    is_writable: bool = True

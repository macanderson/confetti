"""Source protocol and registration for configuration sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from .filters import Filter


class Source(Protocol):
    """Protocol defining the interface for configuration sources.
    
    All configuration sources must implement this protocol to be
    used with the Confetti configuration management system.
    """
    
    id: str
    name: str
    extension: Optional[str]

    def load(
        self, 
        filter: Optional[Filter] = None, 
        depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """Load configuration values from the source.
        
        Args:
            filter: Optional filter to apply to keys.
            depth: Optional depth limit for hierarchical sources.
            
        Returns:
            Dictionary of configuration key-value pairs.
        """
        ...

    def get(self, key: str) -> Optional[Any]:
        """Get a single value by key.
        
        Args:
            key: Configuration key to retrieve.
            
        Returns:
            Value if key exists, None otherwise.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a value for a key.
        
        Args:
            key: Configuration key to set.
            value: Value to set.
        """
        ...

    def unset(self, key: str) -> None:
        """Remove a key from the source.
        
        Args:
            key: Configuration key to remove.
        """
        ...

    def save(self) -> None:
        """Persist any staged changes to the source."""
        ...

    def reload(self) -> None:
        """Reload values from the source."""
        ...

    def exists(self, key: str) -> bool:
        """Check if a key exists in the source.
        
        Args:
            key: Configuration key to check.
            
        Returns:
            True if key exists, False otherwise.
        """
        ...

    def keys(self) -> List[str]:
        """Get all keys from the source.
        
        Returns:
            List of all configuration keys.
        """
        ...

    def values(self) -> Dict[str, Any]:
        """Get all values from the source.
        
        Returns:
            Dictionary of all configuration key-value pairs.
        """
        ...

    def clear(self) -> None:
        """Remove all keys from the source."""
        ...

    def size(self) -> int:
        """Get the number of keys in the source.
        
        Returns:
            Number of configuration keys.
        """
        ...


@dataclass
class RegisteredSource:
    """A source registered with an Environment.
    
    Attributes:
        source: The source instance.
        filter: Optional filter to apply to source keys.
        depth: Optional depth limit for hierarchical sources.
        is_writable: Whether the source can be written to.
    """
    
    source: Source
    filter: Optional[Filter] = None
    depth: Optional[int] = None
    is_writable: bool = True

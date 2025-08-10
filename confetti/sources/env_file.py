"""Environment file (.env) configuration source."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.filters import Filter, should_include_key
from ..core.source import Source
from ..dotenv import (
    DotEnv, 
    set_key as dotenv_set_key, 
    unset_key as dotenv_unset_key
)


class EnvFileSource(Source):
    """Configuration source for .env files.
    
    Reads and writes configuration from environment files using
    KEY=VALUE format with support for comments and variable expansion.
    """
    
    def __init__(self, path: Path, name: Optional[str] = None):
        """Initialize EnvFileSource.
        
        Args:
            path: Path to the .env file.
            name: Optional custom name for this source.
        """
        self.path = Path(path)
        self._dotenv = DotEnv(self.path)
        self.name = name or f"env:{self.path.name}"
        self.id = str(self.path.resolve())
        self.extension = ".env"
        self._cache: Dict[str, Any] = {}
        self._staged: Dict[str, Optional[Any]] = {}

    def load(
        self, 
        filter: Optional[Filter] = None, 
        depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """Load configuration from the env file.
        
        Args:
            filter: Optional filter to apply to keys.
            depth: Not used for env files (flat structure).
            
        Returns:
            Dictionary of configuration values.
        """
        self._dotenv.load_dotenv(override=False)
        self._cache = self._dotenv.values()
        if filter:
            return {
                k: v for k, v in self._cache.items() 
                if should_include_key(k, filter)
            }
        return dict(self._cache)

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key.
        
        Args:
            key: Configuration key.
            
        Returns:
            Value if key exists, None otherwise.
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Stage a value to be set.
        
        Args:
            key: Configuration key.
            value: Value to set.
        """
        self._staged[key] = value

    def unset(self, key: str) -> None:
        """Stage a key to be removed.
        
        Args:
            key: Configuration key to remove.
        """
        self._staged[key] = None

    def save(self) -> None:
        """Save all staged changes to the env file."""
        for k, v in self._staged.items():
            if v is None:
                dotenv_unset_key(self.path, k)
            else:
                dotenv_set_key(self.path, k, str(v))
        self._staged.clear()
        self.reload()

    def reload(self) -> None:
        """Reload configuration from the env file."""
        self._dotenv = DotEnv(self.path)
        self._dotenv.load_dotenv(override=False)
        self._cache = self._dotenv.values()

    def exists(self, key: str) -> bool:
        """Check if a key exists.
        
        Args:
            key: Configuration key.
            
        Returns:
            True if key exists, False otherwise.
        """
        return key in self._cache

    def keys(self) -> List[str]:
        """Get all configuration keys.
        
        Returns:
            List of all keys.
        """
        return list(self._cache.keys())

    def values(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all key-value pairs.
        """
        return dict(self._cache)

    def clear(self) -> None:
        """Remove all configuration values."""
        for key in list(self._cache.keys()):
            self.unset(key)

    def size(self) -> int:
        """Get the number of configuration entries.
        
        Returns:
            Number of key-value pairs.
        """
        return len(self._cache)

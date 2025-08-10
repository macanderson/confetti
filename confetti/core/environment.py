"""Environment management for configuration sources."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import Config
from .filters import Filter
from .source import RegisteredSource, Source
# Lazy imports inside _create_source to avoid optional dependency import at module load time


class Environment:
    """Manage configuration sources for a specific environment.
    
    An Environment represents a named collection of configuration
    sources that can be loaded and merged into a unified Config object.
    """
    
    def __init__(self, name: str):
        """Initialize Environment with a name.
        
        Args:
            name: Environment name (e.g., 'development', 'production').
        """
        self.name = name
        self._registered: List[RegisteredSource] = []

    def register_sources(self, *paths_or_uris: Union[str, Path]) -> None:
        """Register multiple configuration sources.
        
        Args:
            *paths_or_uris: Variable number of file paths or URIs.
        """
        for item in paths_or_uris:
            self.register_source(item)

    def register_source(
        self,
        path_or_uri: Union[str, Path],
        *,
        filter: Optional[Filter] = None,
        depth: Optional[int] = None,
        name: Optional[str] = None,
        is_writable: Optional[bool] = None,
    ) -> None:
        """Register a single configuration source.
        
        Args:
            path_or_uri: File path or URI of the source.
            filter: Optional filter to apply to source keys.
            depth: Optional depth limit for hierarchical sources.
            name: Optional custom name for the source.
            is_writable: Whether the source can be written to.
        """
        src = self._create_source(path_or_uri, name=name)
        writable = True if is_writable is None else is_writable
        self._registered.append(
            RegisteredSource(
                source=src, 
                filter=filter, 
                depth=depth, 
                is_writable=writable
            )
        )

    def _create_source(
        self, 
        path_or_uri: Union[str, Path], 
        name: Optional[str]
    ) -> Source:
        """Create a source instance based on path/URI type.
        
        Args:
            path_or_uri: File path or URI of the source.
            name: Optional custom name for the source.
            
        Returns:
            Source instance.
            
        Raises:
            ValueError: If source type is not supported.
        """
        s = str(path_or_uri)
        if s.startswith("redis://"):
            from ..sources.redis_kv import RedisKeyValueSource
            return RedisKeyValueSource(s, name=name)
        p = Path(s)
        if p.suffix in {".env", ""} and p.exists():
            from ..sources.env_file import EnvFileSource
            return EnvFileSource(p, name=name)
        if p.suffix.lower() == ".ini":
            from ..sources.ini_file import IniFileSource
            return IniFileSource(p, name=name)
        if p.suffix.lower() in {".yaml", ".yml"}:
            from ..sources.yaml_file import YamlFileSource
            return YamlFileSource(p, name=name)
        if p.suffix.lower() == ".json":
            from ..sources.json_file import JsonFileSource
            return JsonFileSource(p, name=name)
        # default to env file if no suffix but file exists
        if p.exists():
            from ..sources.env_file import EnvFileSource
            return EnvFileSource(p, name=name)
        if s.startswith("github://"):
            from ..sources.github_env import GitHubEnvSource
            return GitHubEnvSource(s, name=name)
        raise ValueError(f"Unsupported source type: {path_or_uri}")

    def get_config(self) -> Config:
        """Get a Config object with all registered sources.
        
        Returns:
            Config object with materialized values from all sources.
        """
        cfg = Config(self._registered)
        cfg.materialize()
        return cfg

    def add_source_type(self, source: Source) -> None:
        """Add a custom source instance directly.
        
        Args:
            source: Source instance to add.
        """
        # Allow manual injection of a ready-made source instance
        self._registered.append(RegisteredSource(source=source))

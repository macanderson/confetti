from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import Config
from .config_loader import ConfigLoader
from .filters import Filter
from .source import RegisteredSource, Source
# Lazy imports inside _create_source to avoid optional dependency import at module load time


class Environment:
    """Environment for managing configuration sources."""

    def __init__(
        self,
        name: str,
        sources: Optional[List[Union[str, Path]]] = None,
        config_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize an Environment.

        Args:
            name: Name of the environment (e.g., "production", "development").
            sources: Optional list of sources to register. These will be merged
                with sources from confetti.yaml if present.
            config_path: Optional path to confetti.yaml file. If not provided,
                searches for confetti.yaml in current and parent directories.
        """
        self.name = name
        self._registered: List[RegisteredSource] = []
        self._config_loader = ConfigLoader(config_path)

        # Load sources from confetti.yaml if available
        self._load_from_config_file()

        # Register any explicitly provided sources
        if sources:
            self.register_sources(*sources)

    def _load_from_config_file(self) -> None:
        """Load sources from confetti.yaml if available."""
        try:
            sources = self._config_loader.get_sources(self.name)
            for source_config in sources:
                try:
                    parsed = self._config_loader.parse_source(source_config)
                    self.register_source(
                        parsed["path_or_uri"],
                        filter=parsed.get("filter"),
                        depth=parsed.get("depth"),
                        name=parsed.get("name"),
                        is_writable=parsed.get("is_writable"),
                    )
                except Exception as e:
                    # Graceful error handling - print warning and continue
                    print(
                        f"Warning: Failed to load source from confetti.yaml: {e}"
                    )
        except Exception as e:
            # If there's an error loading the config file itself, continue
            # This allows the Environment to work even without confetti.yaml
            if self._config_loader.config_path:
                print(
                    f"Warning: Error loading confetti.yaml from "
                    f"{self._config_loader.config_path}: {e}"
                )

    def register_sources(self, *paths_or_uris: Union[str, Path]) -> None:
        """Register multiple sources at once.

        Args:
            *paths_or_uris: Variable number of paths or URIs to register.
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
        """Register a single source.

        Args:
            path_or_uri: Path to a file or URI for the source.
            filter: Optional filter to apply when loading from this source.
            depth: Optional depth limit for nested structures.
            name: Optional name for the source.
            is_writable: Whether the source should be writable. Defaults to True.
        """
        src = self._create_source(path_or_uri, name=name)
        writable = True if is_writable is None else is_writable
        self._registered.append(
            RegisteredSource(
                source=src, filter=filter, depth=depth, is_writable=writable
            )
        )

    def _create_source(
        self, path_or_uri: Union[str, Path], name: Optional[str]
    ) -> Source:
        """Create a Source instance based on path/URI type.

        Args:
            path_or_uri: Path to file or URI for the source.
            name: Optional name for the source.

        Returns:
            Source instance.

        Raises:
            ValueError: If the source type is not supported.
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
            Config object with materialized configuration.
        """
        cfg = Config(self._registered)
        cfg.materialize()
        return cfg

    def add_source_type(self, source: Source) -> None:
        """Add a custom source instance.

        Args:
            source: Source instance to add.
        """
        # Allow manual injection of a ready-made source instance
        self._registered.append(RegisteredSource(source=source))

    @property
    def config_file_path(self) -> Optional[Path]:
        """Get the path to the loaded confetti.yaml file, if any.

        Returns:
            Path to confetti.yaml file, or None if not found/loaded.
        """
        return self._config_loader.config_path

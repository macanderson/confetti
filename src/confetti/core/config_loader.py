"""Configuration loader for confetti.yaml files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .filters import Filter


class ConfigLoader:
    """Handles loading and parsing of confetti.yaml configuration files."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize config loader.

        Args:
            config_path: Path to confetti.yaml file. If None, looks in current
                directory and parent directories.
        """
        self.config_path = self._find_config_file(config_path)
        self._config: Optional[Dict[str, Any]] = None

    def _find_config_file(
        self, config_path: Optional[Union[str, Path]] = None
    ) -> Optional[Path]:
        """Find the confetti.yaml file.

        Args:
            config_path: Explicit path to config file, or None to search.

        Returns:
            Path to config file if found, None otherwise.
        """
        if config_path is not None:
            path = Path(config_path)
            if path.exists():
                return path
            return None

        # Search for confetti.yaml in current and parent directories
        current = Path.cwd()
        while current != current.parent:
            candidate = current / "confetti.yaml"
            if candidate.exists():
                return candidate
            current = current.parent

        # Check root directory
        candidate = current / "confetti.yaml"
        if candidate.exists():
            return candidate

        return None

    def load(self) -> Dict[str, Any]:
        """Load the configuration file.

        Returns:
            Parsed configuration dictionary, or empty dict if no config file.

        Raises:
            yaml.YAMLError: If the config file is invalid YAML.
        """
        if self.config_path is None:
            return {}

        if self._config is not None:
            return self._config

        try:
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
                return self._config
        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid confetti.yaml at {self.config_path}: {e}"
            ) from e
        except Exception as e:
            # Graceful error handling - return empty config on read errors
            print(f"Warning: Could not read confetti.yaml at {self.config_path}: {e}")
            return {}

    def get_environment_config(
        self, environment_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific environment.

        Args:
            environment_name: Name of the environment.

        Returns:
            Environment configuration dict, or None if not found.
        """
        config = self.load()
        environments = config.get("environments", {})
        return environments.get(environment_name)

    def get_sources(self, environment_name: str) -> List[Dict[str, Any]]:
        """Get source configurations for an environment.

        Args:
            environment_name: Name of the environment.

        Returns:
            List of source configuration dictionaries.
        """
        env_config = self.get_environment_config(environment_name)
        if env_config is None:
            return []
        return env_config.get("sources", [])

    def parse_source(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a source configuration into components.

        Args:
            source_config: Raw source configuration from YAML.

        Returns:
            Dictionary with parsed source components.
        """
        result: Dict[str, Any] = {}

        # Handle path or URI
        if "path" in source_config:
            result["path_or_uri"] = Path(source_config["path"])
        elif "uri" in source_config:
            result["path_or_uri"] = source_config["uri"]
        else:
            raise ValueError("Source must have either 'path' or 'uri'")

        # Handle filter configuration
        filter_config = source_config.get("filter")
        if filter_config:
            filter_obj = self._parse_filter(filter_config)
            result["filter"] = filter_obj

        # Handle depth (can be in filter or at source level)
        if "depth" in source_config:
            result["depth"] = source_config["depth"]
        elif filter_config and "depth" in filter_config:
            result["depth"] = filter_config["depth"]

        # Handle other attributes
        if "name" in source_config:
            result["name"] = source_config["name"]
        if "writable" in source_config:
            result["is_writable"] = source_config["writable"]

        return result

    def _parse_filter(self, filter_config: Dict[str, Any]) -> Filter:
        """Parse filter configuration into a Filter object.

        Args:
            filter_config: Filter configuration dictionary.

        Returns:
            Filter object.
        """
        include_regex = None
        if "include_regex" in filter_config:
            include_regex = re.compile(filter_config["include_regex"])

        hierarchical_spec = filter_config.get("hierarchical_spec")
        depth = filter_config.get("depth")

        return Filter(
            include_regex=include_regex,
            hierarchical_spec=hierarchical_spec,
            depth=depth,
        )

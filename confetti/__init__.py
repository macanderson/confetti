"""Confetti - Configuration management library.

Compose configuration from multiple sources into a unified config with
provenance tracking and save semantics.
"""

from .core.environment import Environment
from .core.config import Config
from .core.source import Source, RegisteredSource
from .core.filters import Filter

__all__ = [
    "Environment",
    "Config",
    "Source",
    "RegisteredSource",
    "Filter",
]

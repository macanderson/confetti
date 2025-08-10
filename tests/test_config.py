"""Unit tests for the Config class."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from confetti.core.config import Config
from confetti.core.source import RegisteredSource
from confetti.core.types import ConfigChange, ProvenanceRecord


class MockSource:
    """Mock source for testing."""
    
    def __init__(self, source_id: str, data: Dict[str, Any]):
        """Initialize mock source."""
        self.id = source_id
        self.name = f"mock:{source_id}"
        self.extension = None
        self._data = data
        self._staged = {}
        
    def load(self, filter=None, depth=None):
        """Load mock data."""
        return dict(self._data)
        
    def get(self, key: str):
        """Get value by key."""
        return self._data.get(key)
        
    def set(self, key: str, value: Any):
        """Set value."""
        self._staged[key] = value
        
    def unset(self, key: str):
        """Unset key."""
        self._staged[key] = None
        
    def save(self):
        """Save staged changes."""
        for k, v in self._staged.items():
            if v is None:
                self._data.pop(k, None)
            else:
                self._data[k] = v
        self._staged.clear()
        
    def reload(self):
        """Reload data."""
        pass
        
    def exists(self, key: str):
        """Check if key exists."""
        return key in self._data
        
    def keys(self):
        """Get all keys."""
        return list(self._data.keys())
        
    def values(self):
        """Get all values."""
        return dict(self._data)
        
    def clear(self):
        """Clear all data."""
        self._data.clear()
        
    def size(self):
        """Get size."""
        return len(self._data)


class TestConfig:
    """Test suite for Config class."""
    
    def test_materialize_empty(self):
        """Test materializing with no sources."""
        config = Config([])
        config.materialize()
        assert config.values() == {}
        
    def test_materialize_single_source(self):
        """Test materializing with single source."""
        source = MockSource("s1", {"key1": "value1", "key2": "value2"})
        rs = RegisteredSource(source=source)
        config = Config([rs])
        config.materialize()
        
        assert config.values() == {"key1": "value1", "key2": "value2"}
        assert config.get("key1") == "value1"
        assert config.get("missing") is None
        assert config.get("missing", "default") == "default"
        
    def test_materialize_multiple_sources_override(self):
        """Test that later sources override earlier ones."""
        source1 = MockSource("s1", {"key": "value1", "only1": "v1"})
        source2 = MockSource("s2", {"key": "value2", "only2": "v2"})
        
        config = Config([
            RegisteredSource(source=source1),
            RegisteredSource(source=source2)
        ])
        config.materialize()
        
        values = config.values()
        assert values["key"] == "value2"  # s2 overrides s1
        assert values["only1"] == "v1"
        assert values["only2"] == "v2"
        
    def test_provenance_tracking(self):
        """Test provenance records are created correctly."""
        source1 = MockSource("s1", {"key1": "value1"})
        source2 = MockSource("s2", {"key2": "value2"})
        
        config = Config([
            RegisteredSource(source=source1),
            RegisteredSource(source=source2)
        ])
        config.materialize()
        
        prov1 = config.provenance("key1")
        assert prov1 is not None
        assert prov1.source_id == "s1"
        assert prov1.key == "key1"
        
        prov2 = config.provenance("key2")
        assert prov2 is not None
        assert prov2.source_id == "s2"
        
        assert config.provenance("missing") is None
        
    def test_set_value(self):
        """Test setting configuration values."""
        source = MockSource("s1", {"existing": "value"})
        config = Config([RegisteredSource(source=source)])
        
        config.set("new_key", "new_value")
        assert config.get("new_key") == "new_value"
        assert len(config._staged) == 1
        assert config._staged[0].op == "set"
        assert config._staged[0].key == "new_key"
        assert config._staged[0].value == "new_value"
        
    def test_set_with_preferred_source(self):
        """Test setting value with preferred source."""
        source1 = MockSource("s1", {})
        source2 = MockSource("s2", {})
        config = Config([
            RegisteredSource(source=source1),
            RegisteredSource(source=source2)
        ])
        
        config.set("key", "value", source="s2")
        assert config._staged[0].target_source_id == "s2"
        
    def test_unset_value(self):
        """Test unsetting configuration values."""
        source = MockSource("s1", {"key": "value"})
        config = Config([RegisteredSource(source=source)])
        config.materialize()
        
        config.unset("key")
        assert config.get("key") is None
        assert len(config._staged) == 1
        assert config._staged[0].op == "unset"
        assert config._staged[0].key == "key"
        
    def test_unset_nonexistent_key(self):
        """Test unsetting a key that doesn't exist."""
        source = MockSource("s1", {})
        config = Config([RegisteredSource(source=source)])
        
        config.unset("missing")
        assert len(config._staged) == 0  # No change staged
        
    def test_remove_source(self):
        """Test removing a source."""
        source1 = MockSource("s1", {"key1": "value1"})
        source2 = MockSource("s2", {"key2": "value2"})
        
        config = Config([
            RegisteredSource(source=source1),
            RegisteredSource(source=source2)
        ])
        config.materialize()
        
        config.remove_source("s1")
        assert len(config.registered_sources) == 1
        assert config.registered_sources[0].source.id == "s2"
        
        # After re-materialization, key1 should be gone
        assert config.get("key1") is None
        assert config.get("key2") == "value2"
        
    def test_reload(self):
        """Test reloading sources."""
        source = MockSource("s1", {"key": "value"})
        config = Config([RegisteredSource(source=source)])
        config.materialize()
        
        # Modify source data directly
        source._data["key"] = "new_value"
        source._data["new_key"] = "new"
        
        config.reload()
        assert config.get("key") == "new_value"
        assert config.get("new_key") == "new"
        
    def test_save_changes(self):
        """Test saving staged changes."""
        source1 = MockSource("s1", {"key1": "value1"})
        source2 = MockSource("s2", {"key2": "value2"})
        
        config = Config([
            RegisteredSource(source=source1, is_writable=True),
            RegisteredSource(source=source2, is_writable=True)
        ])
        config.materialize()
        
        config.set("key1", "modified")
        config.set("new_key", "new_value")
        config.unset("key2")
        
        config.save()
        
        assert source1._data["key1"] == "modified"
        assert source1._data["new_key"] == "new_value"
        assert "key2" not in source2._data
        assert len(config._staged) == 0  # Staged changes cleared
        
    def test_save_to_readonly_source_raises(self):
        """Test that saving to read-only source raises error."""
        source = MockSource("s1", {})
        config = Config([RegisteredSource(source=source, is_writable=False)])
        
        config.set("key", "value")
        
        with pytest.raises(PermissionError, match="not writable"):
            config.save()
            
    def test_resolve_target_source_no_sources(self):
        """Test resolving target source with no sources registered."""
        config = Config([])
        
        with pytest.raises(ValueError, match="No sources registered"):
            config._resolve_target_source_id("key", None)
            
    def test_save_to_github_dry_run(self):
        """Test save_to_github with dry_run."""
        source = MockSource("s1", {"key1": "value1", "key2": "value2"})
        config = Config([RegisteredSource(source=source)])
        config.materialize()
        
        with patch("confetti.core.config.GitHubEnvSource") as mock_gh:
            mock_gh_instance = MagicMock()
            mock_gh_instance.get.side_effect = lambda k: {
                "key1": "old_value",
                "key3": "value3"
            }.get(k)
            mock_gh_instance.keys.return_value = ["key1", "key3"]
            mock_gh.return_value = mock_gh_instance
            
            result = config.save_to_github(
                "github://owner/repo#env", 
                dry_run=True
            )
            
            assert result["set"]["key1"] == "value1"  # Changed
            assert result["set"]["key2"] == "value2"  # New
            assert result["delete"] == ["key3"]  # Removed
            
    def test_save_to_github_apply(self):
        """Test save_to_github without dry_run."""
        source = MockSource("s1", {"key1": "value1"})
        config = Config([RegisteredSource(source=source)])
        config.materialize()
        
        with patch("confetti.core.config.GitHubEnvSource") as mock_gh:
            mock_gh_instance = MagicMock()
            mock_gh.return_value = mock_gh_instance
            
            result = config.save_to_github("github://owner/repo#env")
            
            assert result == {}
            mock_gh_instance.load.assert_called_once()
            mock_gh_instance.set.assert_called_with("key1", "value1")
            mock_gh_instance.save.assert_called_once()
            
    def test_values_materializes_if_needed(self):
        """Test that values() materializes config if not done yet."""
        source = MockSource("s1", {"key": "value"})
        config = Config([RegisteredSource(source=source)])
        
        # Should materialize automatically
        values = config.values()
        assert values == {"key": "value"}
        assert config._effective == {"key": "value"}
        
    def test_get_materializes_if_needed(self):
        """Test that get() materializes config if not done yet."""
        source = MockSource("s1", {"key": "value"})
        config = Config([RegisteredSource(source=source)])
        
        # Should materialize automatically
        value = config.get("key")
        assert value == "value"
        assert config._effective == {"key": "value"}
        
    def test_provenance_materializes_if_needed(self):
        """Test that provenance() materializes config if not done yet."""
        source = MockSource("s1", {"key": "value"})
        config = Config([RegisteredSource(source=source)])
        
        # Should materialize automatically
        prov = config.provenance("key")
        assert prov is not None
        assert prov.source_id == "s1"
        assert config._effective == {"key": "value"}
"""Tests for confetti.yaml configuration loading."""

import re
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from confetti.core.config_loader import ConfigLoader
from confetti.core.environment import Environment
from confetti.core.filters import Filter


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_init_with_explicit_path(self, tmp_path):
        """Test initialization with explicit config path."""
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text("environments: {}")

        loader = ConfigLoader(config_file)
        assert loader.config_path == config_file

    def test_init_with_nonexistent_explicit_path(self, tmp_path):
        """Test initialization with nonexistent explicit path."""
        config_file = tmp_path / "nonexistent.yaml"

        loader = ConfigLoader(config_file)
        assert loader.config_path is None

    def test_find_config_in_current_dir(self, tmp_path, monkeypatch):
        """Test finding confetti.yaml in current directory."""
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text("environments: {}")
        monkeypatch.chdir(tmp_path)

        loader = ConfigLoader()
        assert loader.config_path == config_file

    def test_find_config_in_parent_dir(self, tmp_path, monkeypatch):
        """Test finding confetti.yaml in parent directory."""
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text("environments: {}")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        loader = ConfigLoader()
        assert loader.config_path == config_file

    def test_no_config_file_found(self, tmp_path, monkeypatch):
        """Test when no confetti.yaml is found."""
        monkeypatch.chdir(tmp_path)

        loader = ConfigLoader()
        assert loader.config_path is None

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_data = {
            "environments": {
                "production": {
                    "sources": [
                        {"path": "./config.yaml"},
                        {"uri": "redis://localhost:6379"},
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        loader = ConfigLoader(config_file)
        loaded = loader.load()
        assert loaded == config_data

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading an invalid YAML file."""
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text("invalid: yaml: content: [")

        loader = ConfigLoader(config_file)
        with pytest.raises(ValueError, match="Invalid confetti.yaml"):
            loader.load()

    def test_load_with_read_error(self, tmp_path):
        """Test graceful handling of read errors."""
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text("test: data")
        config_file.chmod(0o000)  # Remove read permissions

        loader = ConfigLoader(config_file)
        result = loader.load()
        assert result == {}  # Should return empty dict on error

        # Restore permissions for cleanup
        config_file.chmod(0o644)

    def test_get_environment_config(self, tmp_path):
        """Test getting configuration for a specific environment."""
        config_data = {
            "environments": {
                "production": {"sources": [{"path": "prod.yaml"}]},
                "development": {"sources": [{"path": "dev.yaml"}]},
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        loader = ConfigLoader(config_file)
        prod_config = loader.get_environment_config("production")
        assert prod_config == {"sources": [{"path": "prod.yaml"}]}

        dev_config = loader.get_environment_config("development")
        assert dev_config == {"sources": [{"path": "dev.yaml"}]}

        missing_config = loader.get_environment_config("staging")
        assert missing_config is None

    def test_get_sources(self, tmp_path):
        """Test getting sources for an environment."""
        config_data = {
            "environments": {
                "production": {
                    "sources": [
                        {"path": "./config.yaml", "depth": 3},
                        {"uri": "redis://localhost:6379", "writable": True},
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        loader = ConfigLoader(config_file)
        sources = loader.get_sources("production")
        assert len(sources) == 2
        assert sources[0] == {"path": "./config.yaml", "depth": 3}
        assert sources[1] == {"uri": "redis://localhost:6379", "writable": True}

        # Test nonexistent environment
        sources = loader.get_sources("nonexistent")
        assert sources == []

    def test_parse_source_with_path(self):
        """Test parsing source configuration with path."""
        loader = ConfigLoader()
        source_config = {
            "path": "./config.yaml",
            "name": "Main Config",
            "depth": 3,
            "writable": False,
        }

        parsed = loader.parse_source(source_config)
        assert parsed["path_or_uri"] == Path("./config.yaml")
        assert parsed["name"] == "Main Config"
        assert parsed["depth"] == 3
        assert parsed["is_writable"] is False

    def test_parse_source_with_uri(self):
        """Test parsing source configuration with URI."""
        loader = ConfigLoader()
        source_config = {"uri": "redis://localhost:6379", "writable": True}

        parsed = loader.parse_source(source_config)
        assert parsed["path_or_uri"] == "redis://localhost:6379"
        assert parsed["is_writable"] is True

    def test_parse_source_missing_path_and_uri(self):
        """Test parsing source without path or URI raises error."""
        loader = ConfigLoader()
        source_config = {"name": "Invalid"}

        with pytest.raises(ValueError, match="must have either 'path' or 'uri'"):
            loader.parse_source(source_config)

    def test_parse_source_with_filter(self):
        """Test parsing source with filter configuration."""
        loader = ConfigLoader()
        source_config = {
            "path": "./config.yaml",
            "filter": {
                "include_regex": "^(DATABASE_|REDIS_)",
                "hierarchical_spec": {"database": True, "redis": {"host": True}},
                "depth": 2,
            },
        }

        parsed = loader.parse_source(source_config)
        assert "filter" in parsed
        filter_obj = parsed["filter"]
        assert isinstance(filter_obj, Filter)
        assert filter_obj.include_regex.pattern == "^(DATABASE_|REDIS_)"
        assert filter_obj.hierarchical_spec == {
            "database": True,
            "redis": {"host": True},
        }
        assert filter_obj.depth == 2

    def test_parse_source_depth_at_source_level(self):
        """Test parsing source with depth at source level."""
        loader = ConfigLoader()
        source_config = {"path": "./config.yaml", "depth": 5}

        parsed = loader.parse_source(source_config)
        assert parsed["depth"] == 5

    def test_parse_source_depth_in_filter(self):
        """Test parsing source with depth in filter."""
        loader = ConfigLoader()
        source_config = {"path": "./config.yaml", "filter": {"depth": 3}}

        parsed = loader.parse_source(source_config)
        assert parsed["depth"] == 3


class TestEnvironmentWithConfettiYaml:
    """Test Environment integration with confetti.yaml."""

    def test_environment_loads_from_config_file(self, tmp_path, monkeypatch):
        """Test Environment loads sources from confetti.yaml."""
        # Create test files
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("database:\n  host: localhost")
        json_file = tmp_path / "config.json"
        json_file.write_text('{"api": {"key": "secret"}}')

        # Create confetti.yaml
        config_data = {
            "environments": {
                "production": {
                    "sources": [
                        {"path": str(yaml_file)},
                        {"path": str(json_file), "depth": 2},
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        monkeypatch.chdir(tmp_path)

        # Create environment
        env = Environment("production")
        assert len(env._registered) == 2
        assert env.config_file_path == config_file

    def test_environment_merges_explicit_sources(self, tmp_path, monkeypatch):
        """Test Environment merges explicit sources with confetti.yaml."""
        # Create test files
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key1: value1")
        json_file = tmp_path / "config.json"
        json_file.write_text('{"key2": "value2"}')
        env_file = tmp_path / ".env"
        env_file.write_text("KEY3=value3")

        # Create confetti.yaml with two sources
        config_data = {
            "environments": {
                "development": {
                    "sources": [
                        {"path": str(yaml_file)},
                        {"path": str(json_file)},
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        monkeypatch.chdir(tmp_path)

        # Create environment with additional explicit source
        env = Environment("development", sources=[str(env_file)])
        assert len(env._registered) == 3  # 2 from confetti.yaml + 1 explicit

        # Verify all sources are loaded
        config = env.get_config()
        assert "key1" in config.values()
        assert "key2" in config.values()
        assert "KEY3" in config.values()

    def test_environment_handles_missing_config_file(self, tmp_path, monkeypatch):
        """Test Environment works without confetti.yaml."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")

        monkeypatch.chdir(tmp_path)

        # Should work fine without confetti.yaml
        env = Environment("production", sources=[str(env_file)])
        assert len(env._registered) == 1
        assert env.config_file_path is None

        config = env.get_config()
        assert config.get("KEY") == "value"

    def test_environment_handles_invalid_source_gracefully(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test Environment handles invalid sources in confetti.yaml gracefully."""
        # Create confetti.yaml with invalid source
        config_data = {
            "environments": {
                "production": {
                    "sources": [
                        {"path": "/nonexistent/file.yaml"},  # Invalid
                        {"invalid": "source"},  # Missing path/uri
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        monkeypatch.chdir(tmp_path)

        # Should handle errors gracefully
        env = Environment("production")
        captured = capsys.readouterr()
        assert "Warning:" in captured.out
        # Environment should still be created
        assert env is not None

    def test_environment_with_filter_from_config(self, tmp_path, monkeypatch):
        """Test Environment loads sources with filters from confetti.yaml."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            """
database:
  host: localhost
  password: secret
redis:
  host: redis.local
api:
  key: apikey
"""
        )

        config_data = {
            "environments": {
                "production": {
                    "sources": [
                        {
                            "path": str(yaml_file),
                            "filter": {
                                "include_regex": "^(database|redis)",
                                "depth": 2,
                            },
                        }
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        monkeypatch.chdir(tmp_path)

        env = Environment("production")
        config = env.get_config()

        # Should include database and redis keys
        assert "database.host" in config.values()
        assert "redis.host" in config.values()
        # Should exclude api keys due to filter
        assert "api.key" not in config.values()

    def test_environment_with_custom_config_path(self, tmp_path):
        """Test Environment with custom config file path."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value")

        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        config_data = {
            "environments": {
                "staging": {"sources": [{"path": str(yaml_file)}]}
            }
        }
        config_file = custom_dir / "my-config.yaml"
        config_file.write_text(yaml.dump(config_data))

        # Use custom config path
        env = Environment("staging", config_path=config_file)
        assert env.config_file_path == config_file
        assert len(env._registered) == 1

    def test_environment_precedence_order(self, tmp_path, monkeypatch):
        """Test source precedence with confetti.yaml and explicit sources."""
        # Create files with overlapping keys
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: from_yaml")
        json_file = tmp_path / "config.json"
        json_file.write_text('{"key": "from_json"}')
        env_file = tmp_path / ".env"
        env_file.write_text("key=from_env")

        # confetti.yaml defines yaml and json sources
        config_data = {
            "environments": {
                "test": {
                    "sources": [
                        {"path": str(yaml_file)},
                        {"path": str(json_file)},
                    ]
                }
            }
        }
        config_file = tmp_path / "confetti.yaml"
        config_file.write_text(yaml.dump(config_data))

        monkeypatch.chdir(tmp_path)

        # Add env file as explicit source
        env = Environment("test", sources=[str(env_file)])
        config = env.get_config()

        # Last source (env_file) should win
        assert config.get("key") == "from_env"


# Simple test runner for when pytest is not available
if __name__ == "__main__":
    import sys
    import tempfile
    from pathlib import Path
    import os

    class MockMonkeypatch:
        """Simple monkeypatch replacement."""

        def __init__(self):
            self.original_cwd = os.getcwd()

        def chdir(self, path):
            """Change directory."""
            os.chdir(path)

        def __del__(self):
            """Restore original directory."""
            os.chdir(self.original_cwd)

    class MockCapsys:
        """Simple capsys replacement."""

        def __init__(self):
            self.out = ""
            self.err = ""

        def readouterr(self):
            """Return captured output."""
            import io
            import contextlib

            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                pass
            return self

    print("Running tests without pytest...")
    test_loader = TestConfigLoader()
    test_env = TestEnvironmentWithConfettiYaml()

    # Run a few basic tests
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        monkeypatch = MockMonkeypatch()

        # Test ConfigLoader
        test_loader.test_init_with_explicit_path(tmp_path)
        test_loader.test_init_with_nonexistent_explicit_path(tmp_path)
        test_loader.test_parse_source_with_path()

        # Test Environment
        test_env.test_environment_handles_missing_config_file(tmp_path, monkeypatch)

        print("✓ Basic tests passed!")
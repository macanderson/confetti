"""Unit tests for the Environment class."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from confetti.core.environment import Environment
from confetti.core.filters import Filter


class TestEnvironment:
    """Test suite for Environment class."""
    
    def test_init(self):
        """Test Environment initialization."""
        env = Environment("production")
        assert env.name == "production"
        assert env._registered == []
        
    def test_register_sources_multiple(self, tmp_path):
        """Test registering multiple sources."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value")
        
        json_file = tmp_path / "config.json"
        json_file.write_text('{"key": "value"}')
        
        env = Environment("dev")
        env.register_sources(env_file, yaml_file, json_file)
        
        assert len(env._registered) == 3
        
    def test_register_source_with_options(self, tmp_path):
        """Test registering a source with options."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        
        env = Environment("dev")
        filter_obj = Filter(include_regex=None)
        
        env.register_source(
            env_file,
            filter=filter_obj,
            depth=2,
            name="custom_name",
            is_writable=False
        )
        
        assert len(env._registered) == 1
        rs = env._registered[0]
        assert rs.filter == filter_obj
        assert rs.depth == 2
        assert rs.source.name == "custom_name"
        assert rs.is_writable is False
        
    def test_create_source_env_file(self, tmp_path):
        """Test creating an env file source."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        
        env = Environment("dev")
        source = env._create_source(env_file, None)
        
        from confetti.sources.env_file import EnvFileSource
        assert isinstance(source, EnvFileSource)
        assert source.path == env_file
        
    def test_create_source_env_file_no_extension(self, tmp_path):
        """Test creating an env file source without extension."""
        env_file = tmp_path / "envfile"
        env_file.write_text("KEY=value")
        
        env = Environment("dev")
        source = env._create_source(env_file, None)
        
        from confetti.sources.env_file import EnvFileSource
        assert isinstance(source, EnvFileSource)
        
    def test_create_source_yaml(self, tmp_path):
        """Test creating a YAML source."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value")
        
        env = Environment("dev")
        source = env._create_source(yaml_file, None)
        
        from confetti.sources.yaml_file import YamlFileSource
        assert isinstance(source, YamlFileSource)
        assert source.path == yaml_file
        
    def test_create_source_yml(self, tmp_path):
        """Test creating a YAML source with .yml extension."""
        yml_file = tmp_path / "config.yml"
        yml_file.write_text("key: value")
        
        env = Environment("dev")
        source = env._create_source(yml_file, None)
        
        from confetti.sources.yaml_file import YamlFileSource
        assert isinstance(source, YamlFileSource)
        
    def test_create_source_json(self, tmp_path):
        """Test creating a JSON source."""
        json_file = tmp_path / "config.json"
        json_file.write_text('{"key": "value"}')
        
        env = Environment("dev")
        source = env._create_source(json_file, None)
        
        from confetti.sources.json_file import JsonFileSource
        assert isinstance(source, JsonFileSource)
        assert source.path == json_file
        
    def test_create_source_ini(self, tmp_path):
        """Test creating an INI source."""
        ini_file = tmp_path / "config.ini"
        ini_file.write_text("[section]\nkey=value")
        
        env = Environment("dev")
        source = env._create_source(ini_file, None)
        
        from confetti.sources.ini_file import IniFileSource
        assert isinstance(source, IniFileSource)
        assert source.path == ini_file
        
    def test_create_source_redis(self):
        """Test creating a Redis source."""
        env = Environment("dev")
        
        with patch("confetti.sources.redis_kv.redis.Redis"):
            source = env._create_source("redis://localhost:6379", None)
            
        from confetti.sources.redis_kv import RedisKeyValueSource
        assert isinstance(source, RedisKeyValueSource)
        assert source.uri == "redis://localhost:6379"
        
    def test_create_source_github(self):
        """Test creating a GitHub source."""
        env = Environment("dev")
        
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            source = env._create_source(
                "github://owner/repo#production", 
                None
            )
            
        from confetti.sources.github_env import GitHubEnvSource
        assert isinstance(source, GitHubEnvSource)
        assert source.uri == "github://owner/repo#production"
        
    def test_create_source_unsupported(self):
        """Test creating an unsupported source type."""
        env = Environment("dev")
        
        with pytest.raises(ValueError, match="Unsupported source type"):
            env._create_source("unknown://source", None)
            
    def test_create_source_nonexistent_file(self, tmp_path):
        """Test creating source for non-existent file."""
        env = Environment("dev")
        nonexistent = tmp_path / "nonexistent.unknown"
        
        with pytest.raises(ValueError, match="Unsupported source type"):
            env._create_source(nonexistent, None)
            
    def test_get_config(self, tmp_path):
        """Test getting a Config object."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2")
        
        env = Environment("dev")
        env.register_source(env_file)
        
        config = env.get_config()
        assert config.get("KEY1") == "value1"
        assert config.get("KEY2") == "value2"
        assert len(config.registered_sources) == 1
        
    def test_add_source_type(self):
        """Test adding a custom source type."""
        env = Environment("dev")
        
        mock_source = MagicMock()
        mock_source.id = "custom"
        mock_source.name = "Custom Source"
        
        env.add_source_type(mock_source)
        
        assert len(env._registered) == 1
        assert env._registered[0].source == mock_source
        assert env._registered[0].is_writable is True
        
    def test_register_source_default_writable(self, tmp_path):
        """Test that sources are writable by default."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        
        env = Environment("dev")
        env.register_source(env_file)
        
        assert env._registered[0].is_writable is True
        
    def test_create_source_with_custom_name(self, tmp_path):
        """Test creating source with custom name."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        
        env = Environment("dev")
        source = env._create_source(env_file, "my_custom_name")
        
        assert source.name == "my_custom_name"
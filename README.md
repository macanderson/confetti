# Confetti 🎉 - Environment-aware Configuration Management for Python 🐍

[![PyPI Version](https://img.shields.io/pypi/v/confetti)](https://pypi.org/project/confetti/)
[![Python Versions](https://img.shields.io/pypi/pyversions/confetti)](https://pypi.org/project/confetti/)
[![License](https://img.shields.io/github/license/confetti-dev/confetti)](https://github.com/confetti-dev/confetti/blob/main/LICENSE)
[![Tests](https://github.com/confetti-dev/confetti/workflows/Tests/badge.svg)](https://github.com/confetti-dev/confetti/actions)
[![Coverage](https://codecov.io/gh/confetti-dev/confetti/branch/main/graph/badge.svg)](https://codecov.io/gh/confetti-dev/confetti)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://confetti.readthedocs.io)

**Confetti** is a powerful Python library for managing configuration from multiple sources with ease. It allows you to load configuration variables and secrets from various sources (environment files, JSON, YAML, INI, Redis, GitHub Actions) and merge them into a unified configuration object with conflict resolution, type conversion, and source tracking.

## ✨ Features

- **📁 Multiple Configuration Sources**: Support for `.env`, JSON, YAML, INI files, Redis, and GitHub environment variables
- **🔄 Automatic Merging**: Intelligently merge configurations from multiple sources with configurable precedence
- **🔍 Source Tracking**: Track where each configuration value came from with detailed provenance
- **🎯 Flexible Filtering**: Use regex patterns and hierarchical specs to include/exclude configuration keys
- **💾 Two-way Sync**: Not just read - write back changes to configuration sources
- **🔧 Type Safety**: Automatic type conversion and validation
- **🌍 Environment Management**: Organize configurations by environment (development, staging, production)
- **⚡ Async Support**: Async/await support for remote sources
- **🔌 Extensible**: Easy to add custom configuration sources
- **📦 Zero Config**: Works out of the box with sensible defaults

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration Sources](#configuration-sources)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [CLI Usage](#cli-usage)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Installation

### Using pip

```bash
pip install confetti
```

### Using uv (recommended)

```bash
uv add confetti
```

### Using Poetry

```bash
poetry add confetti
```

### Development Installation

```bash
git clone https://github.com/confetti-dev/confetti.git
cd confetti
pip install -e ".[dev]"
```

## 🎯 Quick Start

### Basic Usage

```python
from confetti import Config, Environment
from pathlib import Path

# Create an environment
env = Environment("development")

# Register configuration sources (in order of precedence)
env.register_sources(
    Path(".env"),                    # Local environment variables
    Path("config/base.yaml"),        # Base configuration
    Path("config/development.json"), # Environment-specific config
)

# Get merged configuration
config = env.get_config()

# Access configuration values
database_url = config.get("DATABASE_URL")
debug_mode = config.get("DEBUG", default=False)

# Get all configuration as a dictionary
all_config = config.values()
```

### Direct Config Usage

```python
from confetti import Config
from confetti.sources import EnvFileSource, YamlFileSource

# Create sources directly
env_source = EnvFileSource(Path(".env"))
yaml_source = YamlFileSource(Path("config.yaml"))

# Create config with registered sources
config = Config([
    RegisteredSource(source=env_source),
    RegisteredSource(source=yaml_source),
])

# Materialize and use
config.materialize()
print(config.get("API_KEY"))
```

## 📚 Configuration Sources

### Environment Files (.env)

```python
from pathlib import Path

env.register_source(Path(".env"))
env.register_source(Path(".env.local"))  # Local overrides
```

**.env file example:**
```bash
DATABASE_URL=postgresql://localhost:5432/mydb
REDIS_URL=redis://localhost:6379
API_KEY=secret_key_123
DEBUG=true
```

### YAML Files

```python
env.register_source(Path("config.yaml"))
```

**config.yaml example:**
```yaml
database:
  host: localhost
  port: 5432
  name: myapp
  pool_size: 10

cache:
  backend: redis
  ttl: 3600

features:
  - authentication
  - notifications
  - analytics
```

### JSON Files

```python
env.register_source(Path("settings.json"))
```

**settings.json example:**
```json
{
  "api": {
    "version": "v1",
    "timeout": 30,
    "rate_limit": 1000
  },
  "features": {
    "dark_mode": true,
    "beta_features": false
  }
}
```

### INI Files

```python
env.register_source(Path("config.ini"))
```

**config.ini example:**
```ini
[database]
host = localhost
port = 5432

[cache]
backend = redis
ttl = 3600
```

### Redis Key-Value Store

```python
env.register_source("redis://localhost:6379")

# With authentication and database selection
env.register_source("redis://user:password@localhost:6379/0")

# With key prefix
from confetti.sources import RedisKeyValueSource
redis_source = RedisKeyValueSource(
    "redis://localhost:6379",
    prefix="myapp:"
)
```

### GitHub Environment Variables

```python
import os

# Requires GITHUB_TOKEN environment variable
env.register_source("github://owner/repo#production")

# Or provide token explicitly
from confetti.sources import GitHubEnvSource
github_source = GitHubEnvSource(
    "github://owner/repo#production",
    token="ghp_your_token_here"
)
```

## 🔧 Advanced Usage

### Filtering Configuration Keys

```python
import re
from confetti import Filter

# Include only database-related keys
env.register_source(
    Path(".env"),
    filter=Filter(include_regex=re.compile(r"^DB_.*"))
)

# Hierarchical filtering for structured sources
env.register_source(
    Path("config.yaml"),
    filter=Filter(hierarchical_spec={
        "database": {
            "host": True,
            "port": True,
            # "password": False  # Exclude password
        }
    })
)

# Limit nesting depth
env.register_source(
    Path("deeply_nested.json"),
    depth=2  # Only flatten up to 2 levels deep
)
```

### Source Precedence and Merging

```python
# Sources registered later override earlier ones
env.register_sources(
    Path("config/base.yaml"),     # 1. Base configuration
    Path("config/prod.yaml"),     # 2. Production overrides
    Path(".env"),                 # 3. Environment variables (highest precedence)
)

config = env.get_config()

# Check where a value came from
provenance = config.provenance("DATABASE_URL")
if provenance:
    print(f"DATABASE_URL came from: {provenance.source_id}")
    print(f"Loaded at: {provenance.timestamp_loaded}")
```

### Writing Configuration Changes

```python
# Make changes
config.set("API_KEY", "new_secret_key")
config.set("DEBUG", False)
config.unset("DEPRECATED_SETTING")

# Save changes back to sources
config.save()

# Or save to specific source
config.set("REDIS_URL", "redis://newhost:6379", source="path/to/.env")
config.save()
```

### Custom Configuration Sources

```python
from confetti.core.source import Source
from typing import Dict, Any, Optional

class CustomSource:
    """Example custom configuration source."""
    
    def __init__(self, source_id: str):
        self.id = source_id
        self.name = f"custom:{source_id}"
        self.extension = None
        self._data = {}
        
    def load(self, filter=None, depth=None) -> Dict[str, Any]:
        # Load your configuration here
        return self._data
        
    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)
        
    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        
    def save(self) -> None:
        # Persist changes
        pass
        
    # ... implement other required methods ...

# Use custom source
custom = CustomSource("my_custom_source")
env.add_source_type(custom)
```

### GitHub Environment Sync

```python
# Sync local config to GitHub environment
config = env.get_config()

# Dry run to see what would change
changes = config.save_to_github(
    "github://owner/repo#production",
    dry_run=True
)
print(f"Would set: {changes['set']}")
print(f"Would delete: {changes['delete']}")

# Apply changes
config.save_to_github("github://owner/repo#production")
```

### Environment-based Configuration

```python
import os

# Determine environment
current_env = os.getenv("APP_ENV", "development")

# Create environment-specific configuration
env = Environment(current_env)

# Load base config and environment-specific overrides
env.register_sources(
    Path("config/base.yaml"),
    Path(f"config/{current_env}.yaml"),
    Path(".env.local"),  # Local overrides (not in version control)
)

config = env.get_config()
```

## 📖 API Reference

### Core Classes

#### `Environment`

Manages configuration sources for a specific environment.

```python
env = Environment(name: str)
env.register_source(path_or_uri, filter=None, depth=None, name=None, is_writable=True)
env.register_sources(*paths_or_uris)
env.get_config() -> Config
env.add_source_type(source: Source)
```

#### `Config`

Unified configuration object with source tracking.

```python
config.get(key: str, default=None) -> Any
config.values() -> Dict[str, Any]
config.set(key: str, value: Any, source: str = None)
config.unset(key: str)
config.save()
config.reload()
config.provenance(key: str) -> ProvenanceRecord
config.remove_source(source_id: str)
config.save_to_github(uri: str, token: str = None, dry_run: bool = False)
```

#### `Filter`

Filtering rules for configuration keys.

```python
Filter(
    include_regex: Pattern = None,
    hierarchical_spec: Dict = None,
    depth: int = None
)
```

### Source Classes

All sources implement the `Source` protocol with these methods:

- `load(filter=None, depth=None) -> Dict[str, Any]`
- `get(key: str) -> Any`
- `set(key: str, value: Any)`
- `unset(key: str)`
- `save()`
- `reload()`
- `exists(key: str) -> bool`
- `keys() -> List[str]`
- `values() -> Dict[str, Any]`
- `clear()`
- `size() -> int`

## 💻 CLI Usage

Confetti includes a CLI for managing configurations:

```bash
# List all configuration sources
confetti sources-list --env production

# Get a specific configuration value
confetti get DATABASE_URL --env production

# Set a configuration value
confetti set API_KEY "new_key" --env production --save

# Remove a configuration value
confetti unset DEBUG_MODE --env production --save

# Sync to GitHub
confetti sync-github github://owner/repo#production --env local --dry-run
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/confetti-dev/confetti.git
cd confetti

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=confetti --cov-report=html

# Run linting
ruff check .
black --check .
mypy confetti

# Format code
black .
ruff --fix .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [python-dotenv](https://github.com/theskumar/python-dotenv) and [python-decouple](https://github.com/henriquebastos/python-decouple)
- Built with modern Python best practices
- Special thanks to all contributors

## 🔗 Links

- [PyPI Package](https://pypi.org/project/confetti/)
- [GitHub Repository](https://github.com/confetti-dev/confetti)
- [Documentation](https://confetti.readthedocs.io)
- [Issue Tracker](https://github.com/confetti-dev/confetti/issues)
- [Changelog](CHANGELOG.md)

## 📊 Project Status

- ✅ Production Ready
- ✅ Actively Maintained
- ✅ Semantic Versioning
- ✅ Security Updates

---

<p align="center">Made with ❤️ by the 02Beta Team</p>

## Configuration File (`confetti.yaml`)

Confetti supports defining configuration sources in a YAML file called `confetti.yaml`. This file can be placed in your project root directory or any parent directory, and will be automatically discovered when creating an Environment.

### Basic Usage

Create a `confetti.yaml` file in your project root:

```yaml
environments:
  production:
    sources:
      - path: ./config.yaml
      - path: ./secrets.env
      - uri: redis://localhost:6379
        writable: true
<<<<<<< Updated upstream
  
=======

>>>>>>> Stashed changes
  development:
    sources:
      - path: ./config.dev.yaml
      - path: ./.env.local
```

Then in your Python code:

```python
from confetti import Environment

# Automatically loads sources from confetti.yaml for the "production" environment
env = Environment("production")
config = env.get_config()
```

### Merging with Explicit Sources

You can combine sources from `confetti.yaml` with explicitly provided sources:

```python
# Sources from confetti.yaml are loaded first, then these are added
env = Environment("production", sources=["./override.env"])
```

### Using Filters

Filters allow you to selectively load configuration keys:

```yaml
environments:
  production:
    sources:
      - path: ./config.yaml
        filter:
          include_regex: "^(DATABASE_|REDIS_)"  # Only load keys starting with DATABASE_ or REDIS_
          depth: 3  # Maximum nesting depth for hierarchical data
<<<<<<< Updated upstream
      
=======

>>>>>>> Stashed changes
      - path: ./app-config.json
        filter:
          hierarchical_spec:  # Selectively include nested keys
            database:
              host: true
              port: true
            api:
              endpoint: true
```

### Custom Config File Location

You can specify a custom location for the configuration file:

```python
env = Environment("staging", config_path="./config/my-config.yaml")
```

## `confetti.yaml` Schema Reference

The `confetti.yaml` file follows this schema:

```yaml
# Root level - contains environments
environments:
  # Environment name (e.g., production, development, staging)
  <environment_name>:
    # List of configuration sources for this environment
    sources:
      # Each source is an object with these properties
      - # Source location (one of these is required)
        path: <string>  # File path (relative or absolute)
        uri: <string>   # URI for remote sources (e.g., redis://...)
<<<<<<< Updated upstream
        
=======

>>>>>>> Stashed changes
        # Optional source properties
        name: <string>  # Human-readable name for the source
        writable: <boolean>  # Whether this source can be written to (default: true)
        depth: <integer>  # Maximum depth for nested structure parsing
<<<<<<< Updated upstream
        
=======

>>>>>>> Stashed changes
        # Filter configuration (optional)
        filter:
          # Include keys matching this regex pattern
          include_regex: <string>
<<<<<<< Updated upstream
          
          # Depth limit for nested structures (can also be at source level)
          depth: <integer>
          
=======

          # Depth limit for nested structures (can also be at source level)
          depth: <integer>

>>>>>>> Stashed changes
          # Hierarchical specification for selective inclusion
          # Use true to include a key/path, nested objects to go deeper
          hierarchical_spec:
            <key>: true | <nested_spec>
```

### Complete Example

Here's a comprehensive example showing various configuration options:

```yaml
environments:
  production:
    sources:
      # YAML configuration with regex filter
      - path: ./config/production.yaml
        name: "Main Config"
        filter:
          include_regex: "^(DATABASE_|API_|CACHE_)"
          depth: 3
<<<<<<< Updated upstream
      
=======

>>>>>>> Stashed changes
      # JSON file with hierarchical filtering
      - path: ./config/services.json
        filter:
          hierarchical_spec:
            database:
              primary:
                host: true
                port: true
                credentials: true
            cache:
              redis: true
            monitoring: false  # Exclude monitoring config
<<<<<<< Updated upstream
      
      # Environment file (no filtering)
      - path: ./.env.production
        writable: false  # Read-only source
      
=======

      # Environment file (no filtering)
      - path: ./.env.production
        writable: false  # Read-only source

>>>>>>> Stashed changes
      # Redis for dynamic configuration
      - uri: redis://prod-redis:6379/0
        name: "Dynamic Config"
        writable: true
<<<<<<< Updated upstream
      
=======

>>>>>>> Stashed changes
      # GitHub environment (when implemented)
      - uri: github://myorg/myrepo#production
        name: "GitHub Secrets"
        writable: false

  development:
    sources:
      - path: ./config/development.yaml
      - path: ./.env.local
        writable: true
<<<<<<< Updated upstream
      
=======

>>>>>>> Stashed changes
  testing:
    sources:
      - path: ./config/test.yaml
        filter:
          include_regex: "^TEST_"
      - path: ./.env.test
```

### Filter Examples

#### Regex Filter
<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
```yaml
filter:
  include_regex: "^(DB_|API_)"  # Only keys starting with DB_ or API_
```

<<<<<<< Updated upstream
#### Hierarchical Filter
=======
#### Hierarchical

>>>>>>> Stashed changes
```yaml
filter:
  hierarchical_spec:
    database:  # Include all database.* keys
      host: true  # Include database.host
      port: true  # Include database.port
      pool:  # Include specific pool settings
        size: true
        timeout: true
    api: true  # Include all api.* keys
    internal: false  # Exclude all internal.* keys
```

#### Depth Limiting
<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
```yaml
filter:
  depth: 2  # Only parse up to 2 levels deep
```

### Source Precedence

Sources are loaded in the order they appear in the configuration file. Later sources override earlier ones for the same keys:

```yaml
environments:
  production:
    sources:
      - path: ./defaults.yaml  # Loaded first
      - path: ./overrides.yaml  # Loaded second, overrides defaults
      - uri: redis://localhost:6379  # Loaded last, highest precedence
```

### Error Handling

Confetti handles configuration errors gracefully:

- **Missing file**: If `confetti.yaml` doesn't exist, the Environment works normally with explicit sources
- **Invalid source**: If a source in `confetti.yaml` can't be loaded, a warning is printed but other sources continue loading
- **Invalid YAML**: If `confetti.yaml` contains invalid YAML syntax, an error is raised
- **Missing environment**: If the requested environment isn't in `confetti.yaml`, no sources are loaded from the file

### Best Practices

1. **Keep secrets separate**: Use different source files for secrets vs. non-sensitive configuration
2. **Use filters**: Limit what each source exposes to reduce the attack surface
3. **Environment-specific files**: Create separate configuration files for each environment
4. **Source ordering**: Place default/base configurations first, overrides last
5. **Writable sources**: Mark sources as read-only (`writable: false`) when they shouldn't be modified
6. **Depth limits**: Use depth limits to prevent excessive nesting in hierarchical data

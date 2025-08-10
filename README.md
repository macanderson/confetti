# Confetti 🎉 - Environment-aware Configuration Management for Python 🐍

Confetti is a cli tool and a python library that enables developers to source configuration variables and secrets from multiple sources into unified configuration objects using Github environments to sync configurations across multiple environments and hosting services.

## Getting Started

To get started, install the package globally to use the cli:

```bash
pip install -U confetti
```

or use it as a python library:

```python
from confetti import Environment, Config
from pathlib import Path


environment = Environment("production")

# add as many sources of config as you want, they will be loaded
# in order and the last one will override the previous ones,
# and merged into a single config object retrievable by the function
# `environment.get_config()` which returns a `Config` object.
# config files can include filters to only load certain keys matched by
# a regex pattern exactly like how github has branch protection rules.
# this provides apps with an optimal way to reduce secrets exposure and
# be able to store non-secret static configuration in files that can
# be included in the source code.
environment.register_sources(
  Path.cwd().parent.parent / ".env.local",
  Path.cwd() / "child-directory" / "config.ini",
  Path.cwd() / "config.yaml",
  Path.cwd() / "config.json", # json files can be used to store config in a key-value format, use filters to only load certain keys. filters can be used to parse the keys of its children down to a configurable depth. example: `{"database": {"url": "postgres://postgres:postgres@localhost:5432/postgres"}}` can be parsed down to `{"database": {"url": "postgres://postgres:postgres@localhost:5432/postgres"}}` by using a filter like `{"database": {"url": true}}`
  "redis://localhost:6379",
)

# the program tracks the sources and their filters and retains a memory of which config values
# come from which key in which source, and can be used to get the value of a key from a source.

# the program can also be used to set the value of a key in a source using the memory
# of sources and filters to find the source and key to set the value in.

# example:

config = environment.get_config()
config.set("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/postgres") # sets the value in the config

# or set the value in a specific source:

config.set("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/postgres", source="redis://localhost:6379") # sets the value in the redis key-value store, if the source is not specified, the program will use the default source, which is the first source registered in the array

# if DATABASE_URL is not found in the sources, the program will create a new source
# with the key and value and save it to the sources. If no source is specified, the program
# saves the config to the default source, which is the first source registered in the array
# used to construct the config object (environment.get_config([...])). or Config([...])


config.unset("DATABASE_URL") # removes the key from the config

config.save() # saves the config to the default source, which is the first source registered in the array

# if the config is not saved, the next time the program is run, the value for DATABASE_URL
# will not be set because it was not saved to the source.


config.remove_source("redis://localhost:6379") # removes the redis key-value store from the config

# sources can be registered using file paths or server connection strings.

# only key value stores can be used to set values, and currently only redis is supported.

# the program allows for new custom sources to be created by extending the `Source` class and implementing the `get` and `set` methods.

# example:

from confetti.core.source import Source

# etc...
```

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
        # Optional source properties
        name: <string>  # Human-readable name for the source
        writable: <boolean>  # Whether this source can be written to (default: true)
        depth: <integer>  # Maximum depth for nested structure parsing
        # Filter configuration (optional)
        filter:
          # Include keys matching this regex pattern
          include_regex: <string>

          # Depth limit for nested structures (can also be at source level)
          depth: <integer>

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

      # Environment file (no filtering)
      - path: ./.env.production
        writable: false  # Read-only source

      # Redis for dynamic configuration
      - uri: redis://prod-redis:6379/0
        name: "Dynamic Config"
        writable: true
      # GitHub environment (when implemented)
      - uri: github://myorg/myrepo#production
        name: "GitHub Secrets"
        writable: false

  development:
    sources:
      - path: ./config/development.yaml
      - path: ./.env.local
        writable: true
  testing:
    sources:
      - path: ./config/test.yaml
        filter:
          include_regex: "^TEST_"
      - path: ./.env.test
```

### Filter Examples

#### Regex Filter

```yaml
filter:
  include_regex: "^(DB_|API_)"  # Only keys starting with DB_ or API_
```

#### Hierarchical

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

# Confetti 🎉

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

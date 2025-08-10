# Confetti requirements and technical specification

- Purpose: Implement the Python library and CLI described in this document, so developers can compose configuration from multiple sources (files, key-value stores, GitHub environments), with merge order, filters, provenance tracking, editing and persistence.

- Scope: Python package and CLI only.

## 1) Goals and non-goals

- Goals:
  - Provide the APIs shown in the README for `Environment`, `Config`, and built-in `Source` types.
  - Support file-based sources: `.env`, `.ini`, `.yaml`, `.json`.
  - Support key-value store source: Redis.
  - Support optional GitHub Environments as a source for sync across environments.
  - Provide provenance tracking, filters with regex/depth, merging (last source wins), and persistence via `save()`.
  - Provide a CLI to perform core operations (list/get/set/unset/save/sources management/sync/export/import).
  - Enable custom source types via a clear interface.

- Non-goals (initial release):
  - Web UI or FastAPI service.
  - Advanced schema validation beyond basic type coercion.
  - Multi-tenant auth flows or secret-scanning.

## 2) User-facing behavior

- Python usage should match the README examples, including:

  ```python
  environment = Environment("production")
  # ...
  environment.register_sources(
    Path.cwd().parent.parent / ".env.local",
    Path.cwd() / "child-directory" / "config.ini",
    Path.cwd() / "config.yaml",
    Path.cwd() / "config.json",
    "redis://localhost:6379",
  )
  ```

  - Registering sources accepts paths and connection strings; order matters for merge precedence (later overrides earlier).

- Config operations:
  - `environment.get_config()` returns a `Config`.
  - `config.get(key, default=None)` returns the effective value considering merges.
  - `config.set(key, value, source=None)` stages an in-memory change:
    - If key has provenance, default is to update the original source where the key came from.
    - If no provenance and `source` is None, stage in the default source (the first registered).
    - If `source` is provided, stage in that source (must be a key-value capable source).
  - `config.unset(key)` stages removal in both the effective config and the originating source (per provenance).
  - `config.save()` persists all staged changes to their target sources.
  - `config.remove_source(source_id_or_uri)` removes the source from the environment and recomputes the effective config.
  - `config.reload()` discards staged changes and reloads from all current sources.

- Filters and depth:
  - Each source registration may include an optional filter controlling which keys load and the parse depth for nested objects.
  - Filters: regex-based key matching for flat sources; hierarchical filter spec for structured formats (YAML/JSON).
  - Depth: maximum depth to descend when extracting nested keys from structured formats.

- Provenance:
  - The system must track, for every effective key, (source identifier, source key path) from which the resolved value comes.

- GitHub environments (optional source):
  - Read-only by default; can be made writable for repository variables (not for secrets).
  - Configurable via `GITHUB_TOKEN`, repo `owner/name`, and environment name. Supports listing and pulling environment variables and secrets; secrets are read-only.

## 3) Architecture

- Packages:
  - `confetti/core/`
    - `environment.py`: `Environment`
    - `config.py`: `Config`, `ConfigChange`, `ProvenanceRecord`
    - `source.py`: `Source` ABC/Protocol, `FunctionalSource` adapter, utilities
    - `filters.py`: filter representations and evaluation utilities
    - `merge.py`: merge logic
    - `types.py`: common types
  - `confetti/sources/`
    - `env_file.py`: `.env` source (wrap/extend current `confetti/dotenv.py`)
    - `ini_file.py`: INI source
    - `yaml_file.py`: YAML source
    - `json_file.py`: JSON source
    - `redis_kv.py`: Redis source
    - `github_env.py`: GitHub environments source (optional)
  - `confetti/cli/`
    - `__main__.py`: CLI entrypoint `confetti`
    - `commands/*.py`: subcommands
  - Keep existing `confetti/dotenv.py` but refactor into `sources/env_file.py` and have a thin shim import for backward compatibility if needed.

- Core concepts:
  - `Environment(name: str)`: Holds a list of `RegisteredSource` instances with optional filters and depth.
  - `Config`: Materialized merged view plus staged changes collection; methods for get/set/unset/save/reload and source management operations.
  - `Source`: Interface a source must implement to load/get/set/unset/save/reload/exists/keys/values/clear/size. File sources also implement `path` and `extension`.
  - `Filter`: Combines a regex include pattern and optional explicit hierarchical include spec; `depth` governs nested parsing depth.

## 4) Data model and types

- `Source` interface (Python typing):
  - Required methods:
    - `load(filter: Optional[Filter] = None, depth: Optional[int] = None) -> dict[str, Any]`
    - `get(key: str) -> Optional[Any]`
    - `set(key: str, value: Any) -> None` (stages in-memory)
    - `unset(key: str) -> None` (stages in-memory)
    - `save() -> None`
    - `reload() -> None`
    - `exists(key: str) -> bool`
    - `keys() -> list[str]`
    - `values() -> dict[str, Any]`
    - `clear() -> None`
    - `size() -> int`
  - Identity and metadata:
    - `id: str` (stable identifier; for files use absolute path; for Redis the URI; for GitHub env use `{owner}/{repo}#{environment}`)
    - `name: str`
    - `extension: Optional[str]` for file types

- `RegisteredSource`:
  - `source: Source`
  - `filter: Optional[Filter]`
  - `depth: Optional[int]`
  - `is_writable: bool` (e.g., GitHub secrets false)

- `ProvenanceRecord`:
  - `key: str` effective key
  - `source_id: str`
  - `source_key: str` (for structured data, dot-notated path or JSONPointer)
  - `timestamp_loaded: datetime`

- `ConfigChange`:
  - `op: Literal["set","unset"]`
  - `key: str`
  - `value: Optional[Any]`
  - `target_source_id: str`

- `Filter`:
  - `include_regex: Optional[Pattern[str]]`
  - `hierarchical_spec: Optional[dict[str, Any]]` (boolean leaves indicate include; nested dicts descend)
  - `depth: Optional[int]`

## 5) Merging and precedence

- Load each `RegisteredSource` in order of registration; merge maps into a working dict:
  - For same key collisions, the last source wins.
  - Track provenance: when a key is first set, record source; on override by later source, update provenance to later source.
- For structured sources (YAML/JSON):
  - Flatten nested structures into keys:
    - Default flattening uses dot-notation for nested keys, e.g., `database.url`.
    - Respect `depth`: only descend to `depth` levels; leaves beyond depth are kept as serialized JSON strings unless explicitly filtered by hierarchical spec.
  - Filtering rules:
    - If `hierarchical_spec` is provided, include only specified paths; depth applies after filtering.
    - If `include_regex` is provided, include only keys whose dot-notated path matches the regex.

## 6) Editing and persistence semantics

- `set(key, value, source=None)`:
  - Determine target `source_id`:
    - If `source` provided: target that source. Validate writability; raise if not writable.
    - Else if key has `ProvenanceRecord`: default to its `source_id`.
    - Else: default source = first registered source.
  - Stage `ConfigChange(op="set")`. Update the effective in-memory merged view immediately.
  - `save()`:
    - Group staged changes by target source and call underlying `set/unset` then `save()` on each source. Clear staged changes on success.
- `unset(key)`:
  - If key has provenance, stage `unset` for that `source_id`. Remove from in-memory merged view.
  - If multiple lower-priority sources contain the key, after unsetting in the highest priority source, recompute effective value (it may fall back to the next source). Implementation approach:
    - During `save()`, after applying unsets, re-load sources or re-resolve keys for accuracy.
- `remove_source(id_or_uri)`:
  - Remove the registered source; clear staged changes targeting it; recompute effective merged view and provenance.

## 7) Built-in sources

- Env file (`.env`):
  - Wrap/refactor `confetti/dotenv.py` into a `Source` that can:
    - Load using current parser, support get/set/unset/save/reload.
    - Preserve comments and order where feasible when saving; if not feasible, document overwrite behavior.
  - Support variable expansion as in current `dotenv.py`.

- INI file:
  - Use `configparser`. Flatten as `section.key` for keys. Depth is effectively 2.

- YAML file:
  - Use `pyyaml` safe loader. Parse scalars, lists (serialize lists to JSON for values by default unless filtered for entire subtree), nested dicts flattened per rules.

- JSON file:
  - Use `json` stdlib. Same flattening rules as YAML.

- Redis key-value:
  - Use `redis` Python client. Namespace keys based on optional prefix; values stored as strings.
  - Writable. Support `keys`, `get`, `set`, `delete`, and `save` as no-op or batched pipeline flush.

- GitHub environments (optional):
  - Use `httpx` or `requests`.
  - Read:
    - Repository variables (read/write via REST v3).
    - Environment variables (read/write).
    - Secrets (read-only via Actions secrets endpoints; values cannot be fetched in plaintext—treat as present with value `None` and metadata or skip including secrets entirely unless an encryption workflow is implemented, which is out-of-scope).
  - Provide flag to include/exclude secrets; default exclude.
  - Provide mapping to dot-notated keys.

## 8) CLI specification

- Executable: `confetti`
- Global options:
  - `--env <name>` selects environment (default: `development`)
  - `--config <path>` optional project config for source registrations (see §9)
  - `--source <id_or_uri>` to target specific source when applicable
  - `--json` for JSON output where applicable
  - `-q/--quiet` and `-v/--verbose`
- Commands:
  - `init`:
    - Generates a `confetti.yaml` with example sources and filters.
  - `sources list`:
    - Lists registered sources with ids, types, writable flag, filters, depth.
  - `sources add <path_or_uri> [--filter <regex>] [--depth <n>] [--name <name>]`
  - `sources remove <id_or_uri>`
  - `get <KEY>`:
    - Prints effective value and provenance. JSON mode prints `{"key": "...","value": "...","source":"..."}`
  - `set <KEY> <VALUE> [--source <id_or_uri>]`:
    - Stages change and optionally auto-save with `--save`.
  - `unset <KEY> [--source <id_or_uri>]`
  - `save`:
    - Persists staged changes.
  - `reload`
  - `export [--format json|env|ini|yaml] [--output <path>]`
  - `import <path> [--format auto|json|env|ini|yaml] [--source <id_or_uri>]`
  - `sync github [--owner <owner>] [--repo <repo>] [--environment <name>] [--token <token_env_var_or_value>] [--dry-run]`:
    - Pull variables into a read-only or writable source per flags.
- Exit codes:
  - 0 on success; 1 on user error; 2 on IO/network errors.

## 9) Project configuration file

- `confetti.yaml`:
  - Defines environments and their sources, filters, depth, and default source override.
  - Example:

    ```yaml
    environments:
      production:
        sources:
          - path: ./config.yaml
            filter:
              include_regex: "^(DATABASE_|REDIS_)"
              depth: 3
          - path: ./config.json
          - uri: redis://localhost:6379/0
            writable: true
    ```

## 10) Error handling and logging

- Never print secret values in logs.
- Provide structured error types: `SourceError`, `ValidationError`, `NetworkError`, `PersistenceError`.
- Verbose mode prints actions and summaries without value contents; provenance can be printed.

## 11) Performance and concurrency

- Loading from files is fast, done on demand.
- Redis and GitHub calls should be batched where feasible; provide timeouts and retries with exponential backoff.
- Thread-safety: `Environment` and `Config` are not thread-safe; document this. CLI is single-threaded.

## 12) Security

- Do not log secrets or values by default.
- Support `GITHUB_TOKEN` via environment variables.
- Validate and redact credentials in URIs when displayed.

## 13) Extensibility

- Allow custom sources by:
  - Subclassing `Source` or
  - Using `FunctionalSource` by providing callables for required methods (matching the README’s spirit).
- `Environment.add_source_type(source: Source)` registers a source type or factory.
- Maintain a registry keyed by extension or scheme (e.g., `.env`, `.yaml`, `redis://`).

## 14) Packaging, tooling, and versions

- Python 3.10+
- Package metadata in `pyproject.toml` (PEP 621)
- Dev tooling:
  - Use `uv` for dependency management and locking.
  - Lint with `ruff`, format with `black`, types with `mypy`.
  - Tests with `pytest`.
- Dependencies (latest stable):
  - `PyYAML`
  - `redis`
  - `httpx` (for GitHub)
  - `click` (or `typer`) for CLI
- Entry point: console script `confetti=confetti.cli.__main__:app`

## 15) Testing

- Unit tests:
  - Each source type: load/get/set/unset/save/reload/filters/depth.
  - Merge precedence and provenance correctness.
  - Set/unset behavior with provenance and fallback to lower-priority sources.
  - CLI commands: end-to-end using temp dirs/containers (Redis with testcontainer or localhost if available).
- Integration tests:
  - Combined sources scenario matching the README example.
  - GitHub optional tests guarded by env vars; skip by default.
- Golden tests for export/import across formats.

## 16) Documentation

- Update `README.md` with:
  - Accurate API signatures.
  - CLI usage.
  - Examples for filters and depth on YAML/JSON.
  - Custom source authoring guide with both subclass and functional adapter examples.

## 17) Acceptance criteria

- Python API:
  - The examples in lines 15–37 and 47–103 of the README execute successfully with the implemented library.
- CLI:
  - `confetti init`, `sources list/add/remove`, `get/set/unset/save/reload`, `export`, `import` work as specified.
- Provenance:
  - `config.get(key)` can also return provenance through an optional `return_provenance=True` or a separate `config.provenance(key)` method.
- Filters and depth:
  - Regex include works for flat keys.
  - Hierarchical include and depth limit work for YAML/JSON.
- Redis source:
  - Can set/unset/save values and reflect in effective config.
- GitHub (optional):
  - If configured, can read variables; secrets are not read as plaintext; no crashes when excluded by default.

## 18) Implementation plan (high-level)

- Phase 1: Core types, merging, provenance, `.env` source using existing parser.
- Phase 2: INI/YAML/JSON sources with flattening/filtering/depth.
- Phase 3: Redis source (read/write).
- Phase 4: CLI with core commands.
- Phase 5: GitHub envs source (read, optionally write for variables).
- Phase 6: Docs and tests.

- Deliverables:
  - Updated package with modules as per §3.
  - `pyproject.toml` with proper metadata and entry points.
  - `uv.lock` committed for reproducible dev installs.
  - Test suite green in CI (GitHub Actions recommended).

- Key changes to implement:
  - New core modules for `Environment`, `Config`, `Source` and filter/merge logic.
  - Built-in sources for `.env`, `.ini`, `.yaml`, `.json`, `redis://`, and optional GitHub environments.
  - CLI with source management and config operations.
  - Provenance tracking and save semantics.
  - Packaging with `uv`, tests, and docs.

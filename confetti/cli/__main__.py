from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ..core.environment import Environment

app = typer.Typer(help="Confetti CLI")


def _env(name: str) -> Environment:
    return Environment(name)


@app.command()
def sources_list(env: str = typer.Option("development", "--env")):
    e = _env(env)
    cfg = e.get_config()
    typer.echo(json.dumps([
        {
            "id": rs.source.id,
            "name": rs.source.name,
            "writable": rs.is_writable,
            "depth": rs.depth,
        }
        for rs in cfg.registered_sources
    ], indent=2))


@app.command()
def get(key: str, env: str = typer.Option("development", "--env")):
    e = _env(env)
    cfg = e.get_config()
    value = cfg.get(key)
    prov = cfg.provenance(key)
    typer.echo(json.dumps({"key": key, "value": value, "source": prov.source_id if prov else None}, indent=2))


@app.command()
def set(
    key: str,
    value: str,
    env: str = typer.Option("development", "--env"),
    source: Optional[str] = typer.Option(None, "--source"),
    save: bool = typer.Option(False, "--save"),
):
    e = _env(env)
    cfg = e.get_config()
    cfg.set(key, value, source=source)
    if save:
        cfg.save()
    typer.echo("OK")


@app.command()
def unset(
    key: str,
    env: str = typer.Option("development", "--env"),
    save: bool = typer.Option(False, "--save"),
):
    e = _env(env)
    cfg = e.get_config()
    cfg.unset(key)
    if save:
        cfg.save()
    typer.echo("OK")


@app.command()
def save(env: str = typer.Option("development", "--env")):
    e = _env(env)
    cfg = e.get_config()
    cfg.save()
    typer.echo("Saved")


@app.command("sync-github")
def sync_github(
    github_uri: str = typer.Argument(..., help="github://owner/repo#environment"),
    env: str = typer.Option("development", "--env"),
    token: Optional[str] = typer.Option(None, "--token", help="GitHub token or use GITHUB_TOKEN"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    # Build merged config from current sources, then push into given GitHub environment
    from ..sources.github_env import GitHubEnvSource

    e = _env(env)
    cfg = e.get_config()
    merged = cfg.values()

    gh = GitHubEnvSource(github_uri, token=token)
    gh.load()

    if dry_run:
        # Show diff-like summary
        to_set = {k: v for k, v in merged.items() if gh.get(k) != v}
        to_del = [k for k in gh.keys() if k not in merged]
        typer.echo(json.dumps({"set": to_set, "delete": to_del}, indent=2))
        return

    for k, v in merged.items():
        gh.set(k, str(v))
    # Optionally delete keys not present in merged? Keep conservative: do not delete unless explicit flag in future.
    gh.save()
    typer.echo("Synced to GitHub environment")


if __name__ == "__main__":
    app()

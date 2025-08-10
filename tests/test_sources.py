from __future__ import annotations

import json
from pathlib import Path

import pytest

from confetti import Environment


def test_env_file_load_set_unset(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\n")
    e = Environment("dev")
    e.register_source(env_file)
    cfg = e.get_config()
    assert cfg.get("A") == "1"
    cfg.set("A", "2")
    cfg.save()
    assert cfg.get("A") == "2"
    assert env_file.read_text().strip() == "A=2"
    cfg.unset("A")
    cfg.save()
    assert cfg.get("A") is None


def test_yaml_flatten_and_set(tmp_path: Path):
    yml = tmp_path / "c.yaml"
    yml.write_text("database:\n  url: postgres://localhost\n  pool: 5\n")
    e = Environment("dev")
    e.register_source(yml)
    cfg = e.get_config()
    assert cfg.get("database.url") == "postgres://localhost"
    cfg.set("database.max", 10)
    cfg.save()
    content = yml.read_text()
    assert "max: 10" in content


def test_json_flatten_and_unset(tmp_path: Path):
    js = tmp_path / "c.json"
    js.write_text(json.dumps({"service": {"host": "127.0.0.1", "port": 8000}}))
    e = Environment("dev")
    e.register_source(js)
    cfg = e.get_config()
    assert cfg.get("service.port") == 8000
    cfg.unset("service.port")
    cfg.save()
    data = json.loads(js.read_text())
    assert "port" not in data["service"]


def test_ini_flatten_and_set(tmp_path: Path):
    ini = tmp_path / "c.ini"
    ini.write_text("[s]\nkey=value\n")
    e = Environment("dev")
    e.register_source(ini)
    cfg = e.get_config()
    assert cfg.get("s.key") == "value"
    cfg.set("s.other", "x")
    cfg.save()
    text = ini.read_text()
    assert "other = x" in text


def test_merge_precedence(tmp_path: Path):
    a = tmp_path / "a.env"
    a.write_text("X=1\n")
    b = tmp_path / "b.yaml"
    b.write_text("X: 2\n")
    e = Environment("dev")
    e.register_sources(a, b)
    cfg = e.get_config()
    assert cfg.get("X") == 2 or cfg.get("X") == "2"
    prov = cfg.provenance("X")
    assert prov is not None
    assert prov.source_id.endswith("b.yaml")

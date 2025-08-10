from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from confetti import Environment


def test_env_file_load_set_unset(tmp_path: Path):
    # Copy fixture file to tmp_path
    fixture_file = Path(__file__).parent / "fixtures" / "test.env"
    env_file = tmp_path / ".env"
    shutil.copy2(fixture_file, env_file)

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
    # Copy fixture file to tmp_path
    fixture_file = Path(__file__).parent / "fixtures" / "database.yaml"
    yml = tmp_path / "c.yaml"
    shutil.copy2(fixture_file, yml)

    e = Environment("dev")
    e.register_source(yml)
    cfg = e.get_config()
    assert cfg.get("database.url") == "postgres://localhost"
    cfg.set("database.max", 10)
    cfg.save()
    content = yml.read_text()
    assert "max: 10" in content


def test_json_flatten_and_unset(tmp_path: Path):
    # Copy fixture file to tmp_path
    fixture_file = Path(__file__).parent / "fixtures" / "service.json"
    js = tmp_path / "c.json"
    shutil.copy2(fixture_file, js)

    e = Environment("dev")
    e.register_source(js)
    cfg = e.get_config()
    assert cfg.get("service.port") == 8000
    cfg.unset("service.port")
    cfg.save()
    data = json.loads(js.read_text())
    assert "port" not in data["service"]


def test_ini_flatten_and_set(tmp_path: Path):
    # Copy fixture file to tmp_path
    fixture_file = Path(__file__).parent / "fixtures" / "config.ini"
    ini = tmp_path / "c.ini"
    shutil.copy2(fixture_file, ini)

    e = Environment("dev")
    e.register_source(ini)
    cfg = e.get_config()
    assert cfg.get("s.key") == "value"
    cfg.set("s.other", "x")
    cfg.save()
    text = ini.read_text()
    assert "other = x" in text


def test_merge_precedence(tmp_path: Path):
    # Copy fixture files to tmp_path
    fixture_a = Path(__file__).parent / "fixtures" / "a.env"
    fixture_b = Path(__file__).parent / "fixtures" / "b.yaml"
    a = tmp_path / "a.env"
    b = tmp_path / "b.yaml"
    shutil.copy2(fixture_a, a)
    shutil.copy2(fixture_b, b)

    e = Environment("dev")
    e.register_sources(a, b)
    cfg = e.get_config()
    assert cfg.get("X") == 2 or cfg.get("X") == "2"
    prov = cfg.provenance("X")
    assert prov is not None
    assert prov.source_id.endswith("b.yaml")

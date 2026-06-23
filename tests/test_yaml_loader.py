"""Tests for YAML component loader."""

import tempfile
from pathlib import Path

import pytest

from okw_env.yaml_loader import load_component


def test_load_component():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("PostgresDB:\n  image: postgres\n  version: '17'\n  port: 5432\n")
        f.flush()
        data = load_component(f.name)

    assert "PostgresDB" in data
    assert data["PostgresDB"]["image"] == "postgres"
    assert data["PostgresDB"]["version"] == "17"
    assert data["PostgresDB"]["port"] == 5432


def test_load_component_with_env():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("Redis:\n  image: redis\n  env:\n    REDIS_PASSWORD: secret\n")
        f.flush()
        data = load_component(f.name)

    assert data["Redis"]["env"]["REDIS_PASSWORD"] == "secret"


def test_load_component_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_component("/nonexistent/path.yaml")


def test_load_component_path_object():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("Test:\n  image: test\n")
        f.flush()
        data = load_component(Path(f.name))

    assert "Test" in data

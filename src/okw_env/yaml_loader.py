"""YAML loader for environment component definitions."""

from pathlib import Path

import yaml


def load_component(yaml_path: str | Path) -> dict:
    """Load a single environment component definition from YAML."""
    path = Path(yaml_path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

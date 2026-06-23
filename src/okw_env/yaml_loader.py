"""YAML loader for environment component definitions with inheritance."""

from pathlib import Path

import yaml


def load_component(yaml_path: str | Path) -> dict:
    """Load a single environment component definition from YAML.

    Supports ``extends`` for inheritance: the base component is loaded
    first, then the child keys are merged on top (child wins).
    Paths in ``extends`` are resolved relative to the YAML file.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Component YAML not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return data

    for component_name, component_def in data.items():
        if isinstance(component_def, dict) and "extends" in component_def:
            data[component_name] = _resolve_extends(component_def, path.parent)

    return data


def _resolve_extends(component: dict, base_dir: Path) -> dict:
    """Resolve extends by loading the base and merging child on top."""
    extends_ref = component.pop("extends")

    base_name, base_def = _load_base(extends_ref, base_dir)

    merged = {**base_def, **component}

    for key in base_def:
        if key in component and isinstance(base_def[key], dict) and isinstance(component[key], dict):
            merged[key] = {**base_def[key], **component[key]}

    if "extends" in merged:
        merged = _resolve_extends(merged, base_dir)

    return merged


def _load_base(extends_ref: str, base_dir: Path) -> tuple[str, dict]:
    """Load the base component. extends_ref can be 'ComponentName' or 'file.yaml:ComponentName'."""
    if ":" in extends_ref:
        file_part, component_name = extends_ref.rsplit(":", 1)
        base_path = base_dir / file_part
    else:
        component_name = extends_ref
        base_path = base_dir / f"{component_name}.yaml"

    if not base_path.exists():
        raise FileNotFoundError(
            f"Base component file not found: {base_path} (extends: '{extends_ref}')"
        )

    with base_path.open("r", encoding="utf-8") as f:
        base_data = yaml.safe_load(f)

    if component_name not in base_data:
        raise KeyError(
            f"Base component '{component_name}' not found in {base_path}. "
            f"Available: {list(base_data.keys())}"
        )

    base_def = base_data[component_name]

    if isinstance(base_def, dict) and "extends" in base_def:
        base_def = _resolve_extends(base_def, base_path.parent)

    return component_name, base_def

"""Auto-discovery of installed OKW environment providers via entry points."""

from __future__ import annotations

import sys

from okw_env.provider_base import OkwEnvProviderBase

_ENTRY_POINT_GROUP = "okw_env.providers"

_cache: dict[str, type[OkwEnvProviderBase]] = {}


def discover_providers() -> dict[str, type[OkwEnvProviderBase]]:
    """Scan installed packages for OKW environment providers."""
    if _cache:
        return _cache

    if sys.version_info >= (3, 12):
        from importlib.metadata import entry_points
        eps = entry_points(group=_ENTRY_POINT_GROUP)
    else:
        from importlib.metadata import entry_points
        all_eps = entry_points()
        eps = all_eps.get(_ENTRY_POINT_GROUP, [])

    for ep in eps:
        _cache[ep.name] = ep.load()

    return _cache


def get_provider(name: str) -> OkwEnvProviderBase:
    """Get a provider instance by name (e.g. 'docker', 'proxmox')."""
    providers = discover_providers()
    if name not in providers:
        available = list(providers.keys())
        raise KeyError(
            f"Provider '{name}' not found. "
            f"Installed providers: {available}. "
            f"Install a provider package (e.g. pip install robotframework-okw-env-docker)."
        )
    provider_class = providers[name]
    return provider_class()

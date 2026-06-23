"""Manages registered environment components and delegates to providers."""

import time

from okw_env.provider_base import OkwEnvProviderBase
from okw_env.provider_registry import get_provider


class EnvironmentManager:
    """Tracks all registered components and orchestrates provider calls.

    Each component can use a different provider (determined by the
    ``provider`` key in the component YAML). Providers are resolved
    automatically via the entry point registry.
    """

    def __init__(self):
        self._components: dict[str, dict] = {}
        self._component_ids: dict[str, str] = {}
        self._providers: dict[str, OkwEnvProviderBase] = {}
        self._default_provider: OkwEnvProviderBase | None = None

    def set_provider(self, provider: OkwEnvProviderBase) -> None:
        """Set a default provider (used when YAML has no 'provider' key)."""
        self._default_provider = provider

    def register(self, name: str, component: dict, **overrides) -> None:
        """Register a component for later provisioning."""
        merged = {**component, **overrides}
        self._components[name] = merged

    def build_and_run(self) -> None:
        """Create and start all registered components."""
        for name, component in self._components.items():
            provider = self._resolve_provider(name, component)
            component_id = provider.create(component)
            self._component_ids[name] = component_id
            self._providers[name] = provider
            provider.start(component_id)

    def wait_for_ready(self, name: str, timeout: float = 30.0, interval: float = 1.0) -> None:
        """Poll until the component is ready or timeout is reached."""
        provider = self._require_provider(name)
        component_id = self._require_component_id(name)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if provider.is_ready(component_id):
                return
            time.sleep(interval)
        raise TimeoutError(f"Component '{name}' not ready after {timeout}s.")

    def get_logs(self, name: str) -> str:
        """Retrieve logs from a component."""
        provider = self._require_provider(name)
        component_id = self._require_component_id(name)
        return provider.get_logs(component_id)

    def snapshot(self, name: str) -> str:
        """Snapshot a component's current state."""
        provider = self._require_provider(name)
        component_id = self._require_component_id(name)
        return provider.snapshot(component_id)

    def snapshot_all(self) -> dict[str, str]:
        """Snapshot all running components. Returns {name: snapshot_id}."""
        results = {}
        for name, component_id in self._component_ids.items():
            provider = self._require_provider(name)
            results[name] = provider.snapshot(component_id)
        return results

    def stop_all(self) -> None:
        """Stop and destroy all components."""
        for name, component_id in list(self._component_ids.items()):
            provider = self._providers[name]
            provider.stop(component_id)
            provider.destroy(component_id)
        self._component_ids.clear()
        self._components.clear()
        self._providers.clear()

    def get_component_config(self, name: str) -> dict:
        """Return the registered component definition."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' not registered. Registered: {list(self._components.keys())}")
        return self._components[name]

    def _resolve_provider(self, name: str, component: dict) -> OkwEnvProviderBase:
        """Resolve provider from component YAML or fall back to default."""
        provider_name = component.get("provider")
        if provider_name:
            return get_provider(provider_name, component=component)
        if self._default_provider:
            return self._default_provider
        raise RuntimeError(
            f"Component '{name}' has no 'provider' key and no default provider is set. "
            f"Add 'provider: docker' to the YAML or call set_provider()."
        )

    def _require_provider(self, name: str) -> OkwEnvProviderBase:
        if name not in self._providers:
            raise KeyError(f"No provider for '{name}'. Was build_and_run() called?")
        return self._providers[name]

    def _require_component_id(self, name: str) -> str:
        if name not in self._component_ids:
            raise KeyError(f"Component '{name}' not found. Registered: {list(self._component_ids.keys())}")
        return self._component_ids[name]

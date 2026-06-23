"""Manages registered environment components and delegates to the provider."""

import time

from okw_env.provider_base import OkwEnvProviderBase


class EnvironmentManager:
    """Tracks all registered components and orchestrates provider calls."""

    def __init__(self):
        self._components: dict[str, dict] = {}
        self._component_ids: dict[str, str] = {}
        self._provider: OkwEnvProviderBase | None = None

    def set_provider(self, provider: OkwEnvProviderBase) -> None:
        self._provider = provider

    def _require_provider(self) -> OkwEnvProviderBase:
        if self._provider is None:
            raise RuntimeError("No environment provider set. Call set_provider() first.")
        return self._provider

    def register(self, name: str, component: dict, **overrides) -> None:
        """Register a component for later provisioning."""
        merged = {**component, **overrides}
        self._components[name] = merged

    def build_and_run(self) -> None:
        """Create and start all registered components."""
        provider = self._require_provider()
        for name, component in self._components.items():
            component_id = provider.create(component)
            self._component_ids[name] = component_id
            provider.start(component_id)

    def wait_for_ready(self, name: str, timeout: float = 30.0, interval: float = 1.0) -> None:
        """Poll until the component is ready or timeout is reached."""
        provider = self._require_provider()
        component_id = self._require_component_id(name)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if provider.is_ready(component_id):
                return
            time.sleep(interval)
        raise TimeoutError(f"Component '{name}' not ready after {timeout}s.")

    def get_logs(self, name: str) -> str:
        """Retrieve logs from a component."""
        provider = self._require_provider()
        component_id = self._require_component_id(name)
        return provider.get_logs(component_id)

    def snapshot(self, name: str) -> str:
        """Snapshot a component's current state."""
        provider = self._require_provider()
        component_id = self._require_component_id(name)
        return provider.snapshot(component_id)

    def snapshot_all(self) -> dict[str, str]:
        """Snapshot all running components. Returns {name: snapshot_id}."""
        provider = self._require_provider()
        results = {}
        for name, component_id in self._component_ids.items():
            results[name] = provider.snapshot(component_id)
        return results

    def stop_all(self) -> None:
        """Stop and destroy all components."""
        provider = self._require_provider()
        for name, component_id in list(self._component_ids.items()):
            provider.stop(component_id)
            provider.destroy(component_id)
        self._component_ids.clear()
        self._components.clear()

    def _require_component_id(self, name: str) -> str:
        if name not in self._component_ids:
            raise KeyError(f"Component '{name}' not found. Registered: {list(self._component_ids.keys())}")
        return self._component_ids[name]

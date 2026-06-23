"""Base class for all OKW environment providers."""

from abc import ABC, abstractmethod


class OkwEnvProviderBase(ABC):
    """Every environment provider (Docker, Proxmox, K8s, ...) implements this contract."""

    @abstractmethod
    def create(self, component: dict) -> str:
        """Create the environment component. Returns a provider-specific ID."""

    @abstractmethod
    def start(self, component_id: str) -> None:
        """Start the component."""

    @abstractmethod
    def is_ready(self, component_id: str) -> bool:
        """Check if the component is ready (health check passed)."""

    @abstractmethod
    def snapshot(self, component_id: str) -> str:
        """Freeze the current state for later analysis. Returns a snapshot ID."""

    @abstractmethod
    def stop(self, component_id: str) -> None:
        """Stop the component."""

    @abstractmethod
    def destroy(self, component_id: str) -> None:
        """Remove the component and all associated resources."""

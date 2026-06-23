"""Tests for OkwEnvProviderBase contract compliance."""

import pytest

from okw_env.provider_base import OkwEnvProviderBase


class IncompleteProvider(OkwEnvProviderBase):
    """A provider that does not implement all methods — must fail."""
    pass


class MockProvider(OkwEnvProviderBase):
    """A minimal provider implementing all contract methods."""

    def __init__(self):
        self.calls = []

    def create(self, component: dict) -> str:
        self.calls.append(("create", component))
        return "mock-id-1"

    def start(self, component_id: str) -> None:
        self.calls.append(("start", component_id))

    def is_ready(self, component_id: str) -> bool:
        self.calls.append(("is_ready", component_id))
        return True

    def get_logs(self, component_id: str) -> str:
        self.calls.append(("get_logs", component_id))
        return "mock log output"

    def snapshot(self, component_id: str) -> str:
        self.calls.append(("snapshot", component_id))
        return "mock-snapshot-1"

    def stop(self, component_id: str) -> None:
        self.calls.append(("stop", component_id))

    def destroy(self, component_id: str) -> None:
        self.calls.append(("destroy", component_id))


def test_incomplete_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        IncompleteProvider()


def test_mock_provider_implements_full_contract():
    provider = MockProvider()
    assert isinstance(provider, OkwEnvProviderBase)


def test_create_returns_id():
    provider = MockProvider()
    result = provider.create({"image": "postgres", "version": "17"})
    assert result == "mock-id-1"


def test_all_methods_callable():
    provider = MockProvider()
    cid = provider.create({"image": "test"})
    provider.start(cid)
    assert provider.is_ready(cid) is True
    assert provider.get_logs(cid) == "mock log output"
    assert provider.snapshot(cid) == "mock-snapshot-1"
    provider.stop(cid)
    provider.destroy(cid)

    methods_called = [c[0] for c in provider.calls]
    assert methods_called == ["create", "start", "is_ready", "get_logs", "snapshot", "stop", "destroy"]

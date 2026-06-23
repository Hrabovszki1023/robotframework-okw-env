"""Tests for EnvironmentManager."""

import pytest

from okw_env.environment_manager import EnvironmentManager
from okw_env.provider_base import OkwEnvProviderBase


class MockProvider(OkwEnvProviderBase):

    def __init__(self, ready_after=0):
        self.calls = []
        self._ready_count = 0
        self._ready_after = ready_after

    def create(self, component: dict) -> str:
        cid = f"mock-{len(self.calls)}"
        self.calls.append(("create", component))
        return cid

    def start(self, component_id: str) -> None:
        self.calls.append(("start", component_id))

    def is_ready(self, component_id: str) -> bool:
        self._ready_count += 1
        ready = self._ready_count > self._ready_after
        self.calls.append(("is_ready", component_id, ready))
        return ready

    def get_logs(self, component_id: str) -> str:
        self.calls.append(("get_logs", component_id))
        return f"logs for {component_id}"

    def snapshot(self, component_id: str) -> str:
        self.calls.append(("snapshot", component_id))
        return f"snap-{component_id}"

    def stop(self, component_id: str) -> None:
        self.calls.append(("stop", component_id))

    def destroy(self, component_id: str) -> None:
        self.calls.append(("destroy", component_id))


def test_register_component():
    mgr = EnvironmentManager()
    mgr.register("DB", {"image": "postgres", "provider": "docker"})
    config = mgr.get_component_config("DB")
    assert config["image"] == "postgres"


def test_register_with_overrides():
    mgr = EnvironmentManager()
    mgr.register("DB", {"image": "postgres", "version": "16"}, version="17")
    config = mgr.get_component_config("DB")
    assert config["version"] == "17"


def test_build_and_run_calls_create_and_start():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()

    methods = [c[0] for c in provider.calls]
    assert methods == ["create", "start"]


def test_build_and_run_multiple_components():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.register("Cache", {"image": "redis"})
    mgr.build_and_run()

    methods = [c[0] for c in provider.calls]
    assert methods == ["create", "start", "create", "start"]


def test_wait_for_ready_immediate():
    provider = MockProvider(ready_after=0)
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()
    mgr.wait_for_ready("DB", timeout=5.0)


def test_wait_for_ready_with_polling():
    provider = MockProvider(ready_after=2)
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()
    mgr.wait_for_ready("DB", timeout=5.0, interval=0.01)

    ready_calls = [c for c in provider.calls if c[0] == "is_ready"]
    assert len(ready_calls) == 3
    assert ready_calls[-1][2] is True


def test_wait_for_ready_timeout():
    class NeverReadyProvider(MockProvider):
        def is_ready(self, component_id: str) -> bool:
            return False

    provider = NeverReadyProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()

    with pytest.raises(TimeoutError, match="not ready after"):
        mgr.wait_for_ready("DB", timeout=0.1, interval=0.01)


def test_get_logs():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()

    logs = mgr.get_logs("DB")
    assert "mock-0" in logs


def test_snapshot_single():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()

    snap_id = mgr.snapshot("DB")
    assert snap_id.startswith("snap-")


def test_snapshot_all():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.register("Cache", {"image": "redis"})
    mgr.build_and_run()

    snaps = mgr.snapshot_all()
    assert "DB" in snaps
    assert "Cache" in snaps


def test_stop_all():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.register("Cache", {"image": "redis"})
    mgr.build_and_run()
    mgr.stop_all()

    methods = [c[0] for c in provider.calls]
    assert "stop" in methods
    assert "destroy" in methods


def test_stop_all_clears_state():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()
    mgr.stop_all()

    with pytest.raises(KeyError):
        mgr.get_component_config("DB")


def test_no_provider_raises():
    mgr = EnvironmentManager()
    mgr.register("DB", {"image": "postgres"})
    with pytest.raises(RuntimeError, match="no default provider"):
        mgr.build_and_run()


def test_unknown_component_raises():
    provider = MockProvider()
    mgr = EnvironmentManager()
    mgr.set_provider(provider)
    mgr.register("DB", {"image": "postgres"})
    mgr.build_and_run()

    with pytest.raises(KeyError, match="No provider for"):
        mgr.wait_for_ready("NonExistent")

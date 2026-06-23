"""OKW Environment Library – Robot Framework keywords for environment provisioning."""

from __future__ import annotations

from pathlib import Path

from robot.api import logger
from robot.api.deco import keyword, library

from .environment_manager import EnvironmentManager
from .yaml_loader import load_component


@library(scope="GLOBAL")
class OkwEnvLibrary:
    """Driver-agnostic Robot Framework library for ephemeral test environments.

    Provides keywords to build, run, and tear down isolated environments
    per test case. Provider plugins (Docker, Proxmox, ...) implement the
    actual infrastructure.

    = Keywords =

    | ``ENV_Start``          | Register a component                    |
    | ``ENV_BuildAndRun``    | Create and start all components         |
    | ``ENV_WaitForReady``   | Wait until a component passes its health check |
    | ``ENV_Stop``           | Stop and destroy all components         |
    | ``ENV_CreateImage``    | Snapshot current state for reuse        |
    | ``ENV_StartFromImage`` | Start from snapshot or run fallback     |
    | ``ENV_SnapshotOnFail`` | Freeze state on test failure            |
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, provider=None, components_dir: str | None = None):
        self._manager = EnvironmentManager()
        self._components_dir = Path(components_dir) if components_dir else None
        if provider is not None:
            self._manager.set_provider(provider)

    def set_provider(self, provider):
        self._manager.set_provider(provider)

    @keyword("ENV_Start")
    def env_start(self, name: str, **overrides):
        """Register an environment component for provisioning.

        Loads the component definition from YAML and applies any overrides.

        Example:
        | ENV_Start | PostgresDB | version=17 |
        """
        component = self._load_component(name)
        self._manager.register(name, component, **overrides)
        logger.info(f"ENV_Start: Registered '{name}'")

    @keyword("ENV_BuildAndRun")
    def env_build_and_run(self):
        """Create and start all registered environment components.

        Example:
        | ENV_Start      | WebShop    |
        | ENV_Start      | PostgresDB |
        | ENV_BuildAndRun |            |
        """
        self._manager.build_and_run()
        logger.info("ENV_BuildAndRun: All components started.")

    @keyword("ENV_WaitForReady")
    def env_wait_for_ready(self, name: str, timeout: str | None = None):
        """Wait until a component passes its health check.

        Timeout is read from the component YAML (``timeout`` key).
        An explicit parameter overrides the YAML value.

        Example:
        | ENV_WaitForReady | WebShop |             |
        | ENV_WaitForReady | WebShop | timeout=60s |
        """
        if timeout is None:
            timeout = self._manager.get_component_config(name).get("timeout", "30s")
        timeout_seconds = self._parse_timeout(timeout)
        self._manager.wait_for_ready(name, timeout=timeout_seconds)
        logger.info(f"ENV_WaitForReady: '{name}' is ready.")

    @keyword("ENV_Stop")
    def env_stop(self):
        """Stop and destroy all environment components.

        Example:
        | ENV_Stop |
        """
        self._log_all_components()
        self._manager.stop_all()
        logger.info("ENV_Stop: All components stopped and destroyed.")

    @keyword("ENV_CreateImage")
    def env_create_image(self, name: str):
        """Snapshot the current state of all components for reuse.

        Example:
        | ENV_CreateImage | ShopWithTestData |
        """
        snapshots = self._manager.snapshot_all()
        logger.info(f"ENV_CreateImage: Created image '{name}' with snapshots: {snapshots}")

    @keyword("ENV_StartFromImage")
    def env_start_from_image(self, image_name: str, fallback_keyword: str):
        """Start from a cached image if it exists, otherwise run the fallback keyword.

        Example:
        | ENV_StartFromImage | ShopWithTestData | Setup Shop Environment |
        """
        # TODO: Implement image cache lookup
        # For now, always run the fallback
        from robot.libraries.BuiltIn import BuiltIn
        logger.info(f"ENV_StartFromImage: Image '{image_name}' not found, running fallback '{fallback_keyword}'.")
        BuiltIn().run_keyword(fallback_keyword)

    @keyword("ENV_SnapshotOnFail")
    def env_snapshot_on_fail(self):
        """Snapshot all components if the current test has failed.

        Use in [Teardown] to preserve the failure state for analysis.

        Example:
        | [Teardown] | Run Keywords | ENV_SnapshotOnFail | ENV_Stop |
        """
        from robot.libraries.BuiltIn import BuiltIn
        status = BuiltIn().get_variable_value("${TEST STATUS}", "PASS")
        if status == "FAIL":
            snapshots = self._manager.snapshot_all()
            logger.warn(f"ENV_SnapshotOnFail: Test failed. Snapshots: {snapshots}")
        else:
            logger.info("ENV_SnapshotOnFail: Test passed, no snapshot needed.")

    def _load_component(self, name: str) -> dict:
        """Load component definition from YAML."""
        if self._components_dir is None:
            raise RuntimeError(f"No components_dir configured. Cannot load '{name}'.")
        yaml_path = self._components_dir / f"{name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Component YAML not found: {yaml_path}")
        data = load_component(yaml_path)
        if name not in data:
            raise KeyError(f"Component '{name}' not found in {yaml_path}. Keys: {list(data.keys())}")
        return data[name]

    def _log_all_components(self):
        """Log output of all components into the Robot report."""
        for name in list(self._manager._component_ids.keys()):
            try:
                logs = self._manager.get_logs(name)
                if logs:
                    logger.info(f"--- Logs: {name} ---\n{logs}", html=False)
            except Exception as e:
                logger.warn(f"Could not retrieve logs for '{name}': {e}")

    @staticmethod
    def _parse_timeout(timeout: str) -> float:
        """Parse timeout string like '30s', '2m', '120' to seconds."""
        timeout = timeout.strip().lower()
        if timeout.endswith("s"):
            return float(timeout[:-1])
        if timeout.endswith("m"):
            return float(timeout[:-1]) * 60
        return float(timeout)

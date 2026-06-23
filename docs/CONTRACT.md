# OKW Environment Provider Contract

> This contract is authoritative. All provider implementations
> (Docker, Proxmox, ...) MUST comply.

## Purpose

The contract defines the interface between the driver-agnostic
`okw-env` core and the technology-specific provider plugins.
Tests written against `okw-env` keywords work unchanged regardless
of the underlying provider.

## Provider Base Class

Every provider inherits from `okw_env.provider_base.OkwEnvProviderBase`
and implements all abstract methods.

### Methods

| Method | Signature | Purpose |
|---|---|---|
| `create` | `(component: dict) -> str` | Create the component from its YAML definition. Returns a provider-specific ID. |
| `start` | `(component_id: str) -> None` | Start the component. |
| `is_ready` | `(component_id: str) -> bool` | Health check. Returns `True` when the component is operational. |
| `get_logs` | `(component_id: str) -> str` | Retrieve stdout/stderr logs from the component. |
| `snapshot` | `(component_id: str) -> str` | Freeze the current state. Returns a snapshot ID for later restoration. |
| `get_runtime_info` | `(component_id: str) -> dict` | Return runtime values that override YAML config (e.g. assigned port). Default: `{}`. |
| `stop` | `(component_id: str) -> None` | Stop the component (but keep resources). |
| `destroy` | `(component_id: str) -> None` | Remove the component and all associated resources (networks, volumes, disks). |

### Rules

1. **All abstract methods are mandatory.** `get_runtime_info` is optional
   (default returns `{}`). Override it when the provider assigns values
   at runtime (e.g. dynamic port mapping).
2. **`create` + `start` are separate.** `create` prepares resources,
   `start` activates them. This allows batch creation before starting.
3. **`stop` + `destroy` are separate.** `stop` halts execution,
   `destroy` removes all resources. This allows snapshot between stop and destroy.
4. **`is_ready` is non-blocking.** It returns the current state, not waits.
   Polling is handled by `EnvironmentManager.wait_for_ready()`.
5. **`destroy` is idempotent.** Calling it twice must not fail.
6. **`get_logs` works on running and stopped components.**
7. **`snapshot` works on running components.** The state is frozen
   without stopping (consistent with Docker commit and Proxmox snapshots).

## Provider Registration

Providers register via Python entry points:

```toml
[project.entry-points."okw_env.providers"]
docker = "okw_env_docker:DockerProvider"
```

The `provider` key in the component YAML triggers auto-discovery:

```yaml
PostgresDB:
  provider: docker    # → loads DockerProvider via entry point
  image: postgres
  version: "17"
```

## Component YAML Contract

Every component YAML MUST contain at least:

| Key | Required | Purpose |
|---|---|---|
| `provider` | YES | Provider name (entry point key) |
| `image` / `template` | YES | What to run (provider-specific) |
| `version` | NO | Version tag (default: `latest`) |
| `port` | NO | Primary exposed port |
| `env` | NO | Environment variables (dict) |
| `healthcheck` | NO | Command for health check |
| `timeout` | NO | Ready-timeout (default: `30s`) |
| `depends_on` | NO | List of component names this depends on |

Providers MAY define additional keys specific to their technology.

## Keyword Contract

The following Robot Framework keywords are defined by `okw-env`
and delegate to the provider contract:

| Keyword | Provider methods called |
|---|---|
| `ENV_Start` | (registers component, no provider call yet) |
| `ENV_BuildAndRun` | `create()` + `start()` for each component |
| `ENV_WaitForReady` | `is_ready()` in polling loop |
| `ENV_Stop` | `get_logs()` + `stop()` + `destroy()` for each component |
| `ENV_CreateImage` | `snapshot()` for each component |
| `ENV_StartFromImage` | (image cache lookup, fallback to full provisioning) |
| `ENV_SnapshotOnFail` | `snapshot()` for each component (only on FAIL) |

## Variable Publishing ($MEM{})

After `ENV_BuildAndRun`, all component YAML keys are flattened to
dot-notation and published as Robot Framework test variables. This
bridges environment provisioning with test keywords.

### Flattening Rules

| YAML structure | Variable name | Example value |
|---|---|---|
| Top-level key | `${Name.key}` | `${PostgresDB.image}` → `postgres` |
| Nested dict | `${Name.parent.key}` | `${PostgresDB.env.POSTGRES_DB}` → `shop` |
| Container ID (runtime) | `${Name.ID}` | `${PostgresDB.ID}` → `okw-3df2dcc8` |

All values are converted to strings via `str()`.

### Usage in Robot Framework

Direct access via Robot variable syntax:

```robot
Log    DB: ${PostgresDB.env.POSTGRES_DB} on port ${PostgresDB.port}
```

In OKW keywords via `$MEM{}` expansion:

```robot
SetValue    DB_Host    $MEM{PostgresDB.docker_host}
SetValue    DB_Name    $MEM{PostgresDB.env.POSTGRES_DB}
```

### Design Rationale

The connection data lives in the component YAML — not in environment
variables, not in CI config, not hardcoded in the test. The same test
runs against any Docker host by changing one YAML file. The variables
are the bridge between Phase 0 (environment) and Phase 3 (test execution).

## Error Handling

Providers MUST raise clear exceptions:

| Error | When |
|---|---|
| `RuntimeError` | Provider not configured, invalid state |
| `TimeoutError` | Component not ready within timeout |
| `KeyError` | Unknown component or provider |
| `FileNotFoundError` | Component YAML not found |

## Lifecycle

```
ENV_Start        → register component(s)
ENV_BuildAndRun  → create() → start() → get_runtime_info() → update config
ENV_WaitForReady → is_ready() polling
                   ... test runs ...
ENV_SnapshotOnFail → snapshot() (on FAIL only)
ENV_Stop         → get_logs() → stop() → destroy()
```

## Contract Tests

Provider implementations MUST pass the contract test suite
located in `tests/contract/`. These tests verify that all
methods exist, accept the correct parameters, and behave
according to this contract.

# OKW Environment Keywords — Concept

> Status: Draft
> Date: 2026-06-23

## Problem

Test environments are typically managed separately from test code:
Docker Compose files, CI scripts, infrastructure configs. This separation
creates NOISE — the tester must jump between test code and infrastructure
definitions to understand what a test actually needs.

## Solution

Environment provisioning becomes part of the test case itself, using
the same keyword-driven, YAML-based approach as OKW GUI testing.

## Extended Test Phase Model

The classic OKW test model gains Phase 0 and Phase 5:

```
Phase 0: Build environment         ← NEW
Phase 1: Preconditions (test data, states)
Phase 2: Action
Phase 3: Verification
Phase 4: Cleanup
Phase 5: Tear down environment     ← NEW
```

```robot
*** Test Cases ***
Order With Payment Gateway
    # Phase 0 — Environment
    StartEnvironment    WebShop
    StartEnvironment    PostgresDB
    StartEnvironment    PaymentGW
    BuildAndRun
    WaitForReady        WebShop

    # Phase 1-4 — Test
    StartApp            MyShop
    SetValue            Article      Laptop
    ClickOn             Order
    VerifyValue         Status       Paid
    StopApp

    # Phase 5 — Teardown
    StopEnvironment     ALL
```

## Simplified Phase Model — With Image Reuse

The classic test model requires a reset phase (clean up state from previous
tests) and a cleanup phase (restore state for next tests). Both are complex,
error-prone, and slow. With ephemeral images, both disappear:

**Classic model (without okw-env):**

```
0. Reset/Cleanup          ← complex, error-prone
1. Test data setup
2. Navigation + Action
3. Verification
4. Cleanup                ← complex, error-prone
```

**With okw-env:**

```
0. Instantiate image      ← seconds, always clean
1. Test data setup        ← optional if already in image
1. Navigation (incl. start SUT/App)
2. Test action
3. Acceptance criterion
4. Terminate image        ← trivial, kill & forget
```

**What disappears:**

- **No reset** — every image is factory-fresh
- **No cleanup** — image is simply discarded
- **No "state from previous test"** — impossible, because no shared state

These are the two most error-prone phases in the classic model, and they
are completely eliminated.

### Image Caching — Run Phase 0-1 Once, Reuse Forever

In practice, many test cases share the same preconditions (same environment,
same test data, same initial state). Instead of rebuilding this for every
test, run it once and snapshot:

```
Test 1 (first run):
  Phase 0: Build environment           ┐
  Phase 1: Load test data              │→ Snapshot → "ShopWithTestData"
  Phase 1: Navigate, start App         │
  ...                                  ┘
  ErstelleImage  ShopWithTestData

Test 2-100 (after that):
  → Start from snapshot "ShopWithTestData"   ← seconds instead of minutes
  Phase 2: Test action
  Phase 3: Acceptance criterion
  Phase 4: Terminate image
```

Two new keywords enable this:

```robot
*** Test Cases ***
Order Standard Customer
    StarteImageWennVorhanden    ShopWithTestData    Setup Shop Environment
    # Directly at the actual test — environment is ready
    SetValue    Article    Laptop
    ClickOn     Order
    VerifyValue Status     Paid

Return Standard Customer
    StarteImageWennVorhanden    ShopWithTestData    Setup Shop Environment
    # Same snapshot, different test
    ClickOn     Return
    VerifyValue Status     Returned
```

```robot
*** Keywords ***
Setup Shop Environment
    StartEnvironment    WebShop
    StartEnvironment    PostgresDB
    BuildAndRun
    WaitForReady        WebShop
    StartApp            MyShop
    SetValue            User        admin
    ClickOn             Login
    # ... test data, navigation, etc.
    ErstelleImage       ShopWithTestData
```

**Logic of `StarteImageWennVorhanden`:**

```
StarteImageWennVorhanden  "Name"  "Fallback-Keyword"
    │
    ├── Snapshot "Name" exists?
    │     YES → Start from snapshot (seconds)
    │     NO  → Execute fallback keyword (Phase 0-1)
    │           → Creates snapshot "Name" for next test
```

**Speedup in practice:**

| Scenario | Without image cache | With image cache |
|---|---|---|
| 1 test | 3 min (setup) + 30s (test) | 3 min + 30s (first run) |
| 100 tests, same precondition | 100 × 3.5 min = **350 min** | 3 min + 100 × 30s = **53 min** |

## YAML Component Definitions

Environment components are defined in YAML — same pattern as GUI locators:

```yaml
# environments/components/PostgresDB.yaml
PostgresDB:
  provider: docker
  image: postgres
  version: "16"
  port: 5432
  env:
    POSTGRES_DB: testdb
    POSTGRES_PASSWORD: test123
  healthcheck: "pg_isready -U postgres"

# environments/components/WebShop.yaml
WebShop:
  provider: docker
  image: mycompany/webshop
  version: "2.1"
  port: 8080
  depends_on: [PostgresDB]
  healthcheck: "curl -f http://localhost:8080/health"
```

The test references only abstract names. The framework generates the
provider-specific configuration (e.g., `docker-compose.yml`) automatically.

## Generated Docker Compose (Example)

From the YAML definitions above, the framework generates:

```yaml
# generated — never edit manually
services:
  PostgresDB:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: testdb
      POSTGRES_PASSWORD: test123
    healthcheck:
      test: pg_isready -U postgres
  WebShop:
    image: mycompany/webshop:2.1
    ports: ["8080:8080"]
    depends_on: [PostgresDB]
    healthcheck:
      test: curl -f http://localhost:8080/health
```

## Complete Isolation — Parallel Execution

Each test case brings its own environment. No shared state, no side effects:

```
Test A ──→ [WebShop:8080, DB:5432]     ← own containers
Test B ──→ [WebShop:8081, DB:5433]     ← own containers
Test C ──→ [WebShop:8082, DB:5434]     ← own containers
     └── run simultaneously, no interference
```

Port assignment and network isolation are NOISE — the framework handles
them automatically. The tester only describes **what** is needed.

## Ephemeral Environments — No Security Concerns

Environments exist only for the duration of the test case. After that:
gone. No data, no open ports, no forgotten credentials.

Consequences:

- **Real passwords in tests** — no problem, the container lives 30 seconds
- **Production-like data** — can be loaded without concern, nothing survives
- **No firewall rules** — the network is ephemeral and isolated
- **Compliance becomes trivial** — nothing to protect because nothing persists

All the security measures needed for persistent test environments
(secrets management, network policies, database encryption, access control)
are NOISE that the ephemeral model eliminates completely.

## Version Matrix Testing

Changing a component version = one parameter:

```robot
*** Test Cases ***
[Template]    Test Order
    WebShop=2.1    PostgresDB=16    PaymentGW=1.0
    WebShop=2.1    PostgresDB=17    PaymentGW=1.0    # DB upgrade
    WebShop=3.0    PostgresDB=17    PaymentGW=1.0    # Shop upgrade
    WebShop=3.0    PostgresDB=17    PaymentGW=2.0    # Everything new
```

Four combinations, four isolated environments, fully parallelizable.

## Architecture

```
┌──────────────────────────────┐
│  Robot Framework Test        │  StartEnvironment, StopEnvironment
├──────────────────────────────┤
│  okw-env (abstraction)       │  Keywords, YAML loader, provider contract
├──────────────┬───────────────┤
│  okw-env-    │  okw-env-     │  Provider plugins
│  docker      │  proxmox      │
├──────────────┼───────────────┤
│  Docker      │  Proxmox      │  Underlying APIs
│  Compose     │  VE API       │
└──────────────┴───────────────┘
```

Same test, different provider — only the YAML decides where the
environment runs:

```yaml
# Developer laptop
PostgresDB:
  provider: docker
  image: postgres:17

# CI on Proxmox
PostgresDB:
  provider: proxmox
  template: debian-postgres-17
  node: pve1
  cores: 2
  memory: 2048
```

## Failure Snapshot — Preserve the Crime Scene

When a test fails, the environment contains the **exact state** that caused
the failure: database contents, log files, configuration, network state.
Normally this is destroyed during teardown.

With `snapshot`, the framework freezes all containers before teardown:

```robot
*** Test Cases ***
Order With Payment Gateway
    [Teardown]    Run Keywords
    ...    SnapshotOnFail
    ...    StopEnvironment    ALL
```

Or automatically via a global hook — every failed test gets a snapshot
without extra code in the test case.

**What the tester gets:**
- Snapshot of every container at the moment of failure
- Can start the snapshot later and inspect: DB queries, log files,
  config state, network connections
- No more "I can't reproduce it" — the failure state is preserved

**Provider-specific implementation:**

| Provider | Snapshot mechanism |
|---|---|
| Docker | `docker commit` → saved image |
| Proxmox | VM/LXC snapshot via API |
| Kubernetes | Pod state export |

This is another Signal vs. NOISE win: today, failure analysis requires
reconstructing the environment from logs. With snapshots, the tester
goes directly to the frozen state — maximum Signal.

## Provider Contract

Every provider implements six methods:

| Method | Purpose |
|---|---|
| `create(component)` | Create the environment component |
| `start(component_id)` | Start it |
| `is_ready(component_id)` | Health check passed? |
| `snapshot(component_id)` | Freeze current state for later analysis |
| `stop(component_id)` | Stop it |
| `destroy(component_id)` | Remove it and all resources |

## Potential Provider Plugins

| Category | Plugin | Technology |
|---|---|---|
| Container | `okw-env-docker` | Docker Compose |
| Container | `okw-env-kubernetes` | K8s Namespaces/Pods |
| Container | `okw-env-podman` | Podman (rootless) |
| VM | `okw-env-proxmox` | Proxmox VE API |
| VM | `okw-env-vagrant` | Vagrant/VirtualBox |
| VM | `okw-env-libvirt` | KVM/QEMU |
| Cloud | `okw-env-aws` | EC2, ECS, Fargate |
| Cloud | `okw-env-azure` | Azure Container Instances |
| Cloud | `okw-env-hetzner` | Hetzner Cloud API |
| Special | `okw-env-testcontainers` | Testcontainers (Python) |
| Special | `okw-env-lxd` | LXD/Incus |

Start with Docker (90% of use cases) and Proxmox (existing infrastructure).
Others when needed — YAGNI.

## Signal vs. NOISE

| Signal (tester writes) | NOISE (framework handles) |
|---|---|
| "I need WebShop + DB" | Port mapping, network isolation |
| "WaitForReady" | Health check strategy |
| "StopEnvironment ALL" | Container cleanup, volume deletion |
| "version=17" | Compose file regeneration |
| "PostgresDB" | Docker Compose syntax |

| Persistent environment (NOISE) | Ephemeral environment (Signal) |
|---|---|
| Secrets vault for DB passwords | Password in test — doesn't matter |
| Network policies | Network dies with the test |
| Anonymize test data | Data dies with the test |
| Cleanup jobs for old data | Nothing to clean up |

## AI Perspective

This concept is highly AI-friendly:

1. **Generatability** — An AI can generate the complete test case including
   environment from a natural-language description. No separate Docker
   Compose knowledge needed.
2. **Readability** — `StartEnvironment PaymentGW image=payment:1.0` is
   instantly understandable. Docker Compose with networks, volumes,
   healthchecks requires parsing to find what's relevant.
3. **Reasoning** — When the environment is part of the test, an AI can:
   - Detect missing services ("Your test calls a payment API but Phase 0
     has no PaymentGW")
   - Suggest optimizations ("Tests A and B need the same environment —
     share it?")
   - Compare tests ("A and B differ only in environment — intentional?")

## Consistency with OKW GUI Architecture

| GUI world | Environment world |
|---|---|
| `okw4robot` (Core) | `okw-env` (Core) |
| `okw-web-selenium` | `okw-env-docker` |
| `okw-java-remoteswing` | `okw-env-proxmox` |
| Widget contract (`okw_click`, ...) | Provider contract (`create`, `start`, ...) |
| Widget YAML (locator) | Component YAML (image, port) |
| Adapter loads underlying library | Provider loads underlying API |
| `SetValue Field Value` | `StartEnvironment DB version=17` |
| Framework resolves locator | Framework generates Compose |
| Tester sees no Selenium | Tester sees no Docker |

### Why No Widget Layer for Environments?

In the GUI world, widgets (`WebSe_Button`, `RemoteSw_Button`, ...) are
technology-specific drivers — one per UI element type per technology.
The question arises: does the environment layer need a similar widget
abstraction for different component types (database, web app, queue, ...)?

**No.** The widgets in the GUI layer **are** the drivers — just fine-grained
per UI element. A `WebSe_Button` is a Selenium driver for buttons,
a `WebSe_Input` is a Selenium driver for input fields. The technology
determines how to interact with each element type.

For environments, this fine-granularity is unnecessary. A Docker container
is a Docker container — regardless of whether Postgres or a WebShop runs
inside it. The provider (Docker, Proxmox, ...) handles all component
types the same way: create, start, check health, stop, destroy.

The mapping is:

| GUI | Environment |
|---|---|
| `WebSe_Button` = Selenium driver for buttons | `okw-env-docker` = Docker driver for environments |
| `RemoteSw_Button` = Swing driver for buttons | `okw-env-proxmox` = Proxmox driver for environments |
| Fine-grained: one widget class per element type | Coarse-grained: one driver for all component types |
| Behavior differs per element (click vs. type vs. select) | Behavior is identical (create, start, stop, destroy) |

Project-specific customization happens entirely in YAML (which image,
which port, which env vars) — not in code. Same as GUI widgets, where
the locator YAML is project-specific, not the widget class.

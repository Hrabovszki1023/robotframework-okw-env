# robotframework-okw-env

[![PyPI](https://img.shields.io/pypi/v/robotframework-okw-env)](https://pypi.org/project/robotframework-okw-env/)
[![Python](https://img.shields.io/pypi/pyversions/robotframework-okw-env)](https://pypi.org/project/robotframework-okw-env/)
[![License](https://img.shields.io/badge/License-OKW_Community-orange.svg)](LICENSE)

Driver-agnostic environment abstraction for [OKW4Robot](https://github.com/Hrabovszki1023/robotframework-okw4robot).

> Deutsche Version: [README.de.md](README.de.md)

## What

One set of keywords (`StartEnvironment`, `StopEnvironment`, `WaitForReady`, ...)
to build, run, and tear down ephemeral test environments — regardless of the
underlying provider (Docker, Proxmox, Kubernetes, ...).

## Why — Signal vs. NOISE

Test code should describe **what** the test needs, not **how** infrastructure
is provisioned. Docker Compose syntax, Proxmox API calls, and Kubernetes
manifests are NOISE — the test only needs:

```robot
ENV_Start        WebShop
ENV_Start        PostgresDB    version=17
ENV_BuildAndRun
ENV_WaitForReady WebShop
```

## Architecture

```
┌──────────────────────────────┐
│  Robot Framework Test        │  ENV_Start, ENV_Stop, ...
├──────────────────────────────┤
│  okw-env (this library)      │  Keywords, YAML loader, provider contract
├──────────────┬───────────────┤
│  okw-env-    │  okw-env-     │  Provider plugins
│  docker      │  proxmox      │
├──────────────┼───────────────┤
│  Docker      │  Proxmox      │  Underlying APIs
│  Compose     │  VE API       │
└──────────────┴───────────────┘
```

## Install

```bash
pip install robotframework-okw-env
```

Plus one or more provider plugins:

```bash
pip install robotframework-okw-env-docker
pip install robotframework-okw-env-proxmox
```

## Component YAML

Environment components are defined in YAML — no infrastructure code in tests:

```yaml
PostgresDB:
  provider: docker
  image: postgres
  version: "17"
  port: 5432
  env:
    POSTGRES_DB: testdb
    POSTGRES_PASSWORD: test123
  healthcheck: "pg_isready -U postgres"
```

## Minimal Example

```robot
*** Settings ***
Library    okw4robot.library.OKW4RobotLibrary    WITH NAME    OKW

*** Test Cases ***
Order With Payment Gateway
    # Phase 0 — Environment
    ENV_Start        WebShop
    ENV_Start        PostgresDB
    ENV_Start        PaymentGW
    ENV_BuildAndRun
    ENV_WaitForReady WebShop

    # Phase 1-4 — Test
    StartApp         MyShop
    SetValue         Article      Laptop
    ClickOn          Order
    VerifyValue      Status       Paid
    StopApp

    # Phase 5 — Teardown
    ENV_Stop
```

## Key Benefits

- **Isolation** — Each test gets its own environment, enabling parallel execution
- **Ephemeral** — Environments exist only during test execution, no security concerns
- **Combinable** — Version matrix testing via templates
- **Provider-agnostic** — Same test, different infrastructure

## Runnable Examples

[okw-examples/env-docker/](https://github.com/Hrabovszki1023/okw-examples/tree/main/env-docker/) — Docker Compose environment provisioning.

## Handbuch

[OKW4Robot Handbuch](https://hrabovszki1023.github.io/okw-examples/) — step-by-step guide (German).

## Provider Plugins

| Plugin | Repository |
|---|---|
| [okw-env-docker](https://github.com/Hrabovszki1023/robotframework-okw-env-docker) | Docker Compose |
| [okw-env-proxmox](https://github.com/Hrabovszki1023/robotframework-okw-env-proxmox) | Proxmox VE |

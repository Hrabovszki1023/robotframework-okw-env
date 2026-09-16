# robotframework-okw-env

[![PyPI](https://img.shields.io/pypi/v/robotframework-okw-env)](https://pypi.org/project/robotframework-okw-env/)
[![Python](https://img.shields.io/pypi/pyversions/robotframework-okw-env)](https://pypi.org/project/robotframework-okw-env/)
[![License](https://img.shields.io/badge/License-OKW_Community-orange.svg)](LICENSE)

Treiberunabhängige Umgebungsabstraktion für [OKW4Robot](https://github.com/Hrabovszki1023/robotframework-okw4robot).

> **English version:** [README.md](README.md)

## Was

Ein Satz Keywords (`StartEnvironment`, `StopEnvironment`, `WaitForReady`, ...)
zum Erstellen, Starten und Abbauen ephemerer Testumgebungen — unabhängig vom
zugrunde liegenden Provider (Docker, Proxmox, Kubernetes, ...).

## Warum — Signal vs. NOISE

Testcode sollte beschreiben, **was** der Test braucht, nicht **wie** Infrastruktur
bereitgestellt wird. Docker-Compose-Syntax, Proxmox-API-Aufrufe und Kubernetes-
Manifeste sind NOISE — der Test braucht nur:

```robot
ENV_Start        WebShop
ENV_Start        PostgresDB    version=17
ENV_BuildAndRun
ENV_WaitForReady WebShop
```

## Architektur

```
┌──────────────────────────────┐
│  Robot Framework Test        │  ENV_Start, ENV_Stop, ...
├──────────────────────────────┤
│  okw-env (diese Bibliothek)  │  Keywords, YAML-Loader, Provider-Vertrag
├──────────────┬───────────────┤
│  okw-env-    │  okw-env-     │  Provider-Plugins
│  docker      │  proxmox      │
├──────────────┼───────────────┤
│  Docker      │  Proxmox      │  Zugrunde liegende APIs
│  Compose     │  VE API       │
└──────────────┴───────────────┘
```

## Installation

```bash
pip install robotframework-okw-env
```

Plus ein oder mehrere Provider-Plugins:

```bash
pip install robotframework-okw-env-docker
pip install robotframework-okw-env-proxmox
```

## Komponenten-YAML

Umgebungskomponenten werden in YAML definiert — kein Infrastrukturcode in Tests:

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

## Minimalbeispiel

```robot
*** Settings ***
Library    okw4robot.library.OKW4RobotLibrary    WITH NAME    OKW

*** Test Cases ***
Bestellung mit Zahlungs-Gateway
    # Phase 0 — Umgebung
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

## Vorteile

- **Isolation** — Jeder Test bekommt seine eigene Umgebung, parallele Ausführung möglich
- **Ephemer** — Umgebungen existieren nur während der Testausführung, keine Sicherheitsbedenken
- **Kombinierbar** — Versionsmatrix-Tests via Templates
- **Provider-unabhängig** — Gleicher Test, unterschiedliche Infrastruktur

## Lauffähige Beispiele

[okw-examples/env-docker/](https://github.com/Hrabovszki1023/okw-examples/tree/main/env-docker/) — Docker-Compose-Umgebungen bereitstellen.

## Handbuch

[OKW4Robot Handbuch](https://hrabovszki1023.github.io/okw-examples/) — Schritt-für-Schritt-Anleitung.

## Provider-Plugins

| Plugin | Repository |
|---|---|
| [okw-env-docker](https://github.com/Hrabovszki1023/robotframework-okw-env-docker) | Docker Compose |
| [okw-env-proxmox](https://github.com/Hrabovszki1023/robotframework-okw-env-proxmox) | Proxmox VE |

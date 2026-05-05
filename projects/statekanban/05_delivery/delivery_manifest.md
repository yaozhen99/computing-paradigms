# StateKanban Delivery Manifest

**Version:** 0.1.0 (semver initial release)
**Date:** 2026-05-05
**Integrator:** integration

---

## 1. Product Information

| Field | Value |
|-------|-------|
| Name | statekanban |
| Version | 0.1.0 |
| Description | StateKanban -- Instruction-level development engine |
| Python | >=3.11 |
| Entry point | statekanban.cli.main:cli |

---

## 2. Module Inventory

### 2.1 Core (statekanban/core/) -- Kernel, zero I/O

| Module | Version | File | Description |
|--------|---------|------|-------------|
| kanban | 0.1.0 | statekanban/core/kanban.py | StateKanban facade, FluidZone, CrystalZone, AuditZone, data types |
| errors | 0.1.0 | statekanban/core/errors.py | Error hierarchy (27 error codes across 10 families) |
| viewport | 0.1.0 | statekanban/core/viewport.py | ViewportSlicer, ViewportSlice -- context engineering for LLM |
| message_bus | 0.1.0 | statekanban/core/message_bus.py | In-memory pub/sub and sync call infrastructure |
| process | 0.1.0 | statekanban/core/process.py | ProcessManager -- lifecycle state machine (CREATED/ACTIVE/SUSPENDED/TERMINATED) |
| valve | 0.1.0 | statekanban/core/valve.py | OutputValve -- mandatory validation chain, atomic write guard |
| registry | 0.1.0 | statekanban/core/registry.py | ToolRegistry -- permission-gated dispatch with audit |

### 2.2 CLI (statekanban/cli/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| main | 0.1.0 | statekanban/cli/main.py | Click CLI: run, status, snapshot, restore commands + system bootstrap |

### 2.3 Adapters (statekanban/adapters/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| base | 0.1.0 | statekanban/adapters/base.py | LLMAdapter ABC |
| anthropic_adapter | 0.1.0 | statekanban/adapters/anthropic_adapter.py | Anthropic Messages API adapter (SDK, retry, streaming) |
| cli_adapter | 0.1.0 | statekanban/adapters/cli_adapter.py | Claude CLI subprocess adapter (transitional) |
| mock_adapter | 0.1.0 | statekanban/adapters/mock_adapter.py | Deterministic mock adapter for testing |

### 2.4 Roles (statekanban/roles/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| base | 0.1.0 | statekanban/roles/base.py | ProcessRole ABC |
| coder | 0.1.0 | statekanban/roles/coder.py | Coder role -- generates code artifacts |
| reviewer | 0.1.0 | statekanban/roles/reviewer.py | Reviewer role -- approves/rejects artifacts |
| tester | 0.1.0 | statekanban/roles/tester.py | Tester role -- validates via test execution |
| integrator | 0.1.0 | statekanban/roles/integrator.py | Integrator role -- integrates validated artifacts |
| architect | 0.1.0 | statekanban/roles/architect.py | Architect role -- designs architecture decisions |

### 2.5 Tools (statekanban/tools/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| write_file | 0.1.0 | statekanban/tools/write_file.py | Write artifact via OutputValve (coder, integrator) |
| read_file | 0.1.0 | statekanban/tools/read_file.py | Read file contents (all roles) |
| run_shell | 0.1.0 | statekanban/tools/run_shell.py | Execute shell command (integrator, tester) |
| call_llm | 0.1.0 | statekanban/tools/call_llm.py | Invoke LLM via adapter (all roles) |
| search_code | 0.1.0 | statekanban/tools/search_code.py | Search codebase patterns (all roles) |

### 2.6 Top-level

| Module | Version | File | Description |
|--------|---------|------|-------------|
| __init__ | 0.1.0 | statekanban/__init__.py | Package init, version declaration |
| snapshot | 0.1.0 | statekanban/snapshot.py | Snapshot save/load with atomic write and integrity check |
| config | 0.1.0 | statekanban/config.py | Global configuration dataclass |

### 2.7 Build

| File | Description |
|------|-------------|
| pyproject.toml | Build configuration (setuptools, dependencies, entry point) |

---

## 3. Complete File List

```
05_delivery/
  pyproject.toml
  statekanban/
    __init__.py
    config.py
    snapshot.py
    cli/
      __init__.py
      main.py
    core/
      __init__.py
      errors.py
      kanban.py
      message_bus.py
      process.py
      registry.py
      valve.py
      viewport.py
    adapters/
      __init__.py
      base.py
      anthropic_adapter.py
      cli_adapter.py
      mock_adapter.py
    roles/
      __init__.py
      base.py
      coder.py
      reviewer.py
      tester.py
      integrator.py
      architect.py
    tools/
      __init__.py
      write_file.py
      read_file.py
      run_shell.py
      call_llm.py
      search_code.py
```

**Total files: 32** (1 build config + 31 Python source files)

---

## 4. Dependencies

| Package | Version | Type |
|---------|---------|------|
| click | >=8.1 | runtime |
| anthropic | >=0.30 | runtime |
| pytest | >=7.0 | dev |
| pytest-asyncio | >=0.21 | dev |

---

## 5. Quality Gate Status

| Gate | Status | Details |
|------|--------|---------|
| Review | COMPLETED | 9/9 dimensions PASS, 3 advisory findings (non-blocking) |
| Testing | COMPLETED | 203/203 tests passed, 0 failures |
| Architecture compliance | PASS | All layers compliant |
| API contract compliance | PASS | All signatures match |
| Error code compliance | PASS | 27/27 codes match |
| Security review | PASS | 2 findings (non-blocking) |

---

## 6. Advisory Findings (from review, deferred to next iteration)

| ID | Severity | Description |
|----|----------|-------------|
| S-1 | Medium | TOCTOU in tools/read_file.py -- os.path.exists() before open() |
| S-2 | Low | OutputValve._inject_error_signal() derives code from error text; can emit SK_OV_000 |
| D-1 | Medium | FluidZone retains stale signals after same-key overwrite |

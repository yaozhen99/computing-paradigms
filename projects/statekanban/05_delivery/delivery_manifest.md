# StateKanban Delivery Manifest

**Version:** 0.3.0 (semver incremental release)
**Date:** 2026-05-05
**Integrator:** integration
**Previous version:** 0.2.0
**Round:** 3

---

## 1. Product Information

| Field | Value |
|-------|-------|
| Name | statekanban |
| Version | 0.3.0 |
| Description | StateKanban -- Instruction-level development engine |
| Python | >=3.11 |
| Entry point | statekanban.cli.main:cli |
| Increment type | Minor -- adds R3 incremental features: snapshot module, MockLLMAdapter enhancements, Engine-Registry integration, new error codes, null byte validation |

---

## 2. Module Inventory

### 2.1 Core (statekanban/core/) -- Kernel, zero I/O

| Module | Version | File | Description |
|--------|---------|------|-------------|
| kanban | 0.3.0 | statekanban/core/kanban.py | StateKanban facade, FluidZone (stale-signal fix), CrystalZone, AuditZone, data types |
| errors | 0.3.0 | statekanban/core/errors.py | Error hierarchy (34 error codes across 12 families, +CodexTimeoutError SK_CX_003, +ValveReworkLoopError SK_EN_004) |
| viewport | 0.3.0 | statekanban/core/viewport.py | ViewportSlicer, ViewportSlice -- context engineering for LLM |
| message_bus | 0.3.0 | statekanban/core/message_bus.py | In-memory pub/sub and sync call infrastructure |
| process | 0.3.0 | statekanban/core/process.py | ProcessManager -- lifecycle state machine |
| valve | 0.3.0 | statekanban/core/valve.py | OutputValve -- type-derived error codes (RR-002 fix), validation chain, atomic write guard |
| registry | 0.3.0 | statekanban/core/registry.py | ToolRegistry -- permission-gated dispatch with audit, timeout signal injection |

### 2.2 Engine (statekanban/engine/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| engine | 0.3.0 | statekanban/engine/engine.py | Engine -- drive loop orchestrator, routes LLM calls via ToolRegistry (REQ-005), rework loop detection (REQ-007), _build_context helper |
| response_parser | 0.3.0 | statekanban/engine/response_parser.py | ResponseParser -- 3-strategy LLM response parsing (JSON, code block, error) |
| convergence | 0.3.0 | statekanban/engine/convergence.py | ConvergenceDetector -- round-aware convergence check |
| scheduler | 0.3.0 | statekanban/engine/scheduler.py | RoleScheduler -- Coder->Reviewer->Tester->Integrator order |
| circuit_breaker | 0.3.0 | statekanban/engine/circuit_breaker.py | CircuitBreaker -- max rounds enforcement |
| result | 0.3.0 | statekanban/engine/result.py | ResultSummarizer, EngineResult -- end-of-loop summary |
| router | 0.3.0 | statekanban/engine/router.py | SignalRouter -- signal-to-role routing rules |

### 2.3 CLI (statekanban/cli/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| main | 0.3.0 | statekanban/cli/main.py | CLI: drive (--structured, --behavior, --snapshot-save, --no-registry), snapshot save/load/list/delete + system bootstrap |

### 2.4 Adapters (statekanban/adapters/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| base | 0.3.0 | statekanban/adapters/base.py | LLMAdapter ABC |
| anthropic_adapter | 0.3.0 | statekanban/adapters/anthropic_adapter.py | Anthropic Messages API adapter |
| cli_adapter | 0.3.0 | statekanban/adapters/cli_adapter.py | Claude CLI subprocess adapter |
| mock_adapter | 0.3.0 | statekanban/adapters/mock_adapter.py | Enhanced MockLLM adapter: structured_mode (REQ-001), behavior modes (REQ-002), MockReviewerBehavior/MockCoderBehavior enums |
| codex_adapter | 0.3.0 | statekanban/adapters/codex_adapter.py | CodexAdapter -- null bytes validation (REQ-008), CodexTimeoutError on timeout (REQ-006) |

### 2.5 Roles (statekanban/roles/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| base | 0.3.0 | statekanban/roles/base.py | ProcessRole ABC |
| coder | 0.3.0 | statekanban/roles/coder.py | Coder role -- generates code artifacts |
| reviewer | 0.3.0 | statekanban/roles/reviewer.py | Reviewer role -- approves/rejects artifacts |
| tester | 0.3.0 | statekanban/roles/tester.py | Tester role -- validates via test execution |
| integrator | 0.3.0 | statekanban/roles/integrator.py | Integrator role -- integrates validated artifacts |
| architect | 0.3.0 | statekanban/roles/architect.py | Architect role -- designs architecture decisions |

### 2.6 Tools (statekanban/tools/)

| Module | Version | File | Description |
|--------|---------|------|-------------|
| write_file | 0.3.0 | statekanban/tools/write_file.py | Write artifact via OutputValve |
| read_file | 0.3.0 | statekanban/tools/read_file.py | Read file contents (TOCTOU fix: direct open + exception catch) |
| run_shell | 0.3.0 | statekanban/tools/run_shell.py | Execute shell command |
| call_llm | 0.3.0 | statekanban/tools/call_llm.py | Invoke LLM via adapter (REQ-005a): nested output dict format, null bytes validation (REQ-008), error_code in failure response |
| call_codex | 0.3.0 | statekanban/tools/call_codex.py | Generate code via Codex CLI: null bytes validation (REQ-008), CodexTimeoutError classification (REQ-006) |
| search_code | 0.3.0 | statekanban/tools/search_code.py | Search codebase patterns |

### 2.7 Top-level

| Module | Version | File | Description |
|--------|---------|------|-------------|
| __init__ | 0.3.0 | statekanban/__init__.py | Package init, version declaration |
| snapshot | 0.3.0 | statekanban/snapshot.py | Snapshot save/load with atomic write and SHA-256 integrity check (REQ-003) |
| config | 0.3.0 | statekanban/config.py | Global configuration dataclass (+codex settings) |

### 2.8 Testing (statekanban/testing/) -- NEW in R3

| Module | Version | File | Description |
|--------|---------|------|-------------|
| __init__ | 0.3.0 | statekanban/testing/__init__.py | Testing package init |
| e2e_helpers | 0.3.0 | statekanban/testing/e2e_helpers.py | E2E test helper utilities |

### 2.9 Build

| File | Description |
|------|-------------|
| pyproject.toml | Build configuration (setuptools, dependencies, entry point, version 0.3.0) |

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
    engine/
      __init__.py
      engine.py
      response_parser.py
      convergence.py
      scheduler.py
      circuit_breaker.py
      result.py
      router.py
    adapters/
      __init__.py
      base.py
      anthropic_adapter.py
      cli_adapter.py
      codex_adapter.py
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
      call_codex.py
      search_code.py
    testing/
      __init__.py
      e2e_helpers.py
```

**Total files: 44** (1 build config + 43 Python source files)

**Increment from 0.2.0:** +3 files (snapshot.py already in R2 source but not in R2 delivery; testing/__init__.py, testing/e2e_helpers.py), plus updates to 7 existing files (mock_adapter.py, codex_adapter.py, call_codex.py, call_llm.py, engine.py, errors.py, __init__.py, cli/main.py)

---

## 4. Dependencies

| Package | Version | Type |
|---------|---------|------|
| click | >=8.1 | runtime |
| anthropic | >=0.30 | runtime |
| pytest | >=7.0 | dev |
| pytest-asyncio | >=0.21 | dev |

---

## 5. R3 REQ Implementation Status

| REQ | Title | Status | Module(s) |
|-----|-------|--------|-----------|
| REQ-001 | MockLLMAdapter structured_mode | IMPLEMENTED | adapters/mock_adapter.py |
| REQ-002 | MockLLMAdapter behavior modes | IMPLEMENTED | adapters/mock_adapter.py |
| REQ-003 | Snapshot module | IMPLEMENTED | snapshot.py |
| REQ-004 | E2E test architecture | IMPLEMENTED | testing/e2e_helpers.py |
| REQ-005a | call_llm tool | IMPLEMENTED | tools/call_llm.py |
| REQ-005 | Engine via ToolRegistry | IMPLEMENTED | engine/engine.py |
| REQ-006 | SK_CX_003 CodexTimeoutError | IMPLEMENTED | core/errors.py, adapters/codex_adapter.py |
| REQ-007 | SK_EN_004 ValveReworkLoopError | IMPLEMENTED | core/errors.py, engine/engine.py |
| REQ-008 | SK_TR_004 null bytes validation | IMPLEMENTED | tools/call_codex.py, adapters/codex_adapter.py, tools/call_llm.py |

---

## 6. Quality Gate Status

| Gate | Status | Details |
|------|--------|---------|
| Testing | COMPLETED | 381/381 tests passed, 0 failures, 73% coverage |
| Architecture compliance | PASS | All modules in correct layer, snapshot.py at package root |
| API contract compliance | PASS | All R3 contracts match api_contracts.md |
| Error code compliance | PASS | 34 codes, SK_CX_003 and SK_EN_004 now implemented |
| Security review | PASS | Null byte validation at all Codex entry points (REQ-008) |
| R2 advisory fix verification | PASS | R2-CON-001, R2-ECO-001, R2-ECO-002, R2-SEC-001 all fixed |

---

## 7. Advisory Findings from R3 Review

| ID | Severity | Module | Description |
|----|----------|--------|-------------|
| R3-ARCH-002 | Low | codex_adapter.py | Imports core.kanban data types beyond core.errors (LLMMessage, LLMResponse are data types, not I/O) |
| R3-RR001 | Low | snapshot.py | TOCTOU in delete_snapshot() -- os.path.exists() then os.remove() (not a security risk for delete operations) |

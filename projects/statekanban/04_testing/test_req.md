# StateKanban Test Requirements Document

## 1. Overview

This document defines the testing requirements for the StateKanban system, covering all modules specified in the architecture (02_design/architecture.md) and API contracts (02_design/api_contracts.md).

## 2. Test Scope

### 2.1 Modules Under Test

| Module | Source File | Priority |
|--------|-----------|----------|
| FluidZone | core/kanban.py | P0 |
| CrystalZone | core/kanban.py | P0 |
| AuditZone | core/kanban.py | P0 |
| StateKanban (facade) | core/kanban.py | P0 |
| MessageBus | core/message_bus.py | P0 |
| ViewportSlicer | core/viewport.py | P0 |
| OutputValve | core/valve.py | P0 |
| ToolRegistry | core/registry.py | P0 |
| ProcessManager | core/process.py | P0 |
| Error hierarchy | core/errors.py | P1 |
| Snapshot | snapshot.py | P0 |
| Config | config.py | P1 |
| LLM Adapters | adapters/ | P1 |
| CLI | cli/main.py | P1 |
| Tools (write_file, read_file, etc.) | tools/ | P1 |

### 2.2 Out of Scope

- External API calls to Anthropic (tested via MockLLMAdapter)
- Actual LLM response quality
- Performance benchmarks (deferred)
- P2 features (human gate) beyond stub validation

## 3. Test Levels

### 3.1 Unit Tests

- Each module tested in isolation
- Mock dependencies where necessary
- Focus on: boundary conditions, error paths, state transitions

### 3.2 Integration Tests

- Cross-module interaction tests
- Full pipeline: signal -> collision -> convergence -> artifact
- ToolRegistry + OutputValve integration
- ProcessManager + StateKanban snapshot round-trip
- MessageBus + StateKanban audit integration

### 3.3 Contract Tests

- Error code consistency with api_contracts.md section 3.2
- API signature conformance with api_contracts.md section 2.x
- Data structure serialization/deserialization round-trips

## 4. Key Test Areas

### 4.1 StateKanban FluidZone/CrystalZone Operations and Collision Convergence

- Signal write/read with all filter combinations
- Collision detection: INTENT+VETO conflict, no conflict, resolved
- Convergence loop: agreement before max rounds, forced terminate at 10 rounds
- Signal clearing by round number
- Invalid signal validation
- CrystalZone append-only enforcement: auto-assign seq_no, duplicate detection
- AuditZone monotonic entry IDs and filtering

### 4.2 MessageBus Pub/Sub/Sync/Async

- Subscribe/unsubscribe lifecycle
- Publish dispatches to matching subscribers
- Sync call with handler and timeout
- Async notify fire-and-forget
- Invalid subscription handling
- Sync call timeout raises SyncCallTimeoutError

### 4.3 ViewportSlicer Role-Aware Slicing and Token Budget

- Role-based signal/artifact filtering
- Target pattern matching (glob)
- Priority ordering (role_relevant -> dependency_upstream -> global_summary)
- Token budget truncation
- SliceOverflowError when nothing fits
- InvalidViewportSpecError for unknown roles

### 4.4 OutputValve Validation Chain and Atomic Write

- Sequential fail-fast validation
- SyntaxValidator: Python AST, JSON parsing
- On validation failure: ErrorSignal injected into FluidZone
- On success: atomic write via temp+rename
- AtomicWriteError on I/O failure
- Custom validator insertion

### 4.5 ToolRegistry Permission Control and Audit

- Permission check: allowed roles pass, denied roles raise PermissionDeniedError
- Tool not found raises ToolNotFoundError
- Timeout raises ToolTimeoutError + error signal injection
- Audit logging on every dispatch
- Duplicate tool registration raises ToolNotFoundError
- Parameter hashing for audit

### 4.6 ProcessManager State Machine and Anti-Self-Termination

- Valid transitions: CREATED->ACTIVE, ACTIVE->SUSPENDED, SUSPENDED->ACTIVE, ACTIVE->TERMINATED, SUSPENDED->TERMINATED
- Invalid transitions raise InvalidStateTransitionError
- Self-termination raises SelfTerminationError
- claim_primary: terminate old, activate new, inherit viewport
- HandoffError when no predecessor
- Heartbeat recording and timeout detection
- Process listing and filtering by state

### 4.7 Snapshot Save/Restore

- to_json -> from_json round-trip preserves all data
- Checksum validation: valid checksum passes, tampered data raises SnapshotIntegrityError
- save_snapshot writes to file atomically
- load_snapshot from missing file raises FileNotFoundError
- load_snapshot from invalid JSON raises SnapshotIntegrityError

### 4.8 Error Codes and API Contract Consistency

- Every error class has correct error_code matching api_contracts.md
- Every error class has correct http_analogy
- Error hierarchy matches architecture section 4.1

### 4.9 Paper-Defined Metrics

- Convergence rate: % of collisions that converge within max rounds
- Interception rate: % of invalid writes caught by OutputValve
- Lossless handoff: claim_primary preserves viewport and state

## 5. Acceptance Criteria

- All unit tests pass
- All integration tests pass
- All contract tests pass
- Code coverage >= 80% for core/ modules
- Zero regressions on repeated runs

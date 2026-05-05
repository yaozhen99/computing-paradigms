# StateKanban Architecture Overview

---

## 1. System Purpose

StateKanban is a pure in-memory LLM dispatch kernel that demotes LLMs to stateless compute units. The kanban board is the single source of truth. Viewport slicing controls context, and the output valve guarantees write safety. The kernel has zero direct I/O; all external actions are tool calls.

---

## 2. Layered Architecture

```
+================================================================+
|                        CLI Layer (click)                        |
|  statekanban run | statekanban status | statekanban snapshot    |
+================================================================+
                                |
                                v
+================================================================+
|                    Orchestration Layer                          |
|  ProcessManager | Scheduler | Lifecycle State Machine           |
+================================================================+
                                |
                                v
+================================================================+
|                     Process Layer                               |
|  Coder | Reviewer | Tester | Integrator | Architect            |
|  (Each process = role + viewport + tool permit)                 |
+================================================================+
               |              |              |
               v              v              v
+==================+  +================+  +================+
|  ViewportSlicer  |  |  MessageBus    |  |  ToolRegistry  |
|  (context cut)   |  |  (pub/sub+rpc) |  |  (permit+call) |
+==================+  +================+  +================+
               |              |              |
               v              v              v
+================================================================+
|                   StateKanban (Single Source of Truth)          |
|  +-------------------+  +------------------+  +--------------+ |
|  |    FluidZone      |  |   CrystalZone    |  |  AuditZone   | |
|  | intent/veto/      |  | append-only      |  | action log   | |
|  | collision/converge|  | code/config/doc  |  |              | |
|  +-------------------+  +------------------+  +--------------+ |
+================================================================+
               |
               v
+================================================================+
|                    OutputValve (Guard)                          |
|  syntax check -> type check -> test run -> atomic write         |
+================================================================+
               |
               v
+================================================================+
|                    LLM Adapter Layer                            |
|  AnthropicMessagesAdapter | ClaudeCLIAdapter | MockLLMAdapter  |
+================================================================+
               |
               v
+================================================================+
|                    Infrastructure (OS Boundary)                 |
|  filesystem (write_file/read_file) | shell (run_shell)         |
|  anthropic API (call_llm)         | code search (search_code)  |
+================================================================+
```

---

## 3. Layer Responsibilities

| Layer | Responsibility | Key Constraint |
|-------|---------------|----------------|
| **CLI** | User interaction, command parsing | No business logic |
| **Orchestration** | Process lifecycle, scheduling, heartbeat | Owns ProcessManager state machine |
| **Process** | Role-specific logic, signal production/consumption | Stateless: each invocation rebuilds context from viewport |
| **Middleware** | Slicing, messaging, tool dispatch | No persistent state |
| **StateKanban** | Single source of truth, collision detection, convergence | FluidZone mutable, CrystalZone append-only, AuditZone append-only |
| **OutputValve** | Validation chain, atomic write | No write bypass allowed |
| **LLM Adapter** | Unified LLM call interface | Kernel never touches SDK directly |
| **Infrastructure** | Physical I/O via tools | Only accessible through ToolRegistry |

---

## 4. Core Modules

### 4.1 StateKanban (StateKanban Core)

The central data structure and single source of truth.

**FluidZone** -- Mutable signal area:
- Stores `IntentSignal`, `VetoSignal`, and `ErrorSignal` objects
- Detects collisions (same target, conflicting INTENT and VETO signals)
- Drives convergence loops until consensus or force-terminate at 10 rounds
- Signals are keyed by `(target_id, signal_type, author_role)`

**CrystalZone** -- Immutable production area:
- Append-only store for confirmed artifacts (code, config, docs)
- Each artifact gets a monotonically increasing sequence number
- No delete or update operations; only `append()` exists

**AuditZone** -- Append-only log:
- Records every tool call, signal transition, state mutation
- Entries are timestamped with monotonic counters

**ViewportIndex** -- Per-process window:
- Each process has a named viewport mapped to a `ViewportSpec`
- Viewports filter FluidZone and CrystalZone by signal type, artifact type, and target patterns
- Viewports are recalculated on every read (no cache staleness)

**Snapshot** -- Full-state serialization:
- `to_json()` serializes all zones, viewport specs, and process states with SHA-256 checksum
- `from_json()` reconstructs the entire kanban, verifying checksum integrity

### 4.2 MessageBus

In-memory publish/subscribe and synchronous call infrastructure.

- **Pub/Sub**: Processes subscribe to signal types; bus dispatches to matching callbacks
- **Sync Call**: Caller blocks until callee returns a result (via `asyncio.Future`)
- **Async Notify**: Fire-and-forget signal delivery (best-effort)
- **No persistence**: Messages exist only in memory; StateKanban is the durability layer

### 4.3 ViewportSlicer

Context engineering for LLM calls. This is the mechanism that makes LLM invocations stateless.

- **Role-aware slicing**: Each role has a `ViewportSpec` defining visible signal types, artifact types, and target patterns
- **Token budget**: Hard limit (default 2000 tokens) per LLM call
- **Priority order**: (1) role-relevant signals, (2) dependency-chain upstream, (3) global summary
- **Truncation**: When budget is exceeded, lowest-priority items are dropped first
- **SliceOverflowError**: Raised if even a single item cannot fit within the budget

### 4.4 OutputValve

The mandatory write guard. No physical I/O bypasses this module.

- **Validation chain** (sequential, fail-fast):
  1. Syntax check (AST parse for Python, JSON parse for configs)
  2. Type check (optional, extensible stub)
  3. Test execution (extensible stub for pytest subprocess)
- **On failure**: ErrorSignal injected into FluidZone, tagged with failed artifact and validator name
- **On success**: Atomic write via temp file + `os.replace()` (POSIX) / `os.rename()` with fallback (Windows)
- **Human gate** (P2): Optional confirmation step after auto-validation passes

### 4.5 ToolRegistry

Permission-gated tool dispatch with audit logging.

- **Registration**: Tools are async callables registered with name, param schema, and required permission set
- **Permission check**: Each process has a `set[ToolName]` permit; unauthorized calls raise `PermissionDeniedError`
- **Audit trail**: Every invocation logged to AuditZone with tool name, caller, params hash, result status, and duration
- **Timeout/retry**: Configurable per tool; timeout raises `ToolTimeoutError` and injects ErrorSignal into FluidZone

### 4.6 ProcessManager

Lifecycle management for internal processes.

- **State machine**: `CREATED -> ACTIVE -> SUSPENDED -> TERMINATED`
- **No self-termination**: A process cannot transition itself to TERMINATED; only the scheduler can
- **Heartbeat**: Each active process writes a heartbeat timestamp every N seconds (default 30s)
- **Handoff**: New process `claim_primary()` terminates predecessor and inherits viewport
- **Crash recovery**: If heartbeat exceeds threshold (default 90s), process is recreated from last snapshot

---

## 5. Data Flow Diagrams

### 5.1 Happy Path: Code Generation Cycle

```
User --[CLI: run --intent]--> ProcessManager
  |
  +-- creates Coder process
  +-- creates Reviewer process
  +-- creates Tester process
  |
  v
ProcessManager --[activate Coder]--> Coder
  |
  Coder --[viewport read]--> ViewportSlicer --[slice]--> StateKanban (FluidZone)
  |                                                              |
  Coder --[call_llm]--> ToolRegistry --> LLMAdapter
  |                                                              |
  Coder <--[LLMResponse with tool_use: write_file]--
  |                                                              |
  Coder --[write_file(intent)]--> ToolRegistry --[permit check]--> OutputValve
  |                                                              |
  |                                              OutputValve --[syntax]--> pass
  |                                              OutputValve --[type check]--> pass
  |                                              OutputValve --[test]--> pass
  |                                              OutputValve --[atomic write]--> filesystem
  |                                                              |
  Coder --[IntentSignal(target=artifact)]--> FluidZone
  |
  StateKanban --[collision detect]--> (no veto yet) --> IntentSignal confirmed
  |
  MessageBus --[notify Reviewer]--> Reviewer
  |
  Reviewer --[viewport read]--> ViewportSlicer --> StateKanban
  |
  Reviewer --[IntentSignal(approve) or VetoSignal(reject)]--> FluidZone
```

### 5.2 Collision and Convergence Flow

```
FluidZone: [Coder:Intent(approve, artifact_A), Reviewer:Veto(reject, artifact_A)]
  |
  v
StateKanban --[detect_collision(artifact_A)]--> convergence loop
  |
  Loop iteration:
    1. ViewportSlicer provides collision context to both roles
    2. Coder sees veto reason, generates revised IntentSignal
    3. Reviewer sees revised intent, generates new signal
    4. If signals agree -> convergence achieved -> artifact moves to CrystalZone
    5. If signals disagree -> next iteration
    6. If iteration > 10 -> force terminate, mark "unconverged" in AuditZone
  |
  v
Converged: CrystalZone.append(artifact_A)
           AuditZone.log(convergence_rounds, final_signals)
```

### 5.3 Validation Failure and Rework Flow

```
OutputValve --[syntax check FAIL]--> ValidationFailedError
  |
  v
ErrorSignal(source=OutputValve, target=Coder, reason="syntax error") --> FluidZone
  |
  v
MessageBus --[notify Coder]--> Coder
  |
  Coder --[viewport includes error signal]--> ViewportSlicer
  |
  Coder --[rework via call_llm]--> ... (revised artifact)
  |
  Coder --[write_file(revised)]--> ToolRegistry --> OutputValve (retry validation)
```

### 5.4 Crash Recovery Flow

```
Process crash detected (heartbeat timeout)
  |
  v
ProcessManager --[load latest snapshot]--> StateKanban.from_json(snapshot_data)
  |
  v
ProcessManager --[recreate processes from snapshot]--> ProcessManager
  |
  v
Each process resumes with last known viewport
  |
  v
FluidZone signals preserved -> convergence can resume
CrystalZone artifacts preserved -> no lost work
```

---

## 6. Dependency Graph

```
CLI
  --> ProcessManager
        --> StateKanban
        --> MessageBus
              --> StateKanban (audit)
  --> StateKanban (snapshot/restore)

ProcessRole (Coder, Reviewer, etc.)
  --> ViewportSlicer --> StateKanban
  --> MessageBus
  --> ToolRegistry
        --> StateKanban (audit)
        --> OutputValve (for write_file)
              --> StateKanban (error signal injection)

StateKanban
  --> (no external dependencies -- pure data structure)

LLMAdapter
  --> (no internal dependencies -- wraps external SDK)

MessageBus
  --> StateKanban (audit only)
```

---

## 7. Initialization Order

The system must be initialized in the following order to satisfy dependency constraints:

1. `StateKanban()` -- no dependencies
2. `MessageBus(kanban)` -- depends on StateKanban (audit)
3. `ToolRegistry(kanban)` -- depends on StateKanban (audit)
4. `OutputValve(validators, kanban)` -- depends on StateKanban (error signal injection)
5. `ViewportSlicer(kanban, specs)` -- depends on StateKanban (read)
6. `ProcessManager(kanban, bus)` -- depends on StateKanban + MessageBus
7. `LLMAdapter` -- no internal dependencies
8. Process roles -- depend on ViewportSlicer, MessageBus, ToolRegistry

---

## 8. Inter-Module Interface Contracts

### StateKanban <-> ViewportSlicer
- **Inbound**: ViewportSlicer calls `kanban.fluid.read_signals()` and `kanban.crystal.read_artifacts()` with ViewportSpec-derived filters
- **Contract**: ViewportSlicer never mutates StateKanban; it is a pure read projection

### StateKanban <-> MessageBus
- **Inbound**: MessageBus calls `kanban.audit.log()` for delivery events
- **Contract**: MessageBus is a transport layer; it does not generate signals

### ProcessRole <-> ToolRegistry
- **Inbound**: ProcessRole calls `registry.dispatch(tool_name, caller_role, params)`
- **Contract**: ProcessRole must handle both success and error ToolResults; on error, it writes an ErrorSignal to FluidZone

### ToolRegistry <-> OutputValve
- **Inbound**: ToolRegistry delegates `write_file` to `valve.validate_and_write(artifact)`
- **Contract**: If ValveResult.success is False, ToolRegistry creates a ToolResult with the error and writes an ErrorSignal to FluidZone

### OutputValve <-> StateKanban
- **Inbound**: On validation failure, OutputValve injects ErrorSignal into `kanban.fluid.write_signal()`
- **Contract**: OutputValve only writes ErrorSignals; it never writes IntentSignal or VetoSignal

### ProcessManager <-> StateKanban
- **Contract**: ProcessManager is the sole authority on process state; StateKanban stores it but does not mutate it

---

## 9. Security Design

### Security Invariants

1. **Kernel I/O isolation**: The kernel package (`statekanban.core`) contains zero direct calls to `open()`, `subprocess`, `os.system()`, `socket`, or `requests`. All I/O goes through ToolRegistry.
2. **Tool permit enforcement**: Every tool call passes through `ToolRegistry.dispatch()` which checks the caller's permit set.
3. **Append-only crystal**: `CrystalZone` has no `update()` or `delete()` methods; the only mutation is `append()`.
4. **OutputValve mandatory path**: The `write_file` tool delegates to OutputValve. There is no alternative code path that writes to the filesystem.
5. **Atomic write guarantee**: OutputValve uses temp-file + `os.replace()`. If the process crashes mid-write, the temp file is orphaned (never partially written to the target).
6. **Snapshot integrity**: Snapshots include SHA-256 checksums; on restore, the checksum is verified before state reconstruction.

### Threat Model

| Threat | Vector | Mitigation |
|--------|--------|------------|
| LLM prompt injection | Malicious user intent or LLM output | ViewportSlicer strips raw user input; OutputValve validates all writes |
| Privilege escalation | LLM outputs tool_use for unauthorized tool | ToolRegistry enforces per-role permit set |
| Data tampering | Process modifies CrystalZone | CrystalZone is append-only at API level |
| Write bypass | Process writes directly to filesystem | Kernel has zero I/O; only ToolRegistry + OutputValve touch filesystem |
| Snapshot tampering | Corrupted snapshot file | Checksum validation on load |
| Denial of service | Process spams signals or tool calls | Convergence hard-stop at 10 rounds; tool call timeout |

---

## 10. Error Handling Strategy

### Error Hierarchy

```
StateKanbanError (base)
  +-- FluidZoneError
  |     +-- SignalCollisionError
  |     +-- ConvergenceTimeoutError
  |     +-- InvalidSignalError
  +-- CrystalZoneError
  |     +-- ArtifactConflictError
  |     +-- AppendOnlyViolationError
  +-- AuditZoneError
  |     +-- AuditWriteError
  +-- ViewportError
  |     +-- SliceOverflowError
  |     +-- InvalidViewportSpecError
  +-- OutputValveError
  |     +-- ValidationFailedError
  |     |     +-- SyntaxCheckError
  |     |     +-- TypeCheckError
  |     |     +-- TestExecutionError
  |     +-- AtomicWriteError
  |     +-- HumanGateRejectedError
  +-- ToolRegistryError
  |     +-- PermissionDeniedError
  |     +-- ToolNotFoundError
  |     +-- ToolTimeoutError
  +-- ProcessManagerError
  |     +-- InvalidStateTransitionError
  |     +-- SelfTerminationError
  |     +-- HeartbeatTimeoutError
  |     +-- HandoffError
  +-- MessageBusError
  |     +-- SubscriptionError
  |     +-- SyncCallTimeoutError
  +-- LLMAdapterError
  |     +-- LLMRateLimitError
  |     +-- LLMAuthError
  |     +-- LLMResponseParseError
  +-- SnapshotError
        +-- SnapshotIntegrityError
        +-- SnapshotWriteError
```

### Error Propagation Principles

1. **Fail-loud at boundaries**: Errors at system boundaries (LLM call, file I/O, CLI) are raised explicitly
2. **Signal-back on process errors**: Errors within a process loop are converted to signals in FluidZone, not propagated as exceptions across modules
3. **Never crash the kernel**: StateKanban core, MessageBus, and ProcessManager catch, log, and degrade gracefully
4. **Audit everything**: Every error that results in a state change is logged to AuditZone
5. **Recoverable by default**: All transient errors (LLM timeout, tool timeout) are recoverable via signal re-injection; only data integrity errors are fatal
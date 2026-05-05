# StateKanban -- System Architecture (Round 2)

> Incremental update over Round 1. Adds Engine module, CodexAdapter, call_codex tool,
> LLM response parsing, collision convergence automation, role scheduling, and circuit breaker.

## 1. Layered Architecture

```
+================================================================+
|                        CLI Layer (click)                        |
|  statekanban run | status | snapshot | restore                  |
|  --adapter {mock,anthropic,cli,codex} --max-rounds N --verbose |
+================================================================+
                                |
                                v
+================================================================+
|                    Engine Layer (NEW)                            |
|  Engine: drive loop | signal route | LLM parse | converge       |
|          schedule roles | circuit break | result summary        |
+================================================================+
                                |
                                v
+================================================================+
|                    Orchestration Layer                           |
|  ProcessManager | Scheduler | Lifecycle State Machine            |
+================================================================+
                                |
                                v
+================================================================+
|                     Process Layer                               |
|  Coder | Reviewer | Tester | Integrator | Architect             |
|  (Each process = role + viewport + tool permit)                |
+================================================================+
               |              |              |
               v              v              v
+==================+  +================+  +================+
|  ViewportSlicer  |  |  MessageBus    |  |  ToolRegistry  |
|  (context cut)   |  |  (pub/sub+rpc)|  |  (permit+call) |
+==================+  +================+  +================+
               |              |              |
               v              v              v
+================================================================+
|                   StateKanban (Single Source of Truth)           |
|  +-------------------+  +------------------+  +--------------+   |
|  |    FluidZone      |  |   CrystalZone    |  |  AuditZone   |   |
|  | intent/veto/      |  | append-only      |  | action log   |   |
|  | error/collision/  |  | code/config/doc  |  |              |   |
|  | converge          |  |                  |  |              |   |
|  +-------------------+  +------------------+  +--------------+   |
+================================================================+
               |
               v
+================================================================+
|                    OutputValve (Guard)                          |
|  syntax check -> type check -> test run -> atomic write        |
+================================================================+
               |
               v
+================================================================+
|                    LLM Adapter Layer                            |
|  AnthropicMessagesAdapter | ClaudeCLIAdapter | MockLLMAdapter   |
|  CodexAdapter (NEW)                                            |
+================================================================+
               |
               v
+================================================================+
|                    Infrastructure (OS Boundary)                 |
|  filesystem (write_file/read_file) | shell (run_shell)         |
|  anthropic API (call_llm)         | codex CLI (call_codex)      |
|  code search (search_code)                                     |
+================================================================+
```

### Layer Responsibilities

| Layer | Responsibility | Key Constraint |
|-------|---------------|----------------|
| CLI | User interaction, command parsing, option handling | No business logic |
| Engine | Drive loop, signal routing, LLM parse, convergence, role scheduling, circuit breaker | Stateless between rounds; reads all state from kanban |
| Orchestration | Process lifecycle, scheduling, heartbeat | Owns ProcessManager state machine |
| Process | Role-specific logic, signal production/consumption | Stateless: each invocation rebuilds context from viewport |
| Middleware | Slicing, messaging, tool dispatch | No persistent state |
| StateKanban | Single source of truth, collision detection, convergence | FluidZone mutable, CrystalZone append-only, AuditZone append-only |
| OutputValve | Validation chain, atomic write | No write bypass |
| LLM Adapter | Unified LLM/Codex call interface | Kernel never touches SDK directly; adapter encapsulates |
| Infrastructure | Physical I/O via tools | Only accessible through ToolRegistry |

## 2. Engine Module (NEW)

The Engine is the top-level orchestrator that transforms the static kernel into a running system. It does not replace any existing module; it composes them into a drive loop.

### 2.1 Internal Architecture

```
+================================================================+
|                          Engine                                 |
|                                                                 |
|  +--------------------+  +--------------------+                |
|  | SignalRouter        |  | ResponseParser      |                |
|  | - route(signal)     |  | - parse(raw_text)    |                |
|  |   -> role           |  |   -> ParsedResponse  |                |
|  +--------------------+  +--------------------+                |
|                                                                 |
|  +--------------------+  +--------------------+                |
|  | ConvergenceDetector |  | CircuitBreaker      |                |
|  | - check(target_id)  |  | - should_break()     |                |
|  |   -> bool           |  | - report()          |                |
|  +--------------------+  +--------------------+                |
|                                                                 |
|  +--------------------+  +--------------------+                |
|  | RoleScheduler       |  | ResultSummarizer    |                |
|  | - next_role()       |  | - summarize()       |                |
|  | - order: [C,R,T,I]  |  |   -> EngineResult   |                |
|  +--------------------+  +--------------------+                |
|                                                                 |
|  +----------------------------------------------------+        |
|  | Drive Loop                                          |        |
|  | while not converged and not circuit_broken:          |        |
|  |   for role in schedule:                              |        |
|  |     signals = read_unprocessed(role)                 |        |
|  |     slice = viewport.slice(role)                     |        |
|  |     response = llm.complete(slice)                   |        |
|  |     parsed = parser.parse(response)                  |        |
|  |     inject_signals(parsed)                           |        |
|  |   collision = convergence_detector.check()           |        |
|  |   if converged: crystal_fix + valve_write             |        |
|  +----------------------------------------------------+        |
+================================================================+
```

### 2.2 Engine Responsibilities

| Sub-component | Responsibility | Collaborates With |
|---------------|---------------|-------------------|
| SignalRouter | Given a signal, determine which role should process it | FluidZone (read), ProcessManager (role lookup) |
| ResponseParser | Parse raw LLM text into typed signal (intent/veto/artifact/error) | FluidZone (write error on parse failure), AuditZone (log parse attempts) |
| ConvergenceDetector | Check if all signals for a target_id agree (no pending veto) | FluidZone (read), StateKanban.run_convergence() |
| CircuitBreaker | Track round count; force-terminate when max_rounds exceeded | Config (max_rounds), AuditZone (log circuit break) |
| RoleScheduler | Define and iterate the default role order: Coder -> Reviewer -> Tester -> Integrator | ProcessManager (activate/suspend), ViewportSlicer (isolation) |
| ResultSummarizer | Produce end-of-loop summary | FluidZone, CrystalZone, AuditZone, ProcessManager |

### 2.3 Engine Drive Loop Pseudocode

```python
async def drive(self, intent: str) -> EngineResult:
    # 1. Seed: write initial intent signal
    self._seed_intent(intent)

    round_num = 0
    while True:
        round_num += 1

        # 2. Circuit breaker check
        if self._circuit_breaker.should_break(round_num):
            return self._circuit_breaker.report(round_num)

        # 3. Role scheduling: process each role in order
        for role in self._scheduler.order:
            # 3a. Read unprocessed signals for this role
            signals = self._read_pending_signals(role)

            # 3b. Viewport slice (role-isolated)
            slice = self._slicer.slice(role)

            # 3c. LLM call (via call_llm tool)
            raw_response = await self._call_llm(role, slice)

            # 3d. Parse response into typed signals
            parsed = self._parser.parse(raw_response, role, round_num)

            # 3e. Inject parsed signals into FluidZone
            self._inject_parsed(parsed)

        # 4. Convergence check
        collision = self._kanban.fluid.detect_collision("task_root")
        if not collision.has_collision:
            # 5. Converged: crystal fix + valve write
            self._crystalize_and_write()
            return self._summarizer.summarize(round_num, converged=True)

        # 6. Not converged: next round continues
```

### 2.4 Engine -- Statelessness Principle

The Engine itself holds no mutable state between rounds. All state lives in the StateKanban. The Engine only reads from and writes to the kanban via the existing API. This means:

- A crashed Engine can be restarted from the last kanban snapshot
- The drive loop is idempotent: re-running a round with the same kanban state produces the same result
- The Engine does not bypass ViewportSlicer or ToolRegistry

## 3. CodexAdapter (NEW)

### 3.1 Position in Adapter Layer

CodexAdapter sits alongside AnthropicMessagesAdapter, ClaudeCLIAdapter, and MockLLMAdapter. It implements the same `LLMAdapter` ABC but is specialized for code generation via the OpenAI Codex CLI.

```
LLMAdapter (ABC)
  +-- AnthropicMessagesAdapter   (Messages API, supports tool_use + streaming)
  +-- ClaudeCLIAdapter            (claude -p subprocess, transitional)
  +-- MockLLMAdapter             (deterministic test responses)
  +-- CodexAdapter (NEW)         (codex CLI subprocess, code generation)
```

### 3.2 CodexAdapter Design

```python
class CodexAdapter(LLMAdapter):
    """LLM adapter that executes via the OpenAI Codex CLI."""

    def __init__(self, cli_path: str = "codex", timeout: float = 300.0) -> None:
        self._cli_path = cli_path
        self._timeout = timeout
        self._available: bool | None = None  # lazy availability check

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """
        Execute via `codex` CLI subprocess.

        Input format: prompt extracted from messages + context_files
        Output format: stdout captured as code snippet, wrapped in LLMResponse

        Raises:
            CodexNotAvailableError: Codex CLI not found on PATH
            LLMResponseParseError: Codex returned non-zero exit or timed out
        """
```

### 3.3 CodexAdapter Execution Model

1. **Availability Check**: On first call, check `shutil.which("codex")`. If not found, raise `CodexNotAvailableError`. Cache result.
2. **Input Preparation**: Extract `prompt` from the last user message. Extract `context_files` from message metadata (if present).
3. **Subprocess Execution**: Run `codex` with the prompt via `asyncio.create_subprocess_exec`. Apply timeout.
4. **Output Parsing**: Capture stdout as raw text. Wrap in `LLMResponse.content`.
5. **Graceful Degradation**: If Codex CLI is missing, the Engine should fall back to `call_llm` with the Anthropic adapter, or report to the user. The Engine decides; the adapter just reports unavailability.

### 3.4 CodexAdapter vs LLMAdapter Semantic Differences

| Aspect | LLMAdapter (general) | CodexAdapter (code) |
|--------|----------------------|---------------------|
| Primary output | Structured JSON (intent/veto/artifact) | Code snippet text |
| Tool use | Supports tool_use blocks | No tool_use; output is code |
| Context | Viewport slice (signals + artifacts) | Prompt + context_files |
| Streaming | Supported | Not supported (subprocess) |
| Availability | API key required | CLI must be installed |

The Engine's ResponseParser handles both formats. When using CodexAdapter, the parser treats the entire response content as an artifact (code snippet).

## 4. call_codex Tool (NEW)

### 4.1 Tool Registration

Registered in ToolRegistry with the same pattern as `call_llm`. Peer tool, not replacement.

```python
ToolDef(
    name="call_codex",
    description="Generate code via OpenAI Codex CLI. Input: prompt + context_files. Output: code snippet.",
    param_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Code generation prompt"},
            "context_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file paths for Codex context",
            },
            "output_path": {
                "type": "string",
                "description": "Target file path for generated code",
            },
            "max_tokens": {"type": "integer", "default": 4096},
        },
        "required": ["prompt"],
    },
    required_permissions={"coder", "integrator"},
    timeout_seconds=300.0,
)
```

### 4.2 Permission Model

| Role | call_codex | call_llm |
|------|-----------|---------|
| coder | ALLOWED | ALLOWED |
| integrator | ALLOWED | ALLOWED |
| reviewer | DENIED | ALLOWED |
| tester | DENIED | ALLOWED |
| architect | DENIED | ALLOWED |

Permission denied calls are logged to AuditZone with event type `permission_denied`, including the caller role and tool name. The ToolRegistry raises `PermissionDeniedError` as with any other permission violation.

### 4.3 call_codex Implementation

```python
def create_call_codex_tool(codex_adapter: CodexAdapter) -> Any:
    """Create the call_codex tool bound to a CodexAdapter."""

    async def call_codex(params: dict[str, Any]) -> dict[str, Any]:
        prompt = params.get("prompt", "")
        context_files = params.get("context_files", [])
        output_path = params.get("output_path", "")
        max_tokens = params.get("max_tokens", 4096)

        # Build a single-turn message for Codex
        content = prompt
        if context_files:
            content += "\n\nContext files: " + ", ".join(context_files)

        messages = [LLMMessage(role="user", content=content)]

        response = await codex_adapter.complete(
            messages=messages,
            max_tokens=max_tokens,
        )

        # Codex output is code -- wrap as artifact candidate
        return {
            "success": True,
            "content": response.content,
            "output_path": output_path,
            "finish_reason": response.finish_reason,
        }

    return call_codex
```

## 5. LLM Response Parsing Design

### 5.1 ParsedResponse Structure

```python
class ParsedResponseType(Enum):
    INTENT = "intent"
    VETO = "veto"
    ARTIFACT = "artifact"
    ERROR = "error"

@dataclass(frozen=True)
class ParsedResponse:
    """Result of parsing an LLM raw response into typed signals."""
    response_type: ParsedResponseType
    target_id: str
    payload: dict[str, Any]
    reason: str = ""            # for veto
    artifact_path: str = ""     # for artifact
    artifact_content: str = ""  # for artifact
    artifact_type: str = "code" # for artifact
    parse_success: bool = True
    parse_error: str = ""       # if parse_success is False
```

### 5.2 Parsing Strategy

The ResponseParser handles three input formats:

1. **Structured JSON**: LLM returns `{"type": "intent", "target_id": "...", "payload": {...}}` or `{"type": "veto", ...}` or `{"type": "artifact", ...}`. Parse directly into ParsedResponse.
2. **Code block**: LLM returns a fenced code block (e.g., ```python ... ```). Treat as artifact type.
3. **Unstructured text**: Cannot be parsed. Create an ErrorSignal and inject into FluidZone.

### 5.3 Parsing Algorithm

```python
def parse(self, raw_response: LLMResponse, author_role: str, round_number: int) -> list[ParsedResponse]:
    """
    Parse raw LLM response into zero or more ParsedResponse objects.

    Returns:
        List of parsed responses. On complete parse failure, returns a single
        ParsedResponse with response_type=ERROR.
    """
    content = raw_response.content or ""

    # Strategy 1: Try structured JSON
    parsed = self._try_structured_json(content, author_role, round_number)
    if parsed is not None:
        return parsed

    # Strategy 2: Try code block extraction
    parsed = self._try_code_block(content, author_role, round_number)
    if parsed is not None:
        return parsed

    # Strategy 3: Unstructured -- error signal
    return [ParsedResponse(
        response_type=ParsedResponseType.ERROR,
        target_id="parse_failure",
        payload={"raw_content_preview": content[:200]},
        parse_success=False,
        parse_error="Response is not structured JSON or code block",
    )]
```

### 5.4 Structured JSON Schema

```json
{
    "type": "intent" | "veto" | "artifact",
    "target_id": "string",
    "payload": { },
    "reason": "string (required for veto)",
    "artifact_path": "string (required for artifact)",
    "artifact_content": "string (required for artifact)",
    "artifact_type": "code|config|doc|test (for artifact)"
}
```

The parser also supports a list of such objects in a top-level JSON array.

### 5.5 Code Block Extraction

When structured JSON parsing fails, the parser looks for fenced code blocks:

```regex
```(\w+)?\s*\n([\s\S]*?)\n```
```

If found, the extracted code is treated as an artifact ParsedResponse with:
- `response_type = ARTIFACT`
- `artifact_type` inferred from the language tag (python -> code, json -> config, etc.)
- `target_id` = "codex_output"

### 5.6 Error Handling on Parse Failure

On parse failure:
1. An `ErrorSignal` is created with `author_role="ResponseParser"`, `target_id="parse_failure"`, `error_code="SK_EN_001"`, `error_detail` containing a truncated preview of the raw content.
2. The `ErrorSignal` is written to `FluidZone`.
3. The Engine's drive loop picks it up in the next round, allowing the Coder to see the parse error and adjust its output.
4. The system does **not** crash on parse failure (NFR-R05).

## 6. Collision Convergence Strategy Design

### 6.1 Convergence Flow in Engine Context

In Round 1, `StateKanban.run_convergence()` was a synchronous loop. In Round 2, the Engine integrates convergence into the drive loop, adding LLM calls between collision detection rounds.

```
Engine Drive Loop:
  Round N:
    [1] Coder reads viewport -> LLM call -> IntentSignal(target=A, round=N)
    [2] Reviewer reads viewport -> LLM call -> VetoSignal(target=A, round=N) or IntentSignal(approve)
    [3] ConvergenceDetector.check(target=A):
        - If no veto signals for target A in round N: CONVERGED
        - If veto exists: NOT CONVERGED, continue to round N+1
    [4] Tester: validates (optional, runs tests)
    [5] Integrator: integrates (if converged)

  After convergence:
    [6] CrystalZone.append(artifact)
    [7] OutputValve.validate_and_write(artifact)
```

### 6.2 Convergence Conditions

A target_id is considered **converged** when ALL of the following hold:

1. There exists at least one `IntentSignal` for the target_id in the latest round.
2. There are NO `VetoSignal` entries for the target_id in the latest round.
3. Any prior `VetoSignal` entries are from rounds before the latest round (i.e., they have been "resolved" by a newer intent).

This replaces the simpler `CollisionResult.is_resolved` check from Round 1, adding round-awareness.

### 6.3 ConvergenceDetector Implementation Outline

```python
class ConvergenceDetector:
    """Determines whether signals for a target have converged."""

    def __init__(self, kanban: StateKanban) -> None:
        self._kanban = kanban

    def check(self, target_id: str, current_round: int) -> ConvergenceCheckResult:
        """
        Check convergence for a target at the given round.

        A target is converged if:
        - There are IntentSignals in current_round for this target
        - There are no VetoSignals in current_round for this target
        """
        current_signals = self._kanban.fluid.read_signals(target_id=target_id)
        round_signals = [s for s in current_signals if s.round_number == current_round]

        intent_in_round = any(s.signal_type == SignalType.INTENT for s in round_signals)
        veto_in_round = any(s.signal_type == SignalType.VETO for s in round_signals)

        converged = intent_in_round and not veto_in_round

        return ConvergenceCheckResult(
            target_id=target_id,
            round_number=current_round,
            converged=converged,
            intent_count=sum(1 for s in round_signals if s.signal_type == SignalType.INTENT),
            veto_count=sum(1 for s in round_signals if s.signal_type == SignalType.VETO),
        )
```

### 6.4 Post-Convergence Pipeline

Once convergence is detected:

1. **CrystalZone Fixation**: The artifact associated with the converged intent is appended to CrystalZone.
2. **OutputValve Validation**: The artifact is submitted to `OutputValve.validate_and_write()`.
3. **Write or Rework**:
   - If valve passes: file is written atomically, audit logged, signal published.
   - If valve fails: ErrorSignal injected to FluidZone, Engine continues to next round (Coder sees error and reworks).
4. **Result Summary**: After all targets converge or circuit breaks, the ResultSummarizer produces the final EngineResult.

## 7. Role Scheduling Order Design

### 7.1 Default Order

The default role scheduling order is:

```
Coder -> Reviewer -> Tester -> Integrator
```

(Architect is not in the default loop; it is activated on-demand for architecture questions.)

### 7.2 Scheduling Semantics

- **Sequential within a round**: Each role completes before the next role starts.
- **Viewport isolation**: When Reviewer starts, it sees Coder's output from this round (via ViewportSlicer). When Tester starts, it sees both Coder's and Reviewer's outputs from this round. When Integrator starts, it sees all preceding outputs.
- **No parallel scheduling**: The drive loop is synchronous, one round at a time, one role at a time (OOS-12).

### 7.3 RoleScheduler Implementation Outline

```python
class RoleScheduler:
    """Defines and iterates the role processing order."""

    DEFAULT_ORDER: list[str] = ["coder", "reviewer", "tester", "integrator"]

    def __init__(self, order: list[str] | None = None) -> None:
        self._order = order or list(self.DEFAULT_ORDER)

    @property
    def order(self) -> list[str]:
        return list(self._order)

    def iter_round(self) -> Iterator[str]:
        """Yield role names in scheduling order for one round."""
        for role in self._order:
            yield role
```

### 7.4 Viewport Isolation Rules

| Role | Can See | Cannot See |
|------|---------|------------|
| Coder | Intent signals, Error signals (including valve failures), CrystalZone artifacts from previous rounds | Reviewer's internal signals, Tester's internal signals |
| Reviewer | Intent signals, Veto signals (its own), Error signals, CrystalZone artifacts | Coder's internal LLM call details, Tester's internal signals |
| Tester | Intent signals, Error signals, CrystalZone code+test artifacts | Reviewer's veto reasons from prior rounds (only sees intent/veto in current round per ViewportSpec) |
| Integrator | Intent signals, Veto signals, Error signals, All CrystalZone artifacts | Other roles' internal LLM call details |

This is enforced by the existing ViewportSlicer's `visible_signal_types` and `visible_target_patterns` in each role's ViewportSpec. No changes to ViewportSlicer are needed; the Engine simply uses the existing specs.

## 8. Data Flow Diagrams

### 8.1 Engine Drive Loop (Happy Path)

```
User --[CLI: run --intent "xxx" --adapter mock]--> Engine
  |
  +-- Engine._seed_intent("xxx")
  |     |
  |     +-- IntentSignal(target="task_root", round=0) --> FluidZone
  |
  +-- Round 1:
  |     |
  |     +-- Coder:
  |     |     ViewportSlicer.slice("coder") -> ViewportSlice
  |     |     call_llm / call_codex -> LLMResponse
  |     |     ResponseParser.parse() -> ParsedResponse(type=ARTIFACT)
  |     |     IntentSignal(target="artifact_1", round=1) -> FluidZone
  |     |
  |     +-- Reviewer:
  |     |     ViewportSlicer.slice("reviewer") -> ViewportSlice (sees Coder's intent)
  |     |     call_llm -> LLMResponse
  |     |     ResponseParser.parse() -> ParsedResponse(type=INTENT, approve)
  |     |     IntentSignal(target="artifact_1", round=1) -> FluidZone
  |     |
  |     +-- ConvergenceDetector.check("artifact_1", round=1):
  |     |     intent=True, veto=False -> CONVERGED
  |     |
  |     +-- CrystalZone.append(artifact_1)
  |     +-- OutputValve.validate_and_write(artifact_1) -> ValveResult(success=True)
  |
  +-- ResultSummarizer.summarize(rounds=1, converged=True)
  +-- CLI outputs summary
```

### 8.2 Collision and Convergence Flow (Engine-Driven)

```
Round 1:
  Coder: IntentSignal(target="artifact_1", round=1, payload={code})
  Reviewer: VetoSignal(target="artifact_1", round=1, reason="missing error handling")

  ConvergenceDetector.check("artifact_1", round=1):
    intent=True, veto=True -> NOT CONVERGED

Round 2:
  Coder: [sees VetoSignal from round 1 via viewport]
         IntentSignal(target="artifact_1", round=2, payload={revised_code})
  Reviewer: [sees revised IntentSignal from round 2]
            IntentSignal(target="artifact_1", round=2, approve)

  ConvergenceDetector.check("artifact_1", round=2):
    intent=True, veto=False -> CONVERGED

  CrystalZone.append(artifact_1)
  OutputValve.validate_and_write(artifact_1) -> success
```

### 8.3 Circuit Breaker Flow

```
Round 1..10:
  Coder produces intent, Reviewer vetoes, loop continues...

Round 10:
  ConvergenceDetector still sees veto.
  CircuitBreaker.should_break(10) -> True (max_rounds=10)

  Engine terminates loop.
  AuditZone.log("circuit_break", round=10)
  ResultSummarizer.summarize(rounds=10, converged=False, forced_terminate=True)
  CLI outputs: "Circuit break: max rounds (10) exceeded. Manual intervention required."
```

### 8.4 Validation Failure and Rework Flow

```
Convergence achieved -> CrystalZone.append(artifact)
  |
  v
OutputValve.validate_and_write(artifact):
  SyntaxValidator -> FAIL
  |
  v
ErrorSignal(target=artifact.path, error_code="SK_OV_001", error_detail="Python syntax error...")
  -> FluidZone

Round N+1:
  Coder: [sees ErrorSignal via viewport]
         IntentSignal(target=artifact.path, round=N+1, payload={fixed_code})
  Reviewer: IntentSignal(approve)
  ConvergenceDetector -> CONVERGED
  OutputValve.validate_and_write(fixed_artifact) -> SUCCESS
```

### 8.5 Codex Code Generation Flow

```
Coder:
  ViewportSlicer.slice("coder") -> ViewportSlice
  call_tool("call_codex", {
      "prompt": "Implement a REST API endpoint for user login",
      "context_files": ["src/auth/models.py", "src/auth/schemas.py"],
      "output_path": "src/auth/login.py",
  })
  |
  v
ToolRegistry.dispatch("call_codex", "coder", params):
  Permission check: "coder" in {"coder", "integrator"} -> PASS
  |
  v
CodexAdapter.complete(messages=[{role: "user", content: prompt + context}])
  -> LLMResponse(content=code_snippet)
  |
  v
call_codex tool returns:
  {"success": True, "content": code_snippet, "output_path": "src/auth/login.py"}
  |
  v
ResponseParser.parse() -> ParsedResponse(type=ARTIFACT)
  -> IntentSignal -> FluidZone
  -> (after convergence) CrystalZone + OutputValve
```

### 8.6 Codex Permission Denied Flow

```
Reviewer:
  call_tool("call_codex", {...})
  |
  v
ToolRegistry.dispatch("call_codex", "reviewer", params):
  Permission check: "reviewer" NOT in {"coder", "integrator"} -> FAIL
  AuditZone.log("permission_denied", tool="call_codex", caller="reviewer")
  |
  v
Raises PermissionDeniedError
  |
  v
Reviewer catches error, writes ErrorSignal to FluidZone:
  ErrorSignal(target="call_codex", error_code="SK_TR_001", error_detail="Permission denied")
```

## 9. Error Handling Strategy (Updated)

### 9.1 Updated Error Hierarchy

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
  |     +-- LLMResponseParseError
  |     +-- LLMAuthError
  +-- CodexAdapterError (NEW)
  |     +-- CodexNotAvailableError (NEW)
  |     +-- CodexExecutionError (NEW)
  +-- EngineError (NEW)
  |     +-- CircuitBreakerError (NEW)
  |     +-- SignalRoutingError (NEW)
  |     +-- ParseRecoveryError (NEW)
  +-- SnapshotError
        +-- SnapshotIntegrityError
        +-- SnapshotWriteError
```

### 9.2 New Error Propagation Rules

| Error Type | Source | Propagation | Recovery |
|------------|--------|-------------|----------|
| CodexNotAvailableError | CodexAdapter | Engine catches, falls back to call_llm or reports to user | Graceful degradation |
| CodexExecutionError | CodexAdapter | Inject ErrorSignal into FluidZone | Coder retries with call_llm |
| CircuitBreakerError | Engine | Raise to CLI, halt task | Manual intervention |
| SignalRoutingError | Engine | Log to AuditZone, inject ErrorSignal into FluidZone | Next round retry |
| ParseRecoveryError | ResponseParser | After N consecutive parse failures, raise to Engine | Engine circuit-breaks |
| LLMResponseParseError | ResponseParser | Inject ErrorSignal into FluidZone | Coder retries in next round |

### 9.3 Error Handling Principles (Updated from Round 1)

1. **Fail-loud at boundaries**: Errors at system boundaries (LLM call, Codex CLI, file I/O, CLI) are raised explicitly.
2. **Signal-back on process errors**: Errors within a process loop are converted to signals in FluidZone, not propagated as exceptions across modules.
3. **Never crash the kernel**: StateKanban core, MessageBus, ProcessManager, and Engine must never raise unhandled exceptions; they catch, log, and degrade gracefully.
4. **Audit everything**: Every error that results in a state change is logged to AuditZone.
5. **Recoverable by default**: All transient errors (LLM timeout, tool timeout, parse failure, Codex unavailable) are recoverable via signal re-injection; only data integrity errors and circuit breaks are fatal.
6. **Circuit break is final (NEW)**: Once the circuit breaker fires, the Engine stops the drive loop and reports to the user. No automatic retry after circuit break.

## 10. Package Structure (Updated)

```
statekanban/
  __init__.py
  cli/                    # CLI layer (click)
    __init__.py
    main.py               # click group + commands (updated: --adapter, --max-rounds, --verbose)
  core/                   # Kernel -- zero I/O
    __init__.py
    kanban.py             # StateKanban, FluidZone, CrystalZone, AuditZone
    viewport.py           # ViewportSlicer, ViewportSpec
    message_bus.py        # MessageBus (pub/sub, sync, async)
    process.py            # ProcessManager, ProcessState
    valve.py              # OutputValve, validation chain
    registry.py           # ToolRegistry, ToolDef
    errors.py             # Error hierarchy (updated with Engine + Codex errors)
  adapters/               # LLM adapters
    __init__.py
    base.py               # LLMAdapter ABC
    anthropic_adapter.py  # Anthropic Messages API
    cli_adapter.py        # Claude CLI subprocess
    mock_adapter.py       # MockLLM for testing (updated: structured JSON support)
    codex_adapter.py      # CodexAdapter via Codex CLI (NEW)
  engine/                 # Engine module (NEW)
    __init__.py
    engine.py             # Engine, DriveLoop
    parser.py             # ResponseParser, ParsedResponse
    convergence.py         # ConvergenceDetector, ConvergenceCheckResult
    scheduler.py           # RoleScheduler
    breaker.py             # CircuitBreaker
    summary.py             # ResultSummarizer, EngineResult
    router.py              # SignalRouter
    errors.py              # Engine-specific errors
  roles/                  # Built-in process roles
    __init__.py
    base.py               # ProcessRole ABC
    coder.py              # (updated: can call call_codex)
    reviewer.py
    tester.py
    integrator.py         # (updated: can call call_codex)
    architect.py
  tools/                  # Built-in tool implementations
    __init__.py
    write_file.py
    read_file.py
    run_shell.py
    call_llm.py
    call_codex.py          # (NEW)
    search_code.py
  snapshot.py             # Snapshot serialization/deserialization
  config.py               # Global configuration dataclass (updated: codex settings)
```

## 11. MockLLM Adapter Enhancement

### 11.1 Structured JSON Support

The MockLLM adapter is enhanced to return structured JSON responses that the ResponseParser can parse, enabling end-to-end drive loop testing without real API calls.

```python
class MockLLMAdapter(LLMAdapter):
    """Enhanced deterministic mock for drive loop testing."""

    def __init__(self, responses: dict[str, list[LLMResponse]] | None = None) -> None:
        self._responses = responses or {}
        self._call_counts: dict[str, int] = {}
        self._structured_mode: bool = False

    def set_structured_response(
        self,
        role: str,
        response_type: ParsedResponseType,
        target_id: str = "task_root",
        payload: dict[str, Any] | None = None,
        reason: str = "",
        artifact_path: str = "",
        artifact_content: str = "",
    ) -> None:
        """Configure a structured JSON response for a role.

        When structured_mode is enabled, complete() returns LLMResponse
        with content containing a JSON string that ResponseParser can parse.
        """
```

### 11.2 Mock Response Patterns for Testing

| Test Scenario | Coder Response | Reviewer Response | Expected Outcome |
|---------------|---------------|-------------------|------------------|
| Happy path | `{"type":"artifact",...}` | `{"type":"intent","target_id":"artifact_1"}` | Converged in 1 round |
| Veto then fix | `{"type":"artifact",...}` (round 1) then revised (round 2) | `{"type":"veto","reason":"..."}` (round 1) then `{"type":"intent"}` (round 2) | Converged in 2 rounds |
| Circuit break | `{"type":"artifact",...}` | `{"type":"veto","reason":"..."}` every round | Circuit break at round 10 |
| Parse failure | Unstructured text | -- | ErrorSignal injected, retry |
| Valve failure | `{"type":"artifact",...}` | `{"type":"intent"}` | Valve fails, ErrorSignal, Coder reworks |

## 12. CLI Integration Design

### 12.1 Updated CLI Commands

```python
@cli.command()
@click.option("--intent", required=True, help="Task intent description")
@click.option("--config", "config_path", default=None, help="Path to config file")
@click.option("--adapter", type=click.Choice(["mock", "anthropic", "cli", "codex"]),
              default="mock", help="LLM adapter to use")
@click.option("--max-rounds", default=10, type=int, help="Maximum drive loop rounds")
@click.option("--verbose", is_flag=True, help="Output per-round details")
def run(intent: str, config_path: str | None, adapter: str,
        max_rounds: int, verbose: bool) -> None:
    """Start a development task with the drive loop."""
```

### 12.2 Adapter Selection Logic

```python
def _create_llm_adapter(config: Config) -> LLMAdapter:
    if config.llm_adapter == "anthropic":
        return AnthropicMessagesAdapter(model=config.llm_model)
    elif config.llm_adapter == "cli":
        return ClaudeCLIAdapter()
    elif config.llm_adapter == "codex":
        return CodexAdapter(timeout=config.codex_timeout)
    else:
        return MockLLMAdapter()
```

### 12.3 Verbose Output Format

When `--verbose` is set, the Engine prints per-round information to stderr:

```
[Round 1] Coder: viewport=12 signals, 3 artifacts; LLM response=247 tokens
[Round 1] Reviewer: viewport=15 signals, 4 artifacts; LLM response=183 tokens
[Round 1] Convergence: target=artifact_1, intent=1, veto=0 -> CONVERGED
[Output] Valve: syntax=PASS, type=PASS, test=PASS; written to src/auth/login.py
[Summary] Rounds: 1 | Converged: True | Artifacts: 1 | Files: src/auth/login.py
```

## 13. Security Design (Updated)

### 13.1 New Threat Vectors

| Threat | Vector | Mitigation |
|--------|--------|------------|
| Codex prompt injection | Malicious context_files or prompt | OutputValve validates all Codex output before write; ViewportSlicer sanitizes |
| Codex write bypass | Codex output written directly | Codex output MUST go through OutputValve; no shortcut path |
| Unauthorized Codex call | Non-coder role tries call_codex | ToolRegistry enforces permission; rejected + audited |
| Codex CLI path injection | cli_path points to malicious binary | CodexAdapter validates CLI existence; Engine does not accept arbitrary paths from LLM |
| Resource exhaustion via Codex | Infinite Codex calls | Circuit breaker limits total rounds; per-call timeout on CodexAdapter |

### 13.2 Updated Security Invariants

All Round 1 invariants hold, plus:

7. **Codex output valve mandatory**: All code generated by Codex must pass through OutputValve before filesystem write. The call_codex tool's return value is an intermediate result, not a write operation.
8. **Codex permission enforcement**: The `call_codex` tool uses the same `ToolRegistry.dispatch()` permission check as all other tools. There is no backdoor.
9. **Adapter isolation**: TheEngine interacts with adapters only through the `LLMAdapter` ABC. Adapter-specific behavior (Codex CLI, Anthropic API) is encapsulated within adapter implementations. The Engine has no adapter-specific code paths.

## 14. Initialization Order (Updated)

The system must be initialized in the following order:

1. `StateKanban()` -- no dependencies
2. `MessageBus(kanban)` -- depends on StateKanban (audit)
3. `ToolRegistry(kanban)` -- depends on StateKanban (audit)
4. `OutputValve(validators, kanban=kanban)` -- depends on StateKanban (error injection)
5. `ViewportSlicer(kanban, specs)` -- depends on StateKanban (read)
6. `ProcessManager(kanban, bus)` -- depends on StateKanban + MessageBus
7. `LLMAdapter` (selected via --adapter) -- no internal dependencies
8. `CodexAdapter` (if selected) -- no internal dependencies
9. **Engine sub-components (NEW):**
   - `ResponseParser()` -- no dependencies
   - `ConvergenceDetector(kanban)` -- depends on StateKanban
   - `RoleScheduler()` -- no dependencies
   - `CircuitBreaker(max_rounds)` -- depends on Config
   - `ResultSummarizer(kanban, pm)` -- depends on StateKanban + ProcessManager
   - `SignalRouter(pm)` -- depends on ProcessManager
10. `Engine(...)` -- depends on all above
11. Process roles -- depend on ViewportSlicer, MessageBus, ToolRegistry
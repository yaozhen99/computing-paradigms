"""Engine: top-level orchestrator that drives the development loop.

Composes all sub-components and executes the drive loop until
convergence or circuit break.

The Engine holds no mutable state between rounds. All state lives in
the StateKanban. The Engine only reads from and writes to the kanban
via the existing API.

REQ-004: Engine routes LLM calls through ToolRegistry.dispatch().
REQ-005a: Engine uses call_llm tool via ToolRegistry.
REQ-006: ValveReworkLoopError on consecutive valve failures (SK_EN_004).
REQ-008: Null bytes validation enforced via call_llm tool.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    ErrorSignal,
    IntentSignal,
    LLMMessage,
    LLMResponse,
    Signal,
    SignalType,
    StateKanban,
    VetoSignal,
    compute_checksum,
    make_signal_id,
    now_utc,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer, ViewportSlice
from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.engine.convergence import ConvergenceDetector
from statekanban.engine.result import EngineResult, ResultSummarizer
from statekanban.engine.response_parser import (
    ParsedResponse,
    ParsedResponseType,
    ResponseParser,
)
from statekanban.engine.router import SignalRouter
from statekanban.engine.scheduler import RoleScheduler
from statekanban.adapters.base import LLMAdapter
from statekanban.config import Config
from statekanban.core.errors import InvalidViewportSpecError, StateKanbanError


class Engine:
    """Top-level orchestrator that drives the development loop.

    Composes all sub-components and executes the drive loop until
    convergence or circuit break.

    REQ-004: LLM calls are routed through ToolRegistry.dispatch("call_llm", ...).
    REQ-005a: call_llm tool is used as the LLM invocation mechanism.
    """

    def __init__(
        self,
        kanban: StateKanban,
        bus: MessageBus,
        registry: ToolRegistry,
        valve: OutputValve,
        slicer: ViewportSlicer,
        pm: ProcessManager,
        adapter: LLMAdapter,
        config: Config,
    ) -> None:
        """
        Args:
            kanban: Single source of truth.
            bus: Inter-process communication.
            registry: Tool dispatch with permission.
            valve: Output validation guard.
            slicer: Viewport context engineering.
            pm: Process lifecycle management.
            adapter: LLM backend (selected via CLI --adapter).
            config: System configuration.

        REQ-005: registry must have "call_llm" tool registered
                 before drive() is called.
        """
        self._kanban = kanban
        self._bus = bus
        self._registry = registry
        self._valve = valve
        self._slicer = slicer
        self._pm = pm
        self._adapter = adapter
        self._config = config
        self._project_root = config.resolve_path("")  # REQ-503: resolved project root
        self._parser = ResponseParser(kanban=kanban)
        self._convergence = ConvergenceDetector(kanban)
        self._scheduler = RoleScheduler()
        self._breaker = CircuitBreaker(max_rounds=config.convergence_max_rounds)
        self._summarizer = ResultSummarizer(kanban, pm)
        self._router = SignalRouter(pm)
        self._verbose = False

        # REQ-006: Valve rework loop detection
        self._consecutive_valve_failures: int = 0
        self._max_consecutive_valve_failures: int = 3

        # REQ-605: Consecutive external exception tracking
        self._consecutive_error_rounds: int = 0
        self._max_consecutive_error_rounds: int = 3

        # REQ-004: Whether to route through ToolRegistry (default True)
        self._use_registry_for_llm: bool = True

    def set_verbose(self, verbose: bool) -> None:
        """Enable per-round verbose output to stderr."""
        self._verbose = verbose

    def set_use_registry_for_llm(self, use_registry: bool) -> None:
        """Configure whether Engine routes LLM calls through ToolRegistry.

        When True (default), _call_llm_for_role uses registry.dispatch().
        When False, falls back to direct adapter.complete() call.

        Args:
            use_registry: Whether to route through ToolRegistry.
        """
        self._use_registry_for_llm = use_registry

    async def drive(self, intent: str) -> EngineResult:
        """Execute the full drive loop for a given intent.

        1. Seeds the initial intent signal into FluidZone.
        2. Iterates the drive loop: role scheduling, LLM calls, parsing,
           signal injection, convergence detection.
        3. On convergence: crystal fixation + valve write.
        4. On circuit break: report failure.
        5. Returns EngineResult summary.

        Args:
            intent: The user's task intent string.

        Returns:
            EngineResult with convergence status, round count, and file list.

        Raises:
            CircuitBreakerError: Max rounds exceeded (propagated to CLI).
            ValveReworkLoopError: Consecutive valve failures (SK_EN_004).
        """
        start_time = datetime.datetime.now(tz=datetime.timezone.utc)

        # 1. Seed the initial intent signal
        await self._seed_intent(intent)

        round_num = 0
        while True:
            round_num += 1

            # 2. Circuit breaker check
            if self._breaker.should_break(round_num):
                self._log_circuit_break(round_num)
                return self._breaker.report(round_num)

            # 3. Role scheduling: process each role in order
            for role in self._scheduler.iter_round():
                await self._process_role(role, round_num)

            # REQ-605: Track consecutive rounds with external exceptions
            error_signals = self._kanban.fluid.read_signals(signal_type=SignalType.ERROR)
            has_external_error = any(
                s.error_code == "SK_EN_006" and s.round_number == round_num
                for s in error_signals
            )
            if has_external_error:
                self._consecutive_error_rounds += 1
                if self._consecutive_error_rounds >= self._max_consecutive_error_rounds:
                    from statekanban.core.errors import EngineExternalError

                    raise EngineExternalError(
                        f"Consecutive external exceptions ({self._consecutive_error_rounds}): "
                        f"abnormal termination"
                    )
            else:
                self._consecutive_error_rounds = 0

            # 4. Convergence check for all pending targets
            all_results = self._convergence.check_all_pending(round_num)
            all_converged = (
                all(r.converged for r in all_results.values()) if all_results else False
            )

            if all_converged:
                # 5. Converged: crystal fix + valve write
                await self._crystalize_and_write()
                return self._summarizer.summarize(
                    total_rounds=round_num,
                    converged=True,
                    start_time=start_time,
                )

            # 6. Not converged: next round continues
            if self._verbose:
                not_converged = [
                    f"{tid} (intent={r.intent_count}, veto={r.veto_count})"
                    for tid, r in all_results.items()
                    if not r.converged
                ]
                print(
                    f"[Round {round_num}] Not converged: {', '.join(not_converged)}",
                    file=sys.stderr,
                )

    async def _seed_intent(self, intent: str) -> None:
        """Write the initial IntentSignal into FluidZone (round 0)."""
        intent_signal = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": intent},
            timestamp=now_utc(),
            round_number=0,
        )
        self._kanban.fluid.write_signal(intent_signal)
        self._kanban.audit.log(
            event_type="intent_seeded",
            actor="Engine",
            action="seed_intent",
            details={"target_id": "task_root", "intent_length": len(intent)},
        )

    async def _process_role(self, role: str, round_number: int) -> None:
        """Process a single role within the drive loop.

        Steps:
        1. Read viewport slice for the role.
        2. Call LLM via ToolRegistry (REQ-004).
        3. Parse response into ParsedResponse objects.
        4. Inject parsed signals into FluidZone.

        Args:
            role: The role to process.
            round_number: Current round number (1-based).
        """
        try:
            # 3a. Viewport slice (role-isolated)
            try:
                slice_data = self._slicer.slice(role)
            except InvalidViewportSpecError:
                # Role has no viewport spec configured -- skip it
                return

            if self._verbose:
                print(
                    f"[Round {round_number}] {role.capitalize()}: "
                    f"viewport={len(slice_data.signals)} signals, "
                    f"{len(slice_data.artifacts)} artifacts",
                    file=sys.stderr,
                )

            # 3b. LLM call via ToolRegistry (REQ-004)
            raw_response = await self._call_llm_for_role(role, slice_data)

            if self._verbose:
                token_count = len((raw_response.content or "")) // 4
                print(
                    f"[Round {round_number}] {role.capitalize()}: "
                    f"LLM response ~{token_count} tokens",
                    file=sys.stderr,
                )

            # REQ-605: If LLM returned an error response, inject SK_EN_006
            # ErrorSignal directly instead of relying on ResponseParser.
            if raw_response.finish_reason in ("error", "degraded"):
                error_signal = ErrorSignal(
                    signal_id=make_signal_id(),
                    author_role="system",
                    target_id=role,
                    payload={
                        "error": raw_response.content or "LLM error",
                        "source": role,
                    },
                    timestamp=now_utc(),
                    round_number=round_number,
                    error_code="SK_EN_006",
                    error_detail=f"External exception in role {role}: "
                    f"{raw_response.content}",
                )
                self._kanban.fluid.write_signal(error_signal)
                return

            # 3c. Parse response into typed signals
            parsed_list = self._parser.parse(raw_response, role, round_number)

            # 3d. Inject parsed signals into FluidZone
            for parsed in parsed_list:
                self._inject_parsed(parsed, role, round_number)

        except StateKanbanError:
            # Internal errors (config, viewport, etc.) should propagate up
            raise
        except Exception as exc:
            # REQ-605: External exception -> internal ErrorSignal (SK_EN_006)
            # Only catch non-internal exceptions (LLM failures, tool errors, etc.)
            error_signal = ErrorSignal(
                signal_id=make_signal_id(),
                author_role="system",
                target_id=role,
                payload={"error": str(exc), "source": role},
                timestamp=now_utc(),
                round_number=round_number,
                error_code="SK_EN_006",
                error_detail=f"External exception in role {role}: {exc}",
            )
            try:
                self._kanban.fluid.write_signal(error_signal)
            except Exception:
                pass

    # ─── REQ-005: Extracted helper ─────────────────────────────

    def _build_context(self, role: str, slice_data: ViewportSlice) -> str:
        """Build context string from viewport slice for a role.

        Extracted from _call_llm_for_role for testability.

        Args:
            role: Requesting role (e.g., "coder", "reviewer").
            slice_data: ViewportSlice with signals and artifacts.

        Returns:
            Formatted context string for LLM consumption.
        """
        context_parts: list[str] = []
        context_parts.append(f"Role: {role}")
        context_parts.append(f"\nSignals ({len(slice_data.signals)}):")
        for sig in slice_data.signals:
            context_parts.append(
                f"  - [{sig.signal_type.value}] {sig.author_role} -> {sig.target_id}: "
                f"{str(sig.payload)[:200]}"
            )
        if slice_data.artifacts:
            context_parts.append(f"\nArtifacts ({len(slice_data.artifacts)}):")
            for art in slice_data.artifacts:
                context_parts.append(f"  - [{art.artifact_type.value}] {art.path}")
        return "\n".join(context_parts)

    # ─── REQ-005: Refactored to use Registry ───────────────────

    async def _call_llm_for_role(
        self, role: str, slice_data: ViewportSlice
    ) -> LLMResponse:
        """Invoke LLM for a role via ToolRegistry.dispatch("call_llm", ...).

        REQ-004 change: Routes through self._registry.dispatch("call_llm", ...)
        for audit logging, permission control, and timeout handling.

        Falls back to direct adapter.complete() if _use_registry_for_llm is False.

        Args:
            role: The role requesting LLM assistance.
            slice_data: Current viewport slice for this role.

        Returns:
            LLMResponse from the LLM call. On dispatch failure, returns
            an error-shaped LLMResponse with finish_reason="error".
        """
        context_text = self._build_context(role, slice_data)

        if not self._use_registry_for_llm:
            # Fallback: direct adapter call (for backward compatibility)
            llm_messages = [LLMMessage(role="user", content=context_text)]
            response = await self._adapter.complete(
                messages=llm_messages,
                max_tokens=self._config.llm_max_tokens,
                temperature=self._config.llm_temperature,
            )
            return response

        # REQ-004: Route through ToolRegistry
        messages = [{"role": "user", "content": context_text}]

        try:
            tool_result = await self._registry.dispatch(
                tool_name="call_llm",
                caller_role=role,
                params={
                    "messages": messages,
                    "max_tokens": self._config.llm_max_tokens,
                    "temperature": self._config.llm_temperature,
                },
            )

            if not tool_result.success:
                # Dispatch failed -- construct a fallback LLMResponse
                return LLMResponse(
                    content=json.dumps(
                        {
                            "type": "error",
                            "target_id": role,
                            "payload": {"error": tool_result.error},
                        }
                    ),
                    finish_reason="error",
                )

            # Extract LLMResponse from dispatch output
            output = tool_result.output
            # call_llm tool returns {"success": True, "output": {"content": ..., "finish_reason": ...}}
            # ToolRegistry.dispatch() wraps the entire return as tool_result.output,
            # so we need to unwrap the nested "output" key first.
            if (
                isinstance(output, dict)
                and "output" in output
                and isinstance(output["output"], dict)
            ):
                inner = output["output"]
                return LLMResponse(
                    content=inner.get("content", ""),
                    finish_reason=inner.get("finish_reason", "end_turn"),
                )
            if isinstance(output, dict) and "content" in output:
                return LLMResponse(
                    content=output["content"],
                    finish_reason=output.get("finish_reason", "end_turn"),
                )

            # Fallback: wrap output as content string
            return LLMResponse(
                content=json.dumps(output) if isinstance(output, dict) else str(output),
                finish_reason="end_turn",
            )

        except Exception as exc:
            # Dispatch exception -- construct error LLMResponse
            return LLMResponse(
                content=json.dumps(
                    {
                        "type": "error",
                        "target_id": role,
                        "payload": {"error": str(exc)},
                    }
                ),
                finish_reason="error",
            )

    def _inject_parsed(
        self, parsed: ParsedResponse, author_role: str, round_number: int
    ) -> None:
        """Inject a parsed response into FluidZone as a typed Signal.

        - ParsedResponseType.INTENT -> IntentSignal
        - ParsedResponseType.VETO -> VetoSignal
        - ParsedResponseType.ARTIFACT -> IntentSignal (artifact approval pending)
        - ParsedResponseType.ERROR -> ErrorSignal

        Args:
            parsed: The parsed response to inject.
            author_role: The role that produced this response.
            round_number: Current round number.
        """
        if parsed.response_type == ParsedResponseType.INTENT:
            signal = IntentSignal(
                signal_id=make_signal_id(),
                author_role=author_role,
                target_id=parsed.target_id,
                payload=parsed.payload,
                timestamp=now_utc(),
                round_number=round_number,
            )
        elif parsed.response_type == ParsedResponseType.VETO:
            signal = VetoSignal(
                signal_id=make_signal_id(),
                author_role=author_role,
                target_id=parsed.target_id,
                payload=parsed.payload,
                timestamp=now_utc(),
                round_number=round_number,
                reason=parsed.reason,
            )
        elif parsed.response_type == ParsedResponseType.ARTIFACT:
            # Artifact is injected as IntentSignal (approval pending)
            signal = IntentSignal(
                signal_id=make_signal_id(),
                author_role=author_role,
                target_id=parsed.target_id,
                payload={
                    **parsed.payload,
                    "artifact_path": parsed.artifact_path,
                    "artifact_content": parsed.artifact_content,
                    "artifact_type": parsed.artifact_type,
                },
                timestamp=now_utc(),
                round_number=round_number,
            )
        elif parsed.response_type == ParsedResponseType.ERROR:
            signal = ErrorSignal(
                signal_id=make_signal_id(),
                author_role=author_role,
                target_id=parsed.target_id,
                payload=parsed.payload,
                timestamp=now_utc(),
                round_number=round_number,
                error_code="SK_EN_003",
                error_detail=parsed.parse_error,
            )
        else:
            # Unknown type -- inject as error
            signal = ErrorSignal(
                signal_id=make_signal_id(),
                author_role=author_role,
                target_id=parsed.target_id,
                payload=parsed.payload,
                timestamp=now_utc(),
                round_number=round_number,
                error_code="SK_EN_003",
                error_detail=f"Unknown parsed response type: {parsed.response_type}",
            )
            return

        self._kanban.fluid.write_signal(signal)

    # ─── REQ-006: Valve rework loop detection ─────────────────

    async def _crystalize_and_write(self) -> None:
        """After convergence: fixate artifact into CrystalZone and submit to OutputValve.

        Steps:
        1. Extract the artifact content from the converged intent signal payload.
        2. Create an Artifact instance.
        3. Append to CrystalZone.
        4. Submit to OutputValve.validate_and_write() (async).
        5. If valve fails, inject ErrorSignal into FluidZone.
        6. REQ-006: Track consecutive valve failures and raise
           ValveReworkLoopError if threshold is exceeded.
        """
        # REQ-503: Ensure project_root directory exists before first write
        if self._project_root and not os.path.exists(self._project_root):
            os.makedirs(self._project_root, exist_ok=True)

        # Read all intent signals and look for artifact payloads
        intent_signals = self._kanban.fluid.read_signals(signal_type=SignalType.INTENT)
        for sig in intent_signals:
            artifact_content = sig.payload.get("artifact_content", "")
            if not artifact_content:
                continue

            artifact_path = sig.payload.get(
                "artifact_path", f"output_{sig.target_id}.py"
            )
            artifact_type_str = sig.payload.get("artifact_type", "code")

            try:
                artifact_type = ArtifactType(artifact_type_str)
            except ValueError:
                artifact_type = ArtifactType.CODE

            artifact = Artifact(
                seq_no=0,  # Auto-assigned
                artifact_type=artifact_type,
                path=artifact_path,
                content=artifact_content,
                checksum=compute_checksum(artifact_content),
                author_role=sig.author_role,
                created_at=now_utc(),
            )

            # Append to CrystalZone
            seq_no = self._kanban.crystal.append(artifact)

            # Submit to OutputValve (async)
            valve_result = await self._valve.validate_and_write(artifact)

            if not valve_result.success:
                # REQ-006: Track consecutive valve failures
                self._consecutive_valve_failures += 1
                if (
                    self._consecutive_valve_failures
                    >= self._max_consecutive_valve_failures
                ):
                    from statekanban.core.errors import ValveReworkLoopError

                    raise ValveReworkLoopError(
                        f"Consecutive valve failures ({self._consecutive_valve_failures}): "
                        f"possible infinite rework loop"
                    )

                # Valve failed: inject ErrorSignal
                error_signal = ErrorSignal(
                    signal_id=make_signal_id(),
                    author_role="OutputValve",
                    target_id=artifact_path,
                    payload={"artifact_path": artifact_path},
                    timestamp=now_utc(),
                    round_number=sig.round_number,
                    error_code="SK_OV_001",
                    error_detail=valve_result.error or "OutputValve validation failed",
                )
                self._kanban.fluid.write_signal(error_signal)
            else:
                # REQ-006: Reset consecutive failure counter on success
                self._consecutive_valve_failures = 0

    def _log_circuit_break(self, round_num: int) -> None:
        """Log circuit break event to AuditZone and stderr."""
        self._kanban.audit.log(
            event_type="circuit_break",
            actor="Engine",
            action="circuit_break",
            details={"round": round_num, "max_rounds": self._breaker.max_rounds},
        )
        if self._verbose:
            print(
                f"[Circuit Break] Max rounds ({self._breaker.max_rounds}) exceeded at round {round_num}",
                file=sys.stderr,
            )

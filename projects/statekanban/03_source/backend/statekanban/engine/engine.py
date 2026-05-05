"""Engine: top-level orchestrator that drives the development loop.

Composes all sub-components and executes the drive loop until
convergence or circuit break.

The Engine holds no mutable state between rounds. All state lives in
the StateKanban. The Engine only reads from and writes to the kanban
via the existing API.
"""

from __future__ import annotations

import datetime
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
from statekanban.engine.response_parser import ParsedResponse, ParsedResponseType, ResponseParser
from statekanban.engine.router import SignalRouter
from statekanban.engine.scheduler import RoleScheduler
from statekanban.adapters.base import LLMAdapter
from statekanban.config import Config


class Engine:
    """Top-level orchestrator that drives the development loop.

    Composes all sub-components and executes the drive loop until
    convergence or circuit break.
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
        """
        self._kanban = kanban
        self._bus = bus
        self._registry = registry
        self._valve = valve
        self._slicer = slicer
        self._pm = pm
        self._adapter = adapter
        self._config = config
        self._parser = ResponseParser(kanban=kanban)
        self._convergence = ConvergenceDetector(kanban)
        self._scheduler = RoleScheduler()
        self._breaker = CircuitBreaker(max_rounds=config.convergence_max_rounds)
        self._summarizer = ResultSummarizer(kanban, pm)
        self._router = SignalRouter(pm)
        self._verbose = False

    def set_verbose(self, verbose: bool) -> None:
        """Enable per-round verbose output to stderr."""
        self._verbose = verbose

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

            # 4. Convergence check for all pending targets
            all_results = self._convergence.check_all_pending(round_num)
            all_converged = all(r.converged for r in all_results.values()) if all_results else False

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
        2. Call LLM via adapter.
        3. Parse response into ParsedResponse objects.
        4. Inject parsed signals into FluidZone.

        Args:
            role: The role to process.
            round_number: Current round number (1-based).
        """
        try:
            # 3a. Viewport slice (role-isolated)
            slice_data = self._slicer.slice(role)

            if self._verbose:
                print(
                    f"[Round {round_number}] {role.capitalize()}: "
                    f"viewport={len(slice_data.signals)} signals, "
                    f"{len(slice_data.artifacts)} artifacts",
                    file=sys.stderr,
                )

            # 3b. LLM call
            raw_response = await self._call_llm_for_role(role, slice_data)

            if self._verbose:
                token_count = len((raw_response.content or "")) // 4
                print(
                    f"[Round {round_number}] {role.capitalize()}: "
                    f"LLM response ~{token_count} tokens",
                    file=sys.stderr,
                )

            # 3c. Parse response into typed signals
            parsed_list = self._parser.parse(raw_response, role, round_number)

            # 3d. Inject parsed signals into FluidZone
            for parsed in parsed_list:
                self._inject_parsed(parsed, role, round_number)

        except Exception as exc:
            # Never crash the kernel -- inject error signal and continue
            error_signal = ErrorSignal(
                signal_id=make_signal_id(),
                author_role="Engine",
                target_id=role,
                payload={"error": str(exc)},
                timestamp=now_utc(),
                round_number=round_number,
                error_code="SK_EN_002",
                error_detail=f"Role processing error: {exc}",
            )
            try:
                self._kanban.fluid.write_signal(error_signal)
            except Exception:
                pass

    async def _call_llm_for_role(self, role: str, slice_data: ViewportSlice) -> LLMResponse:
        """Invoke LLM for a role with the given viewport slice.

        Uses the adapter directly (via ToolRegistry dispatch is optional;
        the adapter already provides the LLM interface).

        Args:
            role: The requesting role.
            slice_data: The viewport slice as context.

        Returns:
            Raw LLMResponse.
        """
        # Build a context message from the viewport slice
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

        context_text = "\n".join(context_parts)

        messages = [LLMMessage(role="user", content=context_text)]

        response = await self._adapter.complete(
            messages=messages,
            max_tokens=self._config.llm_max_tokens,
            temperature=self._config.llm_temperature,
        )
        return response

    def _inject_parsed(self, parsed: ParsedResponse, author_role: str, round_number: int) -> None:
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

    async def _crystalize_and_write(self) -> None:
        """After convergence: fixate artifact into CrystalZone and submit to OutputValve.

        Steps:
        1. Extract the artifact content from the converged intent signal payload.
        2. Create an Artifact instance.
        3. Append to CrystalZone.
        4. Submit to OutputValve.validate_and_write() (async).
        5. If valve fails, inject ErrorSignal into FluidZone.
        """
        # Read all intent signals and look for artifact payloads
        intent_signals = self._kanban.fluid.read_signals(signal_type=SignalType.INTENT)
        for sig in intent_signals:
            artifact_content = sig.payload.get("artifact_content", "")
            if not artifact_content:
                continue

            artifact_path = sig.payload.get("artifact_path", f"output_{sig.target_id}.py")
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

            # Submit to OutputValve (async, can be awaited directly since
            # we are inside an async drive() method)
            valve_result = await self._valve.validate_and_write(artifact)

            if not valve_result.success:
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
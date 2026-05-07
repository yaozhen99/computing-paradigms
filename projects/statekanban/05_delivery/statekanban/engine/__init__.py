"""Engine module: drive loop orchestrator for StateKanban.

Sub-components:
  - Engine: main drive loop class
  - ResponseParser: parse LLM raw responses into typed signals
  - ConvergenceDetector: check signal convergence
  - RoleScheduler: iterate roles in scheduling order
  - CircuitBreaker: enforce max rounds
  - ResultSummarizer: produce EngineResult summaries
"""

from statekanban.engine.engine import Engine
from statekanban.engine.response_parser import (
    ResponseParser,
    ParsedResponse,
    ParsedResponseType,
)
from statekanban.engine.convergence import ConvergenceDetector, ConvergenceCheckResult
from statekanban.engine.scheduler import RoleScheduler
from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.engine.result import ResultSummarizer
from statekanban.engine.router import SignalRouter

__all__ = [
    "Engine",
    "ResponseParser",
    "ParsedResponse",
    "ParsedResponseType",
    "ConvergenceDetector",
    "ConvergenceCheckResult",
    "RoleScheduler",
    "CircuitBreaker",
    "ResultSummarizer",
    "SignalRouter",
]

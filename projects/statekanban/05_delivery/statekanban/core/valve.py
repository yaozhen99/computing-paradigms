"""OutputValve: mandatory validation chain for all physical writes.

No physical I/O bypasses this module. The write_file tool delegates here.

Validation chain (sequential, fail-fast):
1. Syntax check (AST parse for Python, JSON parse for configs)
2. Type check (optional, configurable)
3. Test execution (pytest subprocess for test artifacts; lint for code)

On failure: ErrorSignal injected back into FluidZone.
On success: Atomic write via temp file + os.replace().
"""

from __future__ import annotations

import ast
import json
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import logging

from statekanban.core.errors import AtomicWriteError, ValvePathViolationError
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    ErrorSignal,
    StateKanban,
    make_signal_id,
    now_utc,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of a single validation step."""

    passed: bool
    validator_name: str
    error_detail: str = ""


@dataclass
class ValveResult:
    """Result of the full validation + write pipeline."""

    success: bool
    artifact_path: str | None = None
    validation_results: list[ValidationResult] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Validator ABC
# ---------------------------------------------------------------------------


class Validator(ABC):
    """Base class for valve validators."""

    @abstractmethod
    async def validate(self, artifact: Artifact) -> ValidationResult:
        """Validate an artifact.

        Returns:
            ValidationResult with pass/fail status and optional error detail.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in validators
# ---------------------------------------------------------------------------


class SyntaxValidator(Validator):
    """Validates syntax: AST parse for Python, JSON parse for configs."""

    async def validate(self, artifact: Artifact) -> ValidationResult:
        if artifact.artifact_type == ArtifactType.CODE:
            if artifact.path.endswith(".py"):
                try:
                    ast.parse(artifact.content)
                except SyntaxError as exc:
                    return ValidationResult(
                        passed=False,
                        validator_name="SyntaxValidator",
                        error_detail=f"Python syntax error: {exc}",
                    )
        elif artifact.artifact_type == ArtifactType.CONFIG:
            if artifact.path.endswith(".json"):
                try:
                    json.loads(artifact.content)
                except json.JSONDecodeError as exc:
                    return ValidationResult(
                        passed=False,
                        validator_name="SyntaxValidator",
                        error_detail=f"JSON parse error: {exc}",
                    )

        return ValidationResult(
            passed=True,
            validator_name="SyntaxValidator",
        )


class TypeValidator(Validator):
    """Optional type check validator (stub for future expansion)."""

    async def validate(self, artifact: Artifact) -> ValidationResult:
        # Type checking is optional and configurable per artifact type.
        # For now, always pass -- can be extended with mypy or similar.
        return ValidationResult(
            passed=True,
            validator_name="TypeValidator",
        )


class TestValidator(Validator):
    """Test execution validator (stub for subprocess-based testing)."""

    async def validate(self, artifact: Artifact) -> ValidationResult:
        # Test execution runs pytest for test artifacts.
        # Stub: always pass for now -- real implementation would spawn subprocess.
        if artifact.artifact_type == ArtifactType.TEST:
            # In a real implementation, this would run pytest on the artifact
            pass
        return ValidationResult(
            passed=True,
            validator_name="TestValidator",
        )


# ---------------------------------------------------------------------------
# OutputValve
# ---------------------------------------------------------------------------


class OutputValve:
    """Mandatory validation chain for all physical writes."""

    def __init__(
        self,
        validators: list[Validator] | None = None,
        kanban: StateKanban | None = None,
        project_root: str = "",  # REQ-503: deprecated, use config
        config: Any | None = None,  # REQ-604: preferred
    ) -> None:
        """
        Args:
            validators: Ordered list of validators.
                Default: [SyntaxValidator, TypeValidator, TestValidator].
            kanban: StateKanban instance for error signal injection.
            project_root: Project space root (deprecated, use config).
            config: Config instance for path resolution (REQ-604).
        """
        self._validators: list[Validator] = validators or [
            SyntaxValidator(),
            TypeValidator(),
            TestValidator(),
        ]
        self._kanban = kanban
        self._config = config
        # Backward compat: if config not provided, store project_root
        if config is not None:
            self._project_root = config.project_root
        else:
            self._project_root = project_root

    def set_kanban(self, kanban: StateKanban) -> None:
        """Set the StateKanban instance (for error signal injection)."""
        self._kanban = kanban

    async def validate_and_write(self, artifact: Artifact) -> ValveResult:
        """Execute validation chain and perform atomic write if all pass.

        Args:
            artifact: The artifact to validate and write.

        Returns:
            ValveResult indicating success or failure with details.

        Side effects:
            On success: writes file to filesystem via temp+rename.
            On failure: nothing written to filesystem.
        """
        # Run validation chain (sequential, fail-fast)
        results: list[ValidationResult] = []
        for validator in self._validators:
            result = await validator.validate(artifact)
            results.append(result)
            if not result.passed:
                # Inject error signal into FluidZone
                self._inject_error_signal(artifact, result)
                return ValveResult(
                    success=False,
                    validation_results=results,
                    error=result.error_detail,
                )

        # All validators passed -- validate and resolve artifact path (REQ-601)
        try:
            resolved_path = self._validate_path(artifact.path)
        except ValvePathViolationError as exc:
            error_detail = f"[SK_VS_005] {exc}"
            self._inject_error_signal(
                artifact,
                ValidationResult(
                    passed=False,
                    validator_name="PathValidation",
                    error_detail=error_detail,
                ),
            )
            return ValveResult(
                success=False,
                validation_results=results,
                error=error_detail,
            )
        logger.debug(
            "Valve write: original_path=%s, resolved_path=%s",
            artifact.path,
            resolved_path,
        )
        try:
            self._atomic_write(resolved_path, artifact.content)
        except AtomicWriteError as exc:
            self._inject_error_signal(
                artifact,
                ValidationResult(
                    passed=False,
                    validator_name="AtomicWrite",
                    error_detail=str(exc),
                ),
            )
            return ValveResult(
                success=False,
                validation_results=results,
                error=str(exc),
            )

        return ValveResult(
            success=True,
            artifact_path=resolved_path,
            validation_results=results,
        )

    def add_validator(self, validator: Validator, position: int = -1) -> None:
        """Insert a validator at a given position in the chain."""
        if position == -1:
            self._validators.append(validator)
        else:
            self._validators.insert(position, validator)

    # REQ-503/REQ-604: Resolve artifact path against project_root
    def _resolve_artifact_path(self, artifact_path: str) -> str:
        """Resolve an artifact path for writing.

        REQ-604: When a Config is provided, delegates to
        config.resolve_path() for sandbox-safe resolution.
        Otherwise falls back to legacy project_root/CWD resolution.

        Args:
            artifact_path: Path from the artifact.

        Returns:
            Absolute resolved path.
        """
        # REQ-604: delegate to config when available
        if self._config is not None:
            logger.debug(
                "Valve delegating path resolution to config: %s", artifact_path
            )
            return self._config.resolve_path(artifact_path)
        # Fallback: project_root or CWD (backward compatible with R5)
        if os.path.isabs(artifact_path):
            return artifact_path
        base = self._project_root if self._project_root else os.getcwd()
        return os.path.join(base, artifact_path)

    # REQ-601: Path sandbox validation
    def _validate_path(self, path: str) -> str:
        """Validate that a write path stays within the output directory.

        REQ-601: All write paths must resolve to a subpath of the
        project root (or output directory). Traversal attempts (../),
        absolute paths pointing elsewhere, and symlinks pointing
        outside are rejected.

        Args:
            path: The artifact path to validate.

        Returns:
            The validated absolute path.

        Raises:
            ValvePathViolationError: SK_VS_005 if path escapes output dir.
        """
        # Determine the sandbox boundary first
        if self._config is not None:
            sandbox_root = os.path.realpath(self._config.project_root)
        elif self._project_root:
            sandbox_root = os.path.realpath(self._project_root)
        else:
            # No sandbox configured -- all paths allowed (backward compat)
            resolved = self._resolve_artifact_path(path)
            return os.path.realpath(resolved)

        # Resolve the path, catching PathEscapeError from config.resolve_path
        try:
            resolved = self._resolve_artifact_path(path)
        except Exception as exc:
            # PathEscapeError or ValueError from config.resolve_path
            raise ValvePathViolationError(
                attempted_path=path,
                output_dir=sandbox_root,
            ) from exc

        # Normalize symlinks (REQ-601 rule 3)
        resolved = os.path.realpath(resolved)

        # Check that resolved path is within sandbox
        if not Path(resolved).is_relative_to(Path(sandbox_root)):
            raise ValvePathViolationError(
                attempted_path=path,
                output_dir=sandbox_root,
            )

        return resolved

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    # Validator name -> error code mapping (type-derived, not string-matched)
    _VALIDATOR_ERROR_CODES: dict[str, str] = {
        "SyntaxValidator": "SK_OV_001",
        "TypeValidator": "SK_OV_002",
        "TestValidator": "SK_OV_003",
        "AtomicWrite": "SK_OV_004",
        "HumanGate": "SK_OV_005",
        "PathValidation": "SK_VS_005",
    }

    def _inject_error_signal(
        self, artifact: Artifact, result: ValidationResult
    ) -> None:
        """Inject an ErrorSignal into FluidZone on validation failure."""
        if self._kanban is None:
            return

        error_code = self._VALIDATOR_ERROR_CODES.get(result.validator_name, "SK_OV_000")

        error_signal = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="OutputValve",
            target_id=artifact.path,
            payload={
                "artifact_path": artifact.path,
                "validator_name": result.validator_name,
            },
            timestamp=now_utc(),
            round_number=0,
            error_code=error_code,
            error_detail=result.error_detail,
        )
        self._kanban.fluid.write_signal(error_signal)

    @staticmethod
    def _atomic_write(path: str, content: str) -> None:
        """Write content to file atomically via temp file + rename.

        Uses temp file + os.replace() (POSIX) or os.rename() with
        fallback (Windows).

        Raises:
            AtomicWriteError: If the write fails.
        """
        try:
            # Ensure parent directory exists
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            # Write to temp file first
            fd, tmp_path = tempfile.mkstemp(
                dir=parent or None,
                prefix=".statekanban_tmp_",
                suffix=os.path.splitext(path)[1],
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                # Atomic replace
                os.replace(tmp_path, path)
            except BaseException:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except AtomicWriteError:
            raise
        except OSError as exc:
            raise AtomicWriteError(f"Atomic write failed for {path}: {exc}") from exc

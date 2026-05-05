"""Tests for OutputValve: syntax validation, chain, atomic write, error injection."""

from __future__ import annotations

import os

import pytest

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    SignalType,
    compute_checksum,
    now_utc,
)
from statekanban.core.valve import (
    OutputValve,
    SyntaxValidator,
    TypeValidator,
    TestValidator,
    Validator,
    ValidationResult,
)


def _make_code_artifact(path: str = "output.py", content: str = "x = 1") -> Artifact:
    return Artifact(
        seq_no=0,
        artifact_type=ArtifactType.CODE,
        path=path,
        content=content,
        checksum=compute_checksum(content),
        author_role="coder",
        created_at=now_utc(),
    )


def _make_config_artifact(path: str = "config.json", content: str = '{"a":1}') -> Artifact:
    return Artifact(
        seq_no=0,
        artifact_type=ArtifactType.CONFIG,
        path=path,
        content=content,
        checksum=compute_checksum(content),
        author_role="coder",
        created_at=now_utc(),
    )


class TestSyntaxValidator:
    """TC-OV-001 ~ TC-OV-005: Syntax validation."""

    @pytest.mark.asyncio
    async def test_valid_python_code(self):
        # TC-OV-001
        v = SyntaxValidator()
        art = _make_code_artifact(content="x = 1")
        result = await v.validate(art)
        assert result.passed is True
        assert result.validator_name == "SyntaxValidator"

    @pytest.mark.asyncio
    async def test_invalid_python_code(self):
        # TC-OV-002
        v = SyntaxValidator()
        art = _make_code_artifact(content="def (")
        result = await v.validate(art)
        assert result.passed is False
        assert "syntax" in result.error_detail.lower()

    @pytest.mark.asyncio
    async def test_valid_json_config(self):
        # TC-OV-003
        v = SyntaxValidator()
        art = _make_config_artifact(content='{"a": 1}')
        result = await v.validate(art)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_invalid_json_config(self):
        # TC-OV-004
        v = SyntaxValidator()
        art = _make_config_artifact(content="{invalid}")
        result = await v.validate(art)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_non_py_json_passes(self):
        # TC-OV-005
        v = SyntaxValidator()
        art = _make_code_artifact(path="readme.txt", content="anything goes")
        result = await v.validate(art)
        assert result.passed is True


class TestOutputValveChain:
    """TC-OV-006 ~ TC-OV-007: Validation chain."""

    @pytest.mark.asyncio
    async def test_full_chain_passes(self, valve, tmp_dir):
        # TC-OV-006
        art = _make_code_artifact(path=os.path.join(tmp_dir, "output.py"))
        result = await valve.validate_and_write(art)
        assert result.success is True
        assert result.artifact_path is not None

    @pytest.mark.asyncio
    async def test_fail_fast_on_syntax(self, valve, tmp_dir):
        # TC-OV-007
        art = _make_code_artifact(
            path=os.path.join(tmp_dir, "bad.py"),
            content="def (",
        )
        result = await valve.validate_and_write(art)
        assert result.success is False
        # Only first validator ran (fail-fast)
        assert len(result.validation_results) == 1
        assert result.validation_results[0].validator_name == "SyntaxValidator"


class TestOutputValveWrite:
    """TC-OV-008 ~ TC-OV-009: Atomic write."""

    @pytest.mark.asyncio
    async def test_atomic_write_on_success(self, valve, tmp_dir):
        # TC-OV-008
        path = os.path.join(tmp_dir, "output.py")
        art = _make_code_artifact(path=path)
        result = await valve.validate_and_write(art)
        assert result.success is True
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == "x = 1"

    @pytest.mark.asyncio
    async def test_atomic_write_creates_parent_dir(self, valve, tmp_dir):
        # TC-OV-009
        path = os.path.join(tmp_dir, "subdir", "nested", "output.py")
        art = _make_code_artifact(path=path)
        result = await valve.validate_and_write(art)
        assert result.success is True
        assert os.path.exists(path)


class TestOutputValveErrorInjection:
    """TC-OV-010: ErrorSignal injected on failure."""

    @pytest.mark.asyncio
    async def test_error_signal_injected(self, valve, kanban, tmp_dir):
        # TC-OV-010
        art = _make_code_artifact(
            path=os.path.join(tmp_dir, "bad.py"),
            content="def (",
        )
        result = await valve.validate_and_write(art)
        assert result.success is False
        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        assert len(error_signals) > 0


class TestOutputValveCustomValidator:
    """TC-OV-011 ~ TC-OV-013: Custom and stub validators."""

    def test_add_custom_validator(self, valve):
        # TC-OV-011
        class CustomValidator(Validator):
            async def validate(self, artifact: Artifact) -> ValidationResult:
                return ValidationResult(passed=True, validator_name="custom")

        initial_count = len(valve._validators)
        valve.add_validator(CustomValidator(), position=0)
        assert len(valve._validators) == initial_count + 1
        assert valve._validators[0].__class__.__name__ == "CustomValidator"

    @pytest.mark.asyncio
    async def test_type_validator_passes(self):
        # TC-OV-012
        v = TypeValidator()
        art = _make_code_artifact()
        result = await v.validate(art)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_test_validator_passes(self):
        # TC-OV-013
        v = TestValidator()
        art = _make_code_artifact()
        result = await v.validate(art)
        assert result.passed is True
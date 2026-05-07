"""Valve Path Contract tests (REQ-604).

Covers:
- OutputValve write path goes through config.resolve_path()
- Sandbox mode: write path stays within project_root
- Path escape: traversal path raises PathEscapeError, no file written
- project_root=None backward compatibility
- OutputValve accepts config parameter
- Debug logging of original and resolved path
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pytest

from statekanban.config import Config
from statekanban.core.errors import PathEscapeError
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    StateKanban,
    compute_checksum,
    now_utc,
)
from statekanban.core.valve import OutputValve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_code_artifact(path: str, content: str = "x = 1") -> Artifact:
    return Artifact(
        seq_no=0,
        artifact_type=ArtifactType.CODE,
        path=path,
        content=content,
        checksum=compute_checksum(content),
        author_role="coder",
        created_at=now_utc(),
    )


# ---------------------------------------------------------------------------
# REQ-604: Valve Path Contract -- config parameter
# ---------------------------------------------------------------------------


class TestValveConfigParameter:

    def test_output_valve_accepts_config(self):
        """AC-604.4: OutputValve constructor accepts config parameter."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            valve = OutputValve(config=config)
            assert valve._config is config

    def test_output_valve_with_kanban_and_config(self):
        """OutputValve accepts both kanban and config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)
            assert valve._kanban is kanban
            assert valve._config is config

    def test_output_valve_config_overrides_project_root(self):
        """When both config and project_root are provided, config takes precedence."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            valve = OutputValve(config=config, project_root="/other/path")
            assert valve._project_root == tmp_dir

    def test_output_valve_backward_compat_without_config(self):
        """OutputValve works without config (backward compat)."""
        valve = OutputValve()
        assert valve._config is None
        assert valve._project_root == ""


# ---------------------------------------------------------------------------
# REQ-604: Valve Path Contract -- resolve_path delegation
# ---------------------------------------------------------------------------


class TestValveResolvePathDelegation:

    def test_resolve_delegates_to_config_resolve_path(self):
        """AC-604.1: _resolve_artifact_path delegates to config.resolve_path()."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            valve = OutputValve(config=config)
            result = valve._resolve_artifact_path("output.py")
            expected = str((Path(tmp_dir) / "output.py").resolve())
            assert result == expected
            # Strengthened assertion: resolved path must be within project_root
            assert Path(result).is_relative_to(Path(tmp_dir).resolve())

    def test_resolve_uses_project_root_when_no_config(self):
        """Without config, falls back to project_root-based resolution."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            valve = OutputValve(project_root=tmp_dir)
            result = valve._resolve_artifact_path("output.py")
            assert result == os.path.join(tmp_dir, "output.py")

    def test_resolve_absolute_path_unchanged_with_config(self):
        """Absolute paths are returned unchanged when using config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            valve = OutputValve(config=config)
            abs_path = os.path.join(tmp_dir, "abs_output.py")
            result = valve._resolve_artifact_path(abs_path)
            assert result == abs_path


# ---------------------------------------------------------------------------
# REQ-604: Valve Path Contract -- write operations
# ---------------------------------------------------------------------------


class TestValvePathContractWrite:

    @pytest.mark.asyncio
    async def test_normal_path_write_succeeds(self):
        """AC-604.1: Normal path within project_root writes successfully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact("output.py")
            result = await valve.validate_and_write(art)
            assert result.success is True
            assert result.artifact_path is not None
            # File should exist within project_root
            assert (Path(tmp_dir) / "output.py").exists()
            # Strengthened assertion: artifact_path must be within project_root
            assert Path(result.artifact_path).is_relative_to(Path(tmp_dir).resolve())

    @pytest.mark.asyncio
    async def test_escape_path_write_blocked(self):
        """AC-604.2: Traversal path raises PathEscapeError, no file written."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact("../../etc/evil.py")
            with pytest.raises(PathEscapeError) as exc_info:
                await valve.validate_and_write(art)
            assert exc_info.value.error_code == "SK_06_001"
            # Strengthened assertions: verify attempted_path and project_root
            assert exc_info.value.attempted_path == "../../etc/evil.py"
            assert tmp_dir in exc_info.value.project_root
            # No file should be written at escaped path
            assert not os.path.exists("/etc/evil.py")

    @pytest.mark.asyncio
    async def test_absolute_path_write_succeeds_with_warning(self):
        """AC-604.3: Absolute path writes successfully (warning logged)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            abs_output = os.path.join(tmp_dir, "abs_output.py")
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact(abs_output)
            result = await valve.validate_and_write(art)
            assert result.success is True
            assert result.artifact_path == abs_output
            # Strengthened assertion: file should actually exist on disk
            assert os.path.exists(abs_output)

    @pytest.mark.asyncio
    async def test_nested_path_write_succeeds(self):
        """Nested relative path within project_root writes successfully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact("src/module/output.py")
            result = await valve.validate_and_write(art)
            assert result.success is True
            assert (Path(tmp_dir) / "src" / "module" / "output.py").exists()
            # Strengthened assertion: artifact_path is within project_root
            assert Path(result.artifact_path).is_relative_to(Path(tmp_dir).resolve())

    @pytest.mark.asyncio
    async def test_dotdot_within_root_succeeds(self):
        """Paths with .. that stay within project_root succeed."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create subdir so that subdir/../output.py stays within root
            os.makedirs(os.path.join(tmp_dir, "subdir"), exist_ok=True)
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact("subdir/../output.py")
            result = await valve.validate_and_write(art)
            assert result.success is True
            # File should be at project_root/output.py
            assert (Path(tmp_dir) / "output.py").exists()


# ---------------------------------------------------------------------------
# REQ-604: Valve Path Contract -- debug logging
# ---------------------------------------------------------------------------


class TestValvePathContractLogging:

    @pytest.mark.asyncio
    async def test_valve_logs_resolved_path(self, caplog):
        """AC-604.5: Valve writes debug log with original and resolved path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            config = Config(project_root=tmp_dir)
            valve = OutputValve(kanban=kanban, config=config)

            art = _make_code_artifact("output.py")
            with caplog.at_level(logging.DEBUG, logger="statekanban.core.valve"):
                result = await valve.validate_and_write(art)
            assert result.success is True
            # Check that debug log contains both original and resolved path
            log_messages = [r.message for r in caplog.records]
            assert any("output.py" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_valve_logs_delegation_to_config(self, caplog):
        """Debug log shows Valve delegating to config.resolve_path()."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            valve = OutputValve(config=config)

            with caplog.at_level(logging.DEBUG, logger="statekanban.core.valve"):
                valve._resolve_artifact_path("output.py")
            log_messages = [r.message for r in caplog.records]
            assert any("delegating" in msg.lower() or "config" in msg.lower()
                       for msg in log_messages)


# ---------------------------------------------------------------------------
# REQ-604: Backward compatibility
# ---------------------------------------------------------------------------


class TestValvePathContractBackwardCompat:

    @pytest.mark.asyncio
    async def test_valve_write_without_config_uses_cwd(self):
        """Without config, OutputValve falls back to CWD-based resolution."""
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        with tempfile.TemporaryDirectory() as tmp_dir:
            abs_path = os.path.join(tmp_dir, "output.py")
            art = _make_code_artifact(abs_path)
            result = await valve.validate_and_write(art)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_valve_write_with_project_root_no_config(self):
        """With project_root but no config, legacy resolution still works."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            kanban = StateKanban()
            valve = OutputValve(kanban=kanban, project_root=tmp_dir)

            art = _make_code_artifact("output.py")
            result = await valve.validate_and_write(art)
            assert result.success is True
            assert os.path.exists(os.path.join(tmp_dir, "output.py"))

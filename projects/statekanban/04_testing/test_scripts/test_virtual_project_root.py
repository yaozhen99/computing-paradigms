"""VirtualProjectRoot and Path Traversal Guard tests (REQ-601, REQ-602).

Covers:
- VirtualProjectRoot creation, attributes, and serialization
- Config.resolve_path() normal path resolution
- Path traversal detection (../../etc/passwd, etc.)
- PathEscapeError with error code SK_06_001
- project_root="" backward compatibility (no sandbox mode)
- project_root set activates sandbox mode
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pytest

from statekanban.config import Config, VirtualProjectRoot
from statekanban.core.errors import PathEscapeError


# ---------------------------------------------------------------------------
# REQ-601: VirtualProjectRoot creation and attributes
# ---------------------------------------------------------------------------


class TestVirtualProjectRootCreation:

    def test_vpr_with_explicit_root(self):
        """AC-601.1: VirtualProjectRoot with an explicit root path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            assert vpr.root is not None
            assert vpr.is_set is True
            # root should be an absolute Path (resolved)
            assert vpr.root.is_absolute()

    def test_vpr_with_none_root(self):
        """project_root=None means CWD fallback (no sandbox)."""
        vpr = VirtualProjectRoot(root=None)
        assert vpr.root is None
        assert vpr.is_set is False

    def test_vpr_with_empty_string_root(self):
        """project_root="" means CWD fallback (backward compat)."""
        vpr = VirtualProjectRoot(root="")
        assert vpr.root is None
        assert vpr.is_set is False

    def test_vpr_with_relative_path_converts_to_absolute(self):
        """Relative path is resolved to absolute at construction time."""
        vpr = VirtualProjectRoot(root="some_relative_dir")
        assert vpr.root is not None
        assert vpr.root.is_absolute()

    def test_vpr_to_dict_with_root(self):
        """to_dict serializes root path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            d = vpr.to_dict()
            assert "root" in d
            assert d["root"] == str(vpr.root)

    def test_vpr_to_dict_with_none(self):
        """to_dict serializes None root."""
        vpr = VirtualProjectRoot(root=None)
        d = vpr.to_dict()
        assert d["root"] is None

    def test_vpr_from_dict_with_root(self):
        """from_dict deserializes root path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot.from_dict({"root": tmp_dir})
            assert vpr.is_set is True
            assert vpr.root == Path(tmp_dir).resolve()

    def test_vpr_from_dict_with_none(self):
        """from_dict deserializes None root."""
        vpr = VirtualProjectRoot.from_dict({"root": None})
        assert vpr.is_set is False
        assert vpr.root is None


# ---------------------------------------------------------------------------
# REQ-601: VirtualProjectRoot.resolve()
# ---------------------------------------------------------------------------


class TestVirtualProjectRootResolve:

    def test_resolve_relative_path_with_root(self):
        """resolve() joins relative path with project_root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            result = vpr.resolve("output.py")
            assert result == Path(tmp_dir) / "output.py"

    def test_resolve_relative_path_with_nested_path(self):
        """resolve() joins nested relative path with project_root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            result = vpr.resolve(".statekanban/snapshots/test.json")
            assert result == Path(tmp_dir) / ".statekanban/snapshots/test.json"

    def test_resolve_absolute_path_returns_as_is(self):
        """AC-601.2: Absolute path is returned unchanged (resolved)."""
        # Use a Windows-compatible absolute path
        abs_path = os.path.join(os.getcwd(), "some_absolute_path.txt")
        vpr = VirtualProjectRoot(root=os.getcwd())
        result = vpr.resolve(abs_path)
        # resolve() returns a resolved Path
        assert result == Path(abs_path).resolve()

    def test_resolve_absolute_path_logs_warning(self, caplog):
        """AC-601.2: Absolute path resolution logs a warning."""
        abs_path = os.path.join(os.getcwd(), "some_absolute_path.txt")
        vpr = VirtualProjectRoot(root=os.getcwd())
        with caplog.at_level(logging.WARNING):
            vpr.resolve(abs_path)
        assert any("absolute path" in r.message.lower() for r in caplog.records)

    def test_resolve_with_none_root_falls_back_to_cwd(self):
        """resolve() falls back to Path.cwd() when root is None."""
        vpr = VirtualProjectRoot(root=None)
        result = vpr.resolve("output.py")
        assert result == Path.cwd() / "output.py"

    def test_resolve_empty_path_returns_base(self):
        """resolve() with empty path returns base directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            result = vpr.resolve("")
            assert result == Path(tmp_dir)

    def test_resolve_null_bytes_raises_value_error(self):
        """resolve() rejects null bytes in path."""
        vpr = VirtualProjectRoot(root="/tmp/project")
        with pytest.raises(ValueError, match="null bytes"):
            vpr.resolve("test\x00bad")


# ---------------------------------------------------------------------------
# REQ-601: VirtualProjectRoot.is_within()
# ---------------------------------------------------------------------------


class TestVirtualProjectRootIsWithin:

    def test_is_within_with_path_inside_root(self):
        """is_within() returns True for paths inside project_root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpr = VirtualProjectRoot(root=tmp_dir)
            assert vpr.is_within(Path(tmp_dir) / "output.py") is True

    def test_is_within_with_path_outside_root(self):
        """is_within() returns False for paths outside project_root."""
        vpr = VirtualProjectRoot(root="/tmp/project_a")
        assert vpr.is_within(Path("/tmp/project_b/output.py")) is False

    def test_is_within_with_none_root_always_true(self):
        """is_within() always True when root is None (no sandbox)."""
        vpr = VirtualProjectRoot(root=None)
        assert vpr.is_within(Path("/any/random/path")) is True


# ---------------------------------------------------------------------------
# REQ-601: Config.resolve_path() delegation to VPR
# ---------------------------------------------------------------------------


class TestConfigResolvePathDelegation:

    def test_config_vpr_property_lazy_init(self):
        """Config.vpr is lazily initialized from project_root."""
        config = Config()
        assert config._vpr is None  # Not initialized yet
        vpr = config.vpr  # Access triggers lazy init
        assert vpr is not None
        assert isinstance(vpr, VirtualProjectRoot)

    def test_config_vpr_invalidated_on_project_root_change(self):
        """Changing project_root invalidates cached VPR."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config()
            vpr_before = config.vpr
            assert vpr_before.is_set is False

            config.project_root = tmp_dir
            # VPR cache was invalidated
            assert config._vpr is None
            vpr_after = config.vpr
            assert vpr_after.is_set is True
            assert vpr_after is not vpr_before

    def test_resolve_path_relative_with_project_root(self):
        """AC-601.1: resolve_path joins relative path with project_root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            result = config.resolve_path("output.py")
            # resolve_path returns str, uses Path.resolve() so path is normalized
            expected = str((Path(tmp_dir) / "output.py").resolve())
            assert result == expected

    def test_resolve_path_relative_without_project_root_falls_back_to_cwd(self):
        """resolve_path falls back to CWD when project_root is empty."""
        config = Config(project_root="")
        result = config.resolve_path("output.py")
        expected = str((Path.cwd() / "output.py").resolve())
        assert result == expected

    def test_resolve_path_absolute_path_unchanged(self):
        """AC-601.2: resolve_path returns absolute path unchanged."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            abs_path = os.path.join(tmp_dir, "absolute_file.py")
            result = config.resolve_path(abs_path)
            assert result == abs_path

    def test_resolve_path_absolute_path_logs_warning(self, caplog):
        """AC-601.2: resolve_path logs warning for absolute path input."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            abs_path = os.path.join(tmp_dir, "absolute_file.py")
            with caplog.at_level(logging.WARNING):
                config.resolve_path(abs_path)
            assert any("absolute path" in r.message.lower() for r in caplog.records)

    def test_resolve_path_null_bytes_raises_value_error(self):
        """resolve_path rejects null bytes in path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            with pytest.raises(ValueError, match="null bytes"):
                config.resolve_path("test\x00bad")


# ---------------------------------------------------------------------------
# REQ-602: Path Traversal Guard
# ---------------------------------------------------------------------------


class TestPathTraversalGuard:

    def test_resolve_path_traversal_double_dot_etc_passwd(self):
        """AC-602.1: resolve_path("../../etc/passwd") raises PathEscapeError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            with pytest.raises(PathEscapeError) as exc_info:
                config.resolve_path("../../etc/passwd")
            assert exc_info.value.error_code == "SK_06_001"

    def test_resolve_path_traversal_subdir_double_dot_etc(self):
        """AC-602.2: resolve_path("subdir/../../../etc/passwd") raises PathEscapeError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            with pytest.raises(PathEscapeError) as exc_info:
                config.resolve_path("subdir/../../../etc/passwd")
            assert exc_info.value.error_code == "SK_06_001"

    def test_resolve_path_valid_subdir_normal(self):
        """AC-602.3: resolve_path("valid/subdir/file.txt") returns normal path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            result = config.resolve_path("valid/subdir/file.txt")
            expected = str((Path(tmp_dir) / "valid/subdir/file.txt").resolve())
            assert result == expected

    def test_resolve_path_subdir_double_dot_other_no_escape(self):
        """AC-602.4: resolve_path("subdir/../other/file.txt") resolves within root."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            result = config.resolve_path("subdir/../other/file.txt")
            expected = str((Path(tmp_dir) / "other/file.txt").resolve())
            assert result == expected
            # Verify it stays within project_root
            assert Path(result).is_relative_to(Path(tmp_dir).resolve())

    def test_path_escape_error_code_is_sk_06_001(self):
        """AC-602.5: PathEscapeError has error code SK_06_001."""
        err = PathEscapeError(
            attempted_path="../../etc/passwd",
            project_root="/tmp/project",
        )
        assert err.error_code == "SK_06_001"
        assert err.http_analogy == 403

    def test_path_escape_error_contains_attempted_path_and_project_root(self):
        """AC-602.5: PathEscapeError message includes attempted_path and project_root."""
        err = PathEscapeError(
            attempted_path="../../etc/passwd",
            project_root="/tmp/project",
        )
        assert err.attempted_path == "../../etc/passwd"
        assert err.project_root == "/tmp/project"
        assert "../../etc/passwd" in str(err)
        assert "/tmp/project" in str(err)

    def test_path_escape_error_default_message(self):
        """PathEscapeError auto-generates message when none provided."""
        err = PathEscapeError(
            attempted_path="../secret",
            project_root="/sandbox",
        )
        assert "../secret" in str(err)
        assert "/sandbox" in str(err)

    def test_traversal_guard_uses_is_relative_to(self):
        """AC-602.6: Traversal guard uses Path.is_relative_to(), not string matching."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            # Valid path should not trigger error
            result = config.resolve_path("output.py")
            assert Path(result).is_relative_to(Path(tmp_dir).resolve())

    def test_path_escape_error_hierarchy(self):
        """PathEscapeError inherits from StateKanbanError."""
        from statekanban.core.errors import StateKanbanError

        err = PathEscapeError(attempted_path="x", project_root="y")
        assert isinstance(err, StateKanbanError)


# ---------------------------------------------------------------------------
# REQ-602: Sandbox mode activation and backward compatibility
# ---------------------------------------------------------------------------


class TestSandboxModeActivation:

    def test_project_root_empty_no_sandbox(self):
        """project_root="" does NOT activate sandbox mode -- traversal allowed."""
        config = Config(project_root="")
        # This path would normally escape a sandbox, but with empty root
        # it falls back to CWD, so resolve_path treats it as relative to CWD.
        # No PathEscapeError is raised because vpr.is_set is False.
        result = config.resolve_path("subdir/../output.py")
        assert result == str((Path.cwd() / "output.py").resolve())

    def test_project_root_set_activates_sandbox(self):
        """project_root set activates sandbox mode -- traversal blocked."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            with pytest.raises(PathEscapeError):
                config.resolve_path("../../etc/passwd")

    def test_sandbox_mode_traversal_blocked(self):
        """In sandbox mode, path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            # ../../sensitive escapes sandbox
            with pytest.raises(PathEscapeError) as exc_info:
                config.resolve_path("../../sensitive")
            assert exc_info.value.error_code == "SK_06_001"

    def test_sandbox_mode_valid_path_works(self):
        """In sandbox mode, valid paths resolve correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            result = config.resolve_path("src/output.py")
            assert Path(result).is_relative_to(Path(tmp_dir).resolve())

    def test_vpr_is_set_false_when_project_root_empty(self):
        """vpr.is_set is False when project_root is empty."""
        config = Config(project_root="")
        assert config.vpr.is_set is False

    def test_vpr_is_set_true_when_project_root_set(self):
        """vpr.is_set is True when project_root is set."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            assert config.vpr.is_set is True
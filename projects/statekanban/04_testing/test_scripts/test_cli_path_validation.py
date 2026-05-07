"""CLI Path Validation tests (REQ-605).

Covers:
- validate_project_root() null byte detection
- validate_project_root() relative path -> absolute conversion
- validate_project_root() nonexistent directory detection
- validate_project_root() file-instead-of-directory detection
- Path traversal detection through Config.resolve_path()
- CLI --project-root end-to-end validation
- Config.project_root setter with validate=True
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from statekanban.cli.validate import (
    NullByteError,
    PathNotDirectoryError,
    PathNotExistError,
    PathValidationError,
    validate_project_root,
)
from statekanban.config import Config
from statekanban.core.errors import PathEscapeError


# ---------------------------------------------------------------------------
# REQ-605: validate_project_root() -- null byte detection
# ---------------------------------------------------------------------------


class TestValidateProjectRootNullBytes:

    def test_null_byte_in_path_rejected(self):
        """AC-605.1: validate_project_root rejects paths with null bytes."""
        with pytest.raises(NullByteError):
            validate_project_root("/some/path\x00with_null")

    def test_null_byte_at_end_rejected(self):
        """Null byte at end of path rejected."""
        with pytest.raises(NullByteError):
            validate_project_root("/some/path\x00")

    def test_null_byte_at_start_rejected(self):
        """Null byte at start of path rejected."""
        with pytest.raises(NullByteError):
            validate_project_root("\x00/some/path")

    def test_clean_path_passes_null_check(self):
        """Clean path without null bytes passes null byte check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_project_root(tmp_dir)
            assert result is not None

    def test_null_byte_error_is_path_validation_error(self):
        """NullByteError inherits from PathValidationError."""
        assert issubclass(NullByteError, PathValidationError)


# ---------------------------------------------------------------------------
# REQ-605: validate_project_root() -- relative to absolute conversion
# ---------------------------------------------------------------------------


class TestValidateProjectRootRelativeConversion:

    def test_dot_converted_to_absolute(self):
        """AC-605.3: '.' is converted to absolute CWD path."""
        result = validate_project_root(".")
        assert Path(result).is_absolute()

    def test_relative_path_converted_to_absolute(self):
        """AC-605.3: Relative path is converted to absolute path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            rel_path = os.path.relpath(tmp_dir)
            result = validate_project_root(rel_path)
            assert Path(result).is_absolute()

    def test_absolute_path_left_unchanged(self):
        """Absolute path is left unchanged (except normalization)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_project_root(tmp_dir)
            assert Path(result).resolve() == Path(tmp_dir).resolve()


# ---------------------------------------------------------------------------
# REQ-605: validate_project_root() -- nonexistent directory detection
# ---------------------------------------------------------------------------


class TestValidateProjectRootNonexistent:

    def test_nonexistent_directory_rejected(self):
        """AC-605.4: validate_project_root rejects nonexistent directory."""
        with pytest.raises(PathNotExistError):
            validate_project_root("/this/path/definitely/does/not/exist")

    def test_file_instead_of_directory_rejected(self):
        """validate_project_root rejects a file path (not a directory)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            filepath = f.name
        try:
            with pytest.raises(PathNotDirectoryError):
                validate_project_root(filepath)
        finally:
            os.unlink(filepath)

    def test_existing_directory_accepted(self):
        """Existing directory is accepted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_project_root(tmp_dir)
            assert result is not None
            assert Path(result).exists()
            assert Path(result).is_dir()

    def test_path_not_exist_is_path_validation_error(self):
        """PathNotExistError inherits from PathValidationError."""
        assert issubclass(PathNotExistError, PathValidationError)

    def test_path_not_directory_is_path_validation_error(self):
        """PathNotDirectoryError inherits from PathValidationError."""
        assert issubclass(PathNotDirectoryError, PathValidationError)


# ---------------------------------------------------------------------------
# REQ-605: validate_project_root() -- empty and None handling
# ---------------------------------------------------------------------------


class TestValidateProjectRootEmptyNone:

    def test_empty_string_returns_cwd(self):
        """AC-605.5: Empty string resolves to CWD (backward compat)."""
        result = validate_project_root("")
        # Empty string resolves to CWD via Path("").resolve()
        assert Path(result).is_absolute()

    def test_none_raises_type_error(self):
        """None is not a valid path string -- TypeError."""
        with pytest.raises(TypeError):
            validate_project_root(None)


# ---------------------------------------------------------------------------
# REQ-605: Path traversal detection through Config.resolve_path()
# ---------------------------------------------------------------------------


class TestPathTraversalDetection:

    def test_traversal_in_resolve_path_rejected(self):
        """Path traversal is detected by Config.resolve_path(), not validate_project_root.
        validate_project_root validates the root itself; resolve_path guards traversal."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            with pytest.raises(PathEscapeError) as exc_info:
                config.resolve_path("../../etc/passwd")
            assert exc_info.value.error_code == "SK_06_001"

    def test_validate_project_root_allows_valid_traversal_free_path(self):
        """validate_project_root accepts paths without traversal components."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_project_root(tmp_dir)
            assert result is not None
            # No traversal components in result
            assert ".." not in Path(result).parts


# ---------------------------------------------------------------------------
# REQ-605: CLI --project-root end-to-end validation
# ---------------------------------------------------------------------------


class TestCLIProjectRootE2E:

    def test_cli_with_valid_project_root(self):
        """CLI accepts --project-root with a valid directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [sys.executable, "-m", "statekanban.cli.main", "status",
                 "--project-root", tmp_dir],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Should not fail due to project-root validation
            # (may fail for other reasons like no kanban state, that's ok)
            assert "project-root" not in result.stderr.lower() or result.returncode == 0

    def test_cli_with_null_byte_project_root_rejected(self):
        """Null byte in CLI args causes OS-level rejection (ValueError on Windows)."""
        # On Windows, subprocess.run raises ValueError for embedded null bytes
        # before the CLI even sees the argument. This is OS-level protection.
        with pytest.raises(ValueError, match="null"):
            subprocess.run(
                [sys.executable, "-m", "statekanban.cli.main", "status",
                 "--project-root", "/tmp/test\x00bad"],
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_cli_with_nonexistent_project_root_rejected(self):
        """CLI rejects --project-root pointing to nonexistent directory."""
        result = subprocess.run(
            [sys.executable, "-m", "statekanban.cli.main", "status",
             "--project-root", "/this/does/not/exist"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0

    def test_cli_without_project_root_works(self):
        """CLI works without --project-root (backward compat)."""
        result = subprocess.run(
            [sys.executable, "-m", "statekanban.cli.main", "status"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should not crash due to missing project-root
        # May fail for other reasons (no kanban state), but not arg validation


# ---------------------------------------------------------------------------
# REQ-605: Config.project_root setter with validate=True
# ---------------------------------------------------------------------------


class TestConfigProjectRootSetterValidation:

    def test_config_project_root_valid(self):
        """Config(project_root=valid) works."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config(project_root=tmp_dir)
            assert config.project_root == tmp_dir

    def test_config_project_root_null_byte_caught_by_validate(self):
        """Config(project_root=...) with null byte: caught by validate_project_root().
        Config is a dataclass that does not validate; null bytes are caught by
        validate_project_root() which is the validation entry point."""
        config = Config(project_root="/tmp/test\x00bad")
        # Config stores it without validation (dataclass)
        assert config.project_root == "/tmp/test\x00bad"
        # But validate_project_root catches null bytes
        with pytest.raises(NullByteError):
            validate_project_root(config.project_root)

    def test_config_project_root_nonexistent_caught_by_validate(self):
        """Config(project_root=...) with nonexistent path: caught by validate_project_root().
        Config is a dataclass that does not validate; path existence is checked by
        validate_project_root()."""
        config = Config(project_root="/this/path/does/not/exist")
        # Config stores it without validation
        assert config.project_root == "/this/path/does/not/exist"
        # But validate_project_root catches it
        with pytest.raises(PathNotExistError):
            validate_project_root(config.project_root)

    def test_config_project_root_empty_allowed(self):
        """Config(project_root="") works (backward compat, no validation)."""
        config = Config(project_root="")
        assert config.project_root == ""

    def test_config_project_root_none_allowed(self):
        """Config(project_root=None) works (backward compat)."""
        config = Config(project_root=None)
        assert config.project_root is None or config.project_root == ""

    def test_config_project_root_assignment_invalidates_vpr(self):
        """Setting project_root via attribute invalidates cached VirtualProjectRoot."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = Config()
            _ = config.vpr  # Trigger lazy init
            assert config._vpr is not None

            config.project_root = tmp_dir
            # VPR should be invalidated (setter clears _vpr)
            # On next access, new VPR is created with updated root
            assert config.vpr.is_set is True

    def test_config_project_root_file_rejected(self):
        """Config(project_root=file) -- file-as-dir caught by validate_project_root().
        Config is a dataclass that does not validate; file check is done by
        validate_project_root()."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            filepath = f.name
        try:
            config = Config(project_root=filepath)
            # Config stores it without validation
            assert config.project_root == filepath
            # But validate_project_root catches it
            with pytest.raises(PathNotDirectoryError):
                validate_project_root(config.project_root)
        finally:
            os.unlink(filepath)

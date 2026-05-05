"""write_file tool implementation.

Delegates to OutputValve for validation and atomic write.
Only accessible by coder and integrator roles.
"""

from __future__ import annotations

from typing import Any

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    compute_checksum,
    now_utc,
)
from statekanban.core.valve import OutputValve


def create_write_file_tool(valve: OutputValve) -> Any:
    """Create the write_file tool implementation bound to an OutputValve.

    Returns:
        Async callable that accepts params dict and returns result dict.
    """

    async def write_file(params: dict[str, Any]) -> dict[str, Any]:
        """Write an artifact to the filesystem via OutputValve.

        Args:
            params: Must contain 'path' and 'content'.
                    May contain 'artifact_type' (default: 'code').

        Returns:
            Dict with 'success', 'path', and optional 'error'.
        """
        path = params.get("path", "")
        content = params.get("content", "")
        artifact_type_str = params.get("artifact_type", "code")

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            artifact_type = ArtifactType.CODE

        artifact = Artifact(
            seq_no=0,  # Auto-assigned by CrystalZone
            artifact_type=artifact_type,
            path=path,
            content=content,
            checksum=compute_checksum(content),
            author_role=params.get("author_role", "unknown"),
            created_at=now_utc(),
        )

        result = await valve.validate_and_write(artifact)

        if result.success:
            return {
                "success": True,
                "path": result.artifact_path,
            }
        else:
            return {
                "success": False,
                "path": path,
                "error": result.error,
                "validation_results": [
                    {"passed": v.passed, "validator": v.validator_name, "detail": v.error_detail}
                    for v in result.validation_results
                ],
            }

    return write_file

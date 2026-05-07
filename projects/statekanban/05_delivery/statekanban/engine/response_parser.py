"""ResponseParser: parse raw LLM responses into typed ParsedResponse objects.

Handles three input formats:
1. Structured JSON: {"type": "intent"|"veto"|"artifact", ...}
2. Fenced code block: ```python ... ```
3. Unstructured text: treated as error
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from statekanban.core.kanban import (
    ErrorSignal,
    LLMResponse,
    SignalType,
    make_signal_id,
    now_utc,
    StateKanban,
)

# ---------------------------------------------------------------------------
# ParsedResponse types
# ---------------------------------------------------------------------------


class ParsedResponseType(Enum):
    """Types of parsed LLM responses."""

    INTENT = "intent"
    VETO = "veto"
    ARTIFACT = "artifact"
    ERROR = "error"


@dataclass(frozen=True)
class ParsedResponse:
    """Result of parsing an LLM raw response into typed signals."""

    response_type: ParsedResponseType
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    reason: str = ""  # for veto
    artifact_path: str = ""  # for artifact
    artifact_content: str = ""  # for artifact
    artifact_type: str = "code"  # for artifact
    parse_success: bool = True
    parse_error: str = ""  # if parse_success is False


# ---------------------------------------------------------------------------
# Regex for fenced code blocks
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(\w+)?\s*\n([\s\S]*?)\n```")

# Language tag -> artifact_type mapping
_LANG_ARTIFACT_TYPE: dict[str, str] = {
    "python": "code",
    "py": "code",
    "json": "config",
    "yaml": "config",
    "yml": "config",
    "toml": "config",
    "md": "doc",
    "rst": "doc",
    "txt": "doc",
}


class ResponseParser:
    """Parses raw LLM responses into typed ParsedResponse objects."""

    def __init__(self, kanban: StateKanban | None = None) -> None:
        """
        Args:
            kanban: Optional StateKanban for injecting ErrorSignal on parse failure.
        """
        self._kanban = kanban

    def parse(
        self,
        raw_response: LLMResponse,
        author_role: str,
        round_number: int,
    ) -> list[ParsedResponse]:
        """Parse a raw LLM response into typed signals.

        Args:
            raw_response: The raw LLM response.
            author_role: Role that produced this response.
            round_number: Current round number.

        Returns:
            List of ParsedResponse objects. On complete parse failure,
            returns a single ERROR-typed ParsedResponse.
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
        error_resp = self._make_error_response(
            content,
            author_role,
            round_number,
            "Response is not structured JSON or code block",
        )

        # Inject ErrorSignal into FluidZone if kanban is available
        if self._kanban is not None:
            self._inject_parse_error(error_resp, round_number)

        return [error_resp]

    def _try_structured_json(
        self, content: str, author_role: str, round_number: int
    ) -> list[ParsedResponse] | None:
        """Attempt to parse content as structured JSON.

        Returns None if content is not valid JSON or does not match
        the expected schema.
        """
        content_stripped = content.strip()
        if not content_stripped:
            return None

        try:
            data = json.loads(content_stripped)
        except (json.JSONDecodeError, ValueError):
            return None

        # Support both single object and list of objects
        items: list[dict[str, Any]]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            return None

        results: list[ParsedResponse] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            parsed = self._parse_structured_item(item, author_role, round_number)
            if parsed is not None:
                results.append(parsed)

        return results if results else None

    def _parse_structured_item(
        self,
        item: dict[str, Any],
        author_role: str,
        round_number: int,
    ) -> ParsedResponse | None:
        """Parse a single structured JSON item into a ParsedResponse."""
        resp_type_str = item.get("type", "")
        target_id = item.get("target_id", "task_root")
        payload = item.get("payload", {})

        try:
            resp_type = ParsedResponseType(resp_type_str)
        except ValueError:
            return None

        if resp_type == ParsedResponseType.INTENT:
            return ParsedResponse(
                response_type=ParsedResponseType.INTENT,
                target_id=target_id,
                payload=payload,
            )
        elif resp_type == ParsedResponseType.VETO:
            return ParsedResponse(
                response_type=ParsedResponseType.VETO,
                target_id=target_id,
                payload=payload,
                reason=item.get("reason", ""),
            )
        elif resp_type == ParsedResponseType.ARTIFACT:
            return ParsedResponse(
                response_type=ParsedResponseType.ARTIFACT,
                target_id=target_id,
                payload=payload,
                artifact_path=item.get("artifact_path", ""),
                artifact_content=item.get("artifact_content", ""),
                artifact_type=item.get("artifact_type", "code"),
            )
        else:
            return None

    def _try_code_block(
        self, content: str, author_role: str, round_number: int
    ) -> list[ParsedResponse] | None:
        """Attempt to extract code from fenced code blocks.

        Returns None if no fenced code blocks found.
        """
        match = _CODE_BLOCK_RE.search(content)
        if match is None:
            return None

        lang_tag = match.group(1) or ""
        code_content = match.group(2)

        artifact_type = _LANG_ARTIFACT_TYPE.get(lang_tag.lower(), "code")

        return [
            ParsedResponse(
                response_type=ParsedResponseType.ARTIFACT,
                target_id="codex_output",
                payload={"language": lang_tag, "author_role": author_role},
                artifact_content=code_content,
                artifact_type=artifact_type,
            )
        ]

    def _make_error_response(
        self,
        content: str,
        author_role: str,
        round_number: int,
        error_msg: str,
    ) -> ParsedResponse:
        """Create an ERROR-typed ParsedResponse for parse failures."""
        return ParsedResponse(
            response_type=ParsedResponseType.ERROR,
            target_id="parse_failure",
            payload={"raw_content_preview": content[:200]},
            parse_success=False,
            parse_error=error_msg,
        )

    def _inject_parse_error(
        self,
        error_resp: ParsedResponse,
        round_number: int,
    ) -> None:
        """Inject an ErrorSignal into FluidZone for parse failures."""
        if self._kanban is None:
            return
        error_signal = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="ResponseParser",
            target_id="parse_failure",
            payload=error_resp.payload,
            timestamp=now_utc(),
            round_number=round_number,
            error_code="SK_EN_003",
            error_detail=error_resp.parse_error,
        )
        try:
            self._kanban.fluid.write_signal(error_signal)
        except Exception:
            # Never crash the kernel -- swallow error signal injection failures
            pass

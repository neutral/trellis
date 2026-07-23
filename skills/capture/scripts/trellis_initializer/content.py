"""Pure Trellis handbook-content planning functions."""

from __future__ import annotations

from pathlib import Path

from .constants import (
    FORMAT_MARKER,
    HANDBOOK_BLOCK,
    HANDBOOK_END,
    HANDBOOK_START,
    NEW_OVERVIEW,
)
from .errors import ErrorCode, SupportError
from .models import FileState


def decode_utf8(path: Path, content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SupportError(
            f"expected UTF-8 text at {path.name}", code=ErrorCode.CONFLICT
        ) from exc


def newline_for(content: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in content else b"\n"


def encode_with_newline(text: str, newline: bytes) -> bytes:
    return text.replace("\n", newline.decode("ascii")).encode("utf-8")


def append_block_verbatim(current: bytes, block: str) -> bytes:
    newline = newline_for(current)
    encoded = encode_with_newline(block, newline)
    if not current:
        return encoded + newline
    if current.endswith(newline + newline):
        separator = b""
    elif current.endswith(newline):
        separator = newline
    else:
        separator = newline + newline
    return current + separator + encoded + newline


def validate_handbook_block(path: Path, text: str) -> None:
    del path
    starts = text.count(HANDBOOK_START)
    ends = text.count(HANDBOOK_END)
    if starts != 1 or ends != 1:
        raise SupportError(
            "existing handbook must contain either no Trellis handbook markers or "
            f"exactly one pair; found {starts} start and {ends} end",
            code=ErrorCode.CONFLICT,
        )
    start = text.index(HANDBOOK_START)
    end = text.index(HANDBOOK_END)
    if start > end:
        raise SupportError(
            "the Trellis handbook end marker precedes its start marker",
            code=ErrorCode.CONFLICT,
        )
    block = text[start : end + len(HANDBOOK_END)]
    if block.count(FORMAT_MARKER) != 1:
        raise SupportError(
            f"the managed handbook block must contain exactly one {FORMAT_MARKER!r}",
            code=ErrorCode.CONFLICT,
        )
    for heading in ("## Playbooks", "## Actions"):
        if block.count(heading) != 1:
            raise SupportError(
                "the managed handbook block must contain exactly one "
                f"{heading!r} heading",
                code=ErrorCode.CONFLICT,
            )


def planned_overview(path: Path, before: FileState) -> bytes | None:
    if not before.exists:
        return NEW_OVERVIEW.encode("utf-8")
    assert before.content is not None
    current = before.content
    text = decode_utf8(path, current)
    starts = text.count(HANDBOOK_START)
    ends = text.count(HANDBOOK_END)
    if starts == 0 and ends == 0:
        return append_block_verbatim(current, HANDBOOK_BLOCK)
    validate_handbook_block(path, text)
    return None


def planned_policy_file(path: Path, before: FileState, expected: str) -> bytes | None:
    if not before.exists:
        return expected.encode("utf-8")
    assert before.content is not None
    current = before.content
    if current != expected.encode("utf-8"):
        raise SupportError(
            f"refusing to overwrite a conflicting Trellis scratch policy: {path.name}",
            code=ErrorCode.CONFLICT,
        )
    return None

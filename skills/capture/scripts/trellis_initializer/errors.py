"""Stable initializer diagnostics."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-stable categories behind user-facing errors."""

    UNSAFE_PATH = "unsafe_path"
    DRIFT = "drift"
    CONFLICT = "conflict"
    FILESYSTEM = "filesystem"
    JOURNAL = "journal"
    TRANSITION = "transition"
    ROLLBACK = "rollback"
    UNSUPPORTED = "unsupported"


ERROR_CATALOG: dict[ErrorCode, str] = {
    ErrorCode.UNSAFE_PATH: "a local path is outside the closed capability",
    ErrorCode.DRIFT: "a captured local identity or state changed",
    ErrorCode.CONFLICT: "owner-managed state conflicts with the requested change",
    ErrorCode.FILESYSTEM: "an approved local filesystem operation failed",
    ErrorCode.JOURNAL: "restart metadata is missing, invalid, or unsafe",
    ErrorCode.TRANSITION: "the transaction state machine rejected a transition",
    ErrorCode.ROLLBACK: "rollback or private cleanup was incomplete",
    ErrorCode.UNSUPPORTED: "the runtime lacks a required safety capability",
}


class SupportError(Exception):
    """A catalog-coded, bounded diagnostic with no inspected owner content."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.FILESYSTEM,
    ) -> None:
        if code not in ERROR_CATALOG:
            raise ValueError("unknown initializer diagnostic code")
        unsafe = any(ord(char) < 32 for char in message)
        if not message or len(message) > 2048 or unsafe:
            raise ValueError("initializer diagnostic text is not a safe bounded value")
        super().__init__(message)
        self.code = code
        self.catalog_meaning = ERROR_CATALOG[code]


def stale_journal_error() -> SupportError:
    return SupportError(
        "unfinished initializer transaction found; rerun with --recover to "
        "preview recovery",
        code=ErrorCode.JOURNAL,
    )

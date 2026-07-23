"""Strict metadata-only durable transaction journal."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import (
    JOURNAL_RELATIVE,
    JOURNAL_SCHEMA,
    MANAGED_FILES,
    RECOVERY_TEMP_MARKER,
    STAGE_TEMP_MARKER,
)
from .errors import ErrorCode, SupportError
from .filesystem import (
    FileOperation,
    ReadRoot,
    capture_path_identity,
    identity_from_stat,
    read_verified_bytes,
    require_same_identity,
    require_supported_regular_metadata,
)
from .models import FileOwner, PathIdentity
from .phases import (
    ENTRY_TRANSITIONS,
    TRANSACTION_TRANSITIONS,
    EntryPhase,
    RecoveryActionKind,
    TransactionPhase,
)

MAX_JOURNAL_BYTES = 4 * 1024 * 1024
INCOMPLETE_INITIAL_JOURNAL = "transaction journal has no complete record"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate transaction journal key")
        result[key] = value
    return result


def _reject_nonstandard_number(_value: str) -> None:
    raise ValueError("non-standard transaction journal number")


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class JournalArtifact:
    relative: Path
    digest: str
    identity: PathIdentity | None


@dataclass(frozen=True)
class JournalEntry:
    relative: Path
    before_exists: bool
    before_digest: str | None
    before_mode: int | None
    before_owner: FileOwner | None
    before_identity: PathIdentity | None
    after_digest: str
    after_mode: int | None
    stage: JournalArtifact
    recovery: JournalArtifact | None
    applied_identity: PathIdentity | None
    phase: EntryPhase


@dataclass(frozen=True)
class JournalDirectory:
    relative: Path
    identity: PathIdentity | None


@dataclass(frozen=True)
class JournalRecoveryAction:
    kind: RecoveryActionKind
    relative: Path
    identity: PathIdentity | None


@dataclass(frozen=True)
class JournalRecord:
    sequence: int
    target_identity: PathIdentity
    backend_posture: str
    phase: TransactionPhase
    entries: tuple[JournalEntry, ...]
    created_directories: tuple[JournalDirectory, ...]
    recovery_actions: tuple[JournalRecoveryAction, ...]


def _identity_json(identity: PathIdentity | None) -> dict[str, int] | None:
    if identity is None:
        return None
    return {
        "device": identity.device,
        "inode": identity.inode,
        "file_type": identity.file_type,
    }


def _artifact_json(artifact: JournalArtifact | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return {
        "relative": artifact.relative.as_posix(),
        "digest": artifact.digest,
        "identity": _identity_json(artifact.identity),
    }


def _owner_json(owner: FileOwner | None) -> dict[str, int] | None:
    if owner is None:
        return None
    return {"user": owner.user, "group": owner.group}


def record_json(record: JournalRecord) -> dict[str, Any]:
    return {
        "schema": JOURNAL_SCHEMA,
        "sequence": record.sequence,
        "target_identity": _identity_json(record.target_identity),
        "backend_posture": record.backend_posture,
        "phase": record.phase.value,
        "entries": [
            {
                "relative": entry.relative.as_posix(),
                "before_exists": entry.before_exists,
                "before_digest": entry.before_digest,
                "before_mode": entry.before_mode,
                "before_owner": _owner_json(entry.before_owner),
                "before_identity": _identity_json(entry.before_identity),
                "after_digest": entry.after_digest,
                "after_mode": entry.after_mode,
                "stage": _artifact_json(entry.stage),
                "recovery": _artifact_json(entry.recovery),
                "applied_identity": _identity_json(entry.applied_identity),
                "phase": entry.phase.value,
            }
            for entry in record.entries
        ],
        "created_directories": [
            {
                "relative": directory.relative.as_posix(),
                "identity": _identity_json(directory.identity),
            }
            for directory in record.created_directories
        ],
        "recovery_actions": [
            {
                "kind": action.kind.value,
                "relative": action.relative.as_posix(),
                "identity": _identity_json(action.identity),
            }
            for action in record.recovery_actions
        ],
    }


def encode_record(record: JournalRecord) -> bytes:
    return (
        json.dumps(record_json(record), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _object(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    return value


def _optional_mode(value: Any, label: str) -> int | None:
    if value is None:
        return None
    mode = _integer(value, label)
    if mode > 0o777:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    return mode


def _digest(value: Any, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or len(value) != 64:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        ) from exc
    return value


def _identity(value: Any, label: str, *, optional: bool) -> PathIdentity | None:
    if optional and value is None:
        return None
    item = _object(
        value, frozenset({"device", "inode", "file_type"}), f"{label} identity"
    )
    identity = PathIdentity(
        device=_integer(item["device"], f"{label} device"),
        inode=_integer(item["inode"], f"{label} inode", minimum=1),
        file_type=_integer(item["file_type"], f"{label} file type"),
    )
    if identity.file_type not in {stat.S_IFREG, stat.S_IFDIR}:
        raise SupportError(
            f"invalid transaction journal {label} file type",
            code=ErrorCode.JOURNAL,
        )
    return identity


def _owner(value: Any, label: str) -> FileOwner | None:
    if value is None:
        return None
    item = _object(value, frozenset({"user", "group"}), f"{label} owner")
    return FileOwner(
        user=_integer(item["user"], f"{label} owner user"),
        group=_integer(item["group"], f"{label} owner group"),
    )


def _relative(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != value:
        raise SupportError(
            f"invalid transaction journal {label}", code=ErrorCode.JOURNAL
        )
    return relative


def _artifact(
    value: Any,
    label: str,
    destination: Path,
    marker: str,
    *,
    optional: bool,
) -> JournalArtifact | None:
    if optional and value is None:
        return None
    item = _object(value, frozenset({"relative", "digest", "identity"}), label)
    relative = _relative(item["relative"], f"{label} path")
    expected_name = f".{destination.name}{marker}transaction"
    if relative.parent != destination.parent or relative.name != expected_name:
        raise SupportError(
            f"invalid transaction journal {label} path",
            code=ErrorCode.JOURNAL,
        )
    digest = _digest(item["digest"], f"{label} digest")
    assert digest is not None
    return JournalArtifact(
        relative=relative,
        digest=digest,
        identity=_identity(item["identity"], label, optional=True),
    )


def parse_record(value: Any) -> JournalRecord:
    root = _object(
        value,
        frozenset(
            {
                "schema",
                "sequence",
                "target_identity",
                "backend_posture",
                "phase",
                "entries",
                "created_directories",
                "recovery_actions",
            }
        ),
        "record",
    )
    if root["schema"] != JOURNAL_SCHEMA:
        raise SupportError(
            "unsupported transaction journal schema", code=ErrorCode.JOURNAL
        )
    if not isinstance(root["backend_posture"], str) or not root["backend_posture"]:
        raise SupportError(
            "invalid transaction journal backend posture", code=ErrorCode.JOURNAL
        )
    try:
        phase = TransactionPhase(root["phase"])
    except (TypeError, ValueError) as exc:
        raise SupportError(
            "invalid transaction journal phase", code=ErrorCode.JOURNAL
        ) from exc
    if not isinstance(root["entries"], list) or len(root["entries"]) > len(
        MANAGED_FILES
    ):
        raise SupportError(
            "invalid transaction journal entries", code=ErrorCode.JOURNAL
        )
    entries: list[JournalEntry] = []
    seen: set[Path] = set()
    entry_keys = frozenset(
        {
            "relative",
            "before_exists",
            "before_digest",
            "before_mode",
            "before_owner",
            "before_identity",
            "after_digest",
            "after_mode",
            "stage",
            "recovery",
            "applied_identity",
            "phase",
        }
    )
    for index, raw_entry in enumerate(root["entries"]):
        item = _object(raw_entry, entry_keys, f"entry {index}")
        relative = _relative(item["relative"], f"entry {index} path")
        if relative not in MANAGED_FILES or relative in seen:
            raise SupportError(
                "invalid transaction journal managed path", code=ErrorCode.JOURNAL
            )
        seen.add(relative)
        if not isinstance(item["before_exists"], bool):
            raise SupportError(
                "invalid transaction journal before state", code=ErrorCode.JOURNAL
            )
        try:
            entry_phase = EntryPhase(item["phase"])
        except (TypeError, ValueError) as exc:
            raise SupportError(
                "invalid transaction journal entry phase", code=ErrorCode.JOURNAL
            ) from exc
        before_exists = item["before_exists"]
        before_digest = _digest(
            item["before_digest"], f"entry {index} before digest", optional=True
        )
        before_identity = _identity(
            item["before_identity"], f"entry {index} before", optional=True
        )
        before_mode = _optional_mode(item["before_mode"], f"entry {index} before mode")
        before_owner = _owner(item["before_owner"], f"entry {index} before")
        if before_exists != (before_digest is not None and before_identity is not None):
            raise SupportError(
                "invalid transaction journal before state", code=ErrorCode.JOURNAL
            )
        if (
            (
                not before_exists
                and (before_mode is not None or before_owner is not None)
            )
            or (
                before_exists
                and os.name == "posix"
                and (before_mode is None or before_owner is None)
            )
            or (
                os.name != "posix"
                and (before_mode is not None or before_owner is not None)
            )
        ):
            raise SupportError(
                "invalid transaction journal before metadata",
                code=ErrorCode.JOURNAL,
            )
        after_digest = _digest(item["after_digest"], f"entry {index} after digest")
        assert after_digest is not None
        after_mode = _optional_mode(item["after_mode"], f"entry {index} after mode")
        if (os.name == "posix") != (after_mode is not None):
            raise SupportError(
                "invalid transaction journal after metadata",
                code=ErrorCode.JOURNAL,
            )
        stage = _artifact(
            item["stage"],
            f"entry {index} stage",
            relative,
            STAGE_TEMP_MARKER,
            optional=False,
        )
        assert stage is not None
        recovery = _artifact(
            item["recovery"],
            f"entry {index} recovery",
            relative,
            RECOVERY_TEMP_MARKER,
            optional=not before_exists,
        )
        if before_exists and recovery is None:
            raise SupportError(
                "invalid transaction journal recovery state", code=ErrorCode.JOURNAL
            )
        entries.append(
            JournalEntry(
                relative=relative,
                before_exists=before_exists,
                before_digest=before_digest,
                before_mode=before_mode,
                before_owner=before_owner,
                before_identity=before_identity,
                after_digest=after_digest,
                after_mode=after_mode,
                stage=stage,
                recovery=recovery,
                applied_identity=_identity(
                    item["applied_identity"],
                    f"entry {index} applied",
                    optional=True,
                ),
                phase=entry_phase,
            )
        )
    if (
        not isinstance(root["created_directories"], list)
        or len(root["created_directories"]) > 2
    ):
        raise SupportError(
            "invalid transaction journal directories", code=ErrorCode.JOURNAL
        )
    directories: list[JournalDirectory] = []
    seen_directories: set[Path] = set()
    for index, raw_directory in enumerate(root["created_directories"]):
        item = _object(
            raw_directory,
            frozenset({"relative", "identity"}),
            f"directory {index}",
        )
        relative = _relative(item["relative"], f"directory {index} path")
        if (
            relative not in {Path("_handbook"), Path("_handbook/_scratch")}
            or relative in seen_directories
        ):
            raise SupportError(
                "invalid transaction journal directory path", code=ErrorCode.JOURNAL
            )
        seen_directories.add(relative)
        identity = _identity(item["identity"], f"directory {index}", optional=True)
        if identity is not None and identity.file_type != stat.S_IFDIR:
            raise SupportError(
                "invalid transaction journal directory identity",
                code=ErrorCode.JOURNAL,
            )
        directories.append(JournalDirectory(relative, identity))
    if not isinstance(root["recovery_actions"], list) or len(
        root["recovery_actions"]
    ) > (len(entries) * 4) + len(directories):
        raise SupportError(
            "invalid transaction journal recovery actions",
            code=ErrorCode.JOURNAL,
        )
    entry_by_relative = {entry.relative: entry for entry in entries}
    stage_paths = {entry.stage.relative for entry in entries}
    recovery_paths = {
        entry.recovery.relative for entry in entries if entry.recovery is not None
    }
    directory_paths = {directory.relative for directory in directories}
    recovery_actions: list[JournalRecoveryAction] = []
    seen_actions: set[tuple[RecoveryActionKind, Path]] = set()
    for index, raw_action in enumerate(root["recovery_actions"]):
        item = _object(
            raw_action,
            frozenset({"kind", "relative", "identity"}),
            f"recovery action {index}",
        )
        try:
            kind = RecoveryActionKind(item["kind"])
        except (TypeError, ValueError) as exc:
            raise SupportError(
                "invalid transaction journal recovery action kind",
                code=ErrorCode.JOURNAL,
            ) from exc
        relative = _relative(item["relative"], f"recovery action {index} path")
        identity = _identity(
            item["identity"], f"recovery action {index}", optional=True
        )
        key = (kind, relative)
        if key in seen_actions:
            raise SupportError(
                "duplicate transaction journal recovery action",
                code=ErrorCode.JOURNAL,
            )
        seen_actions.add(key)
        valid = False
        if kind == RecoveryActionKind.RESTORE:
            entry = entry_by_relative.get(relative)
            valid = (
                entry is not None
                and entry.before_exists
                and identity is not None
                and identity.file_type == stat.S_IFREG
                and entry.recovery is not None
                and identity == entry.recovery.identity
            )
        elif kind == RecoveryActionKind.REMOVE_CREATED:
            entry = entry_by_relative.get(relative)
            valid = entry is not None and not entry.before_exists and identity is None
        elif kind == RecoveryActionKind.REMOVE_STAGE:
            valid = relative in stage_paths and identity is None
        elif kind == RecoveryActionKind.REMOVE_RECOVERY:
            valid = relative in recovery_paths and identity is None
        elif kind == RecoveryActionKind.REMOVE_DIRECTORY:
            valid = relative in directory_paths and identity is None
        if not valid:
            raise SupportError(
                "invalid transaction journal recovery action",
                code=ErrorCode.JOURNAL,
            )
        recovery_actions.append(JournalRecoveryAction(kind, relative, identity))
    target_identity = _identity(root["target_identity"], "target", optional=False)
    assert target_identity is not None
    if target_identity.file_type != stat.S_IFDIR:
        raise SupportError(
            "invalid transaction journal target identity", code=ErrorCode.JOURNAL
        )
    return JournalRecord(
        sequence=_integer(root["sequence"], "sequence"),
        target_identity=target_identity,
        backend_posture=root["backend_posture"],
        phase=phase,
        entries=tuple(entries),
        created_directories=tuple(directories),
        recovery_actions=tuple(recovery_actions),
    )


def _artifact_invariants(
    artifact: JournalArtifact | None,
) -> tuple[Path, str] | None:
    if artifact is None:
        return None
    return artifact.relative, artifact.digest


def _entry_invariants(entry: JournalEntry) -> tuple[Any, ...]:
    return (
        entry.relative,
        entry.before_exists,
        entry.before_digest,
        entry.before_mode,
        entry.before_owner,
        entry.before_identity,
        entry.after_digest,
        entry.after_mode,
        _artifact_invariants(entry.stage),
        _artifact_invariants(entry.recovery),
    )


def _identity_progressed(
    before: PathIdentity | None, after: PathIdentity | None
) -> bool:
    return before is None or before == after


def _artifact_identity_progressed(
    before: PathIdentity | None,
    after: PathIdentity | None,
    phase: EntryPhase,
    *,
    consumed_in: frozenset[EntryPhase],
) -> bool:
    return _identity_progressed(before, after) or (
        before is not None and after is None and phase in consumed_in
    )


def _require_record_progression(
    previous: JournalRecord, current: JournalRecord
) -> None:
    if (
        previous.target_identity != current.target_identity
        or previous.backend_posture != current.backend_posture
        or tuple(item.relative for item in previous.created_directories)
        != tuple(item.relative for item in current.created_directories)
        or len(previous.entries) != len(current.entries)
    ):
        raise SupportError(
            "transaction journal immutable metadata changed",
            code=ErrorCode.JOURNAL,
        )
    for directory_before, directory_after in zip(
        previous.created_directories,
        current.created_directories,
        strict=True,
    ):
        if not _identity_progressed(
            directory_before.identity,
            directory_after.identity,
        ):
            raise SupportError(
                "transaction journal directory identity changed",
                code=ErrorCode.JOURNAL,
            )
    if (
        current.phase != previous.phase
        and current.phase not in TRANSACTION_TRANSITIONS[previous.phase]
    ):
        raise SupportError(
            "transaction journal phase progression is invalid",
            code=ErrorCode.JOURNAL,
        )
    for before, after in zip(previous.entries, current.entries, strict=True):
        if _entry_invariants(before) != _entry_invariants(after):
            raise SupportError(
                "transaction journal entry metadata changed",
                code=ErrorCode.JOURNAL,
            )
        if (
            after.phase != before.phase
            and after.phase not in ENTRY_TRANSITIONS[before.phase]
        ):
            raise SupportError(
                "transaction journal entry progression is invalid",
                code=ErrorCode.JOURNAL,
            )
        if not _artifact_identity_progressed(
            before.stage.identity,
            after.stage.identity,
            after.phase,
            consumed_in=frozenset(
                {
                    EntryPhase.APPLIED,
                    EntryPhase.VERIFIED,
                    EntryPhase.CLEANED,
                    EntryPhase.ROLLING_BACK,
                    EntryPhase.ROLLED_BACK,
                    EntryPhase.INCOMPLETE,
                }
            ),
        ):
            raise SupportError(
                "transaction journal stage identity changed",
                code=ErrorCode.JOURNAL,
            )
        before_recovery = (
            before.recovery.identity if before.recovery is not None else None
        )
        after_recovery = after.recovery.identity if after.recovery is not None else None
        if not _artifact_identity_progressed(
            before_recovery,
            after_recovery,
            after.phase,
            consumed_in=frozenset(
                {
                    EntryPhase.CLEANED,
                    EntryPhase.ROLLED_BACK,
                    EntryPhase.INCOMPLETE,
                }
            ),
        ):
            raise SupportError(
                "transaction journal recovery identity changed",
                code=ErrorCode.JOURNAL,
            )
        if not _identity_progressed(before.applied_identity, after.applied_identity):
            raise SupportError(
                "transaction journal applied identity changed",
                code=ErrorCode.JOURNAL,
            )
    if current.recovery_actions[: len(previous.recovery_actions)] != (
        previous.recovery_actions
    ):
        raise SupportError(
            "transaction journal recovery progression is invalid",
            code=ErrorCode.JOURNAL,
        )
    if len(current.recovery_actions) > len(previous.recovery_actions) + 1:
        raise SupportError(
            "transaction journal recovery progression skipped an action",
            code=ErrorCode.JOURNAL,
        )


class JournalStore:
    """Append-only record store; a truncated final record is safely ignored."""

    def __init__(self, root: ReadRoot) -> None:
        self.root = root
        self.path = root.target / JOURNAL_RELATIVE
        self.identity: PathIdentity | None = None
        self.poisoned = False

    def create(self, record: JournalRecord) -> None:
        descriptor = -1
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = self.root.backend.open_file(
                self.path, flags, 0o600, FileOperation.CREATE_JOURNAL
            )
            self.identity = identity_from_stat(self.path, os.fstat(descriptor))
            self.root.backend.fchmod(descriptor, 0o600)
            require_supported_regular_metadata(
                self.path,
                os.fstat(descriptor),
                descriptor=descriptor,
            )
            payload = encode_record(record)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(payload)
                handle.flush()
                self.root.backend.fsync(handle.fileno(), FileOperation.SYNC_FILE)
            require_same_identity(
                self.path,
                self.identity,
                expected_type=stat.S_IFREG,
                description="transaction journal",
                backend=self.root.backend,
            )
            self.root.backend.sync_directory(self.path.parent)
        except FileExistsError as exc:
            raise SupportError(
                "unfinished initializer transaction already exists",
                code=ErrorCode.JOURNAL,
            ) from exc
        except BaseException as exc:
            self.poisoned = self.identity is not None
            if isinstance(exc, SupportError):
                raise
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise SupportError(
                "could not create transaction journal",
                code=ErrorCode.JOURNAL,
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def append(self, record: JournalRecord) -> None:
        if self.poisoned:
            raise SupportError(
                "transaction journal is poisoned after an append failure",
                code=ErrorCode.JOURNAL,
            )
        descriptor = -1
        try:
            if self.identity is None:
                self.identity = capture_path_identity(
                    self.path,
                    expected_type=stat.S_IFREG,
                    description="transaction journal",
                    backend=self.root.backend,
                )
            require_same_identity(
                self.path,
                self.identity,
                expected_type=stat.S_IFREG,
                description="transaction journal",
                backend=self.root.backend,
            )
            flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0)
            descriptor = self.root.backend.open_file(
                self.path, flags, 0o600, FileOperation.APPEND_JOURNAL
            )
            if identity_from_stat(self.path, os.fstat(descriptor)) != self.identity:
                raise SupportError(
                    "transaction journal identity changed",
                    code=ErrorCode.JOURNAL,
                )
            require_supported_regular_metadata(
                self.path,
                os.fstat(descriptor),
                descriptor=descriptor,
            )
            with os.fdopen(descriptor, "ab") as handle:
                descriptor = -1
                handle.write(encode_record(record))
                handle.flush()
                self.root.backend.fsync(handle.fileno(), FileOperation.SYNC_FILE)
            require_same_identity(
                self.path,
                self.identity,
                expected_type=stat.S_IFREG,
                description="transaction journal",
                backend=self.root.backend,
            )
        except BaseException as exc:
            self.poisoned = True
            if isinstance(exc, SupportError):
                raise
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise SupportError(
                "could not update transaction journal",
                code=ErrorCode.JOURNAL,
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def load(self) -> JournalRecord:
        identity = capture_path_identity(
            self.path,
            expected_type=stat.S_IFREG,
            description="transaction journal",
            backend=self.root.backend,
        )
        self.identity = identity
        descriptor = -1
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
            descriptor = self.root.backend.open_file(
                self.path, flags, 0o600, FileOperation.OPEN_READ
            )
            if identity_from_stat(self.path, os.fstat(descriptor)) != identity:
                raise SupportError(
                    "transaction journal changed before it was read",
                    code=ErrorCode.JOURNAL,
                )
            require_supported_regular_metadata(
                self.path,
                os.fstat(descriptor),
                descriptor=descriptor,
            )
            size = int(os.fstat(descriptor).st_size)
            if size > MAX_JOURNAL_BYTES:
                raise SupportError(
                    "transaction journal exceeds its size limit",
                    code=ErrorCode.JOURNAL,
                )
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                content = handle.read(MAX_JOURNAL_BYTES + 1)
        except OSError as exc:
            raise SupportError(
                "could not read transaction journal",
                code=ErrorCode.JOURNAL,
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if len(content) > MAX_JOURNAL_BYTES:
            raise SupportError(
                "transaction journal exceeds its size limit",
                code=ErrorCode.JOURNAL,
            )
        require_same_identity(
            self.path,
            identity,
            expected_type=stat.S_IFREG,
            description="transaction journal",
            backend=self.root.backend,
        )
        complete = content.splitlines(keepends=True)
        records: list[JournalRecord] = []
        previous_sequence = -1
        previous_record: JournalRecord | None = None
        for index, line in enumerate(complete):
            if not line.endswith(b"\n"):
                if index == len(complete) - 1:
                    break
                raise SupportError(
                    "transaction journal contains an incomplete record",
                    code=ErrorCode.JOURNAL,
                )
            try:
                raw = json.loads(
                    line.decode("utf-8"),
                    object_pairs_hook=_unique_object,
                    parse_constant=_reject_nonstandard_number,
                )
            except (UnicodeDecodeError, ValueError, RecursionError) as exc:
                raise SupportError(
                    "transaction journal contains invalid JSON",
                    code=ErrorCode.JOURNAL,
                ) from exc
            record = parse_record(raw)
            if record.sequence != previous_sequence + 1:
                raise SupportError(
                    "transaction journal sequence is invalid",
                    code=ErrorCode.JOURNAL,
                )
            if previous_record is None:
                if (
                    record.phase != TransactionPhase.JOURNALED
                    or record.recovery_actions
                ):
                    raise SupportError(
                        "transaction journal has an invalid initial phase",
                        code=ErrorCode.JOURNAL,
                    )
            else:
                _require_record_progression(previous_record, record)
            previous_sequence = record.sequence
            previous_record = record
            records.append(record)
        if not records:
            raise SupportError(
                INCOMPLETE_INITIAL_JOURNAL,
                code=ErrorCode.JOURNAL,
            )
        return records[-1]

    def matches_incomplete_initial(self, expected: bytes) -> bool:
        """Recognize only a truncated prefix of the exact initial record."""

        identity = capture_path_identity(
            self.path,
            expected_type=stat.S_IFREG,
            description="transaction journal",
            backend=self.root.backend,
        )
        self.identity = identity
        content = read_verified_bytes(
            self.path,
            identity,
            limit=MAX_JOURNAL_BYTES,
            backend=self.root.backend,
        )
        return not content.endswith(b"\n") and expected.startswith(content)

    def remove(self) -> None:
        if self.identity is None:
            self.identity = capture_path_identity(
                self.path,
                expected_type=stat.S_IFREG,
                description="transaction journal",
                backend=self.root.backend,
            )
        require_same_identity(
            self.path,
            self.identity,
            expected_type=stat.S_IFREG,
            description="transaction journal",
            backend=self.root.backend,
        )
        read_verified_bytes(
            self.path,
            self.identity,
            limit=MAX_JOURNAL_BYTES,
            backend=self.root.backend,
        )
        self.root.backend.unlink(self.path, FileOperation.REMOVE_JOURNAL)
        self.root.backend.sync_directory(self.path.parent)

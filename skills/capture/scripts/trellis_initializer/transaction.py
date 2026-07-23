"""State-checked write transaction and restart recovery."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from .constants import (
    MANAGED_FILES,
    RECOVERY_TEMP_MARKER,
    STAGE_TEMP_MARKER,
    TRANSACTION_TEMP_MARKERS,
)
from .errors import ErrorCode, SupportError
from .filesystem import (
    MAX_MANAGED_FILE_BYTES,
    FileOperation,
    FileSystemBackend,
    ReadRoot,
    capture_file_state,
    capture_parent_identities,
    capture_path_identity,
    default_backend,
    identity_from_stat,
    owner_from_stat,
    read_verified_bytes,
    reject_symlinks,
    require_parent_identities,
    require_same_identity,
)
from .journal import (
    INCOMPLETE_INITIAL_JOURNAL,
    JournalArtifact,
    JournalDirectory,
    JournalEntry,
    JournalRecord,
    JournalRecoveryAction,
    JournalStore,
    content_digest,
    encode_record,
)
from .models import (
    FileState,
    OwnedDirectory,
    PathIdentity,
    Plan,
    PlanEntry,
    PreparedEntry,
)
from .phases import (
    EntryPhase,
    RecoveryActionKind,
    TransactionPhase,
    require_entry_transition,
    require_transaction_transition,
)
from .planner import (
    build_immutable_plan,
    require_replaceable_metadata,
    revalidate_entry,
)

PrepareHook = Callable[[PreparedEntry], None]
RevalidateHook = Callable[[Path, PlanEntry], None]
DirectoryCreatedHook = Callable[[OwnedDirectory], None]


def _managed_parent_relatives(
    plan: list[PlanEntry] | tuple[PlanEntry, ...],
) -> tuple[Path, ...]:
    relatives: set[Path] = set()
    for entry in plan:
        parts = entry.relative.parent.parts
        for length in range(1, len(parts) + 1):
            relatives.add(Path(*parts[:length]))
    return tuple(sorted(relatives, key=lambda item: (len(item.parts), item.parts)))


def plan_parent_directories(
    target: Path,
    plan: list[PlanEntry] | tuple[PlanEntry, ...],
    backend: FileSystemBackend | None = None,
) -> list[OwnedDirectory]:
    """Read-only capture of missing parents before the journal is created."""

    selected = backend or default_backend()
    missing: list[OwnedDirectory] = []
    for relative in _managed_parent_relatives(plan):
        reject_symlinks(target, relative, selected, allow_transaction_path=True)
        path = target / relative
        try:
            result = selected.inspect_path(path)
        except FileNotFoundError:
            missing.append(OwnedDirectory(path=path, relative=relative))
            continue
        if identity_from_stat(path, result).file_type != stat.S_IFDIR:
            raise SupportError(
                f"managed support parent is not a directory: {relative.as_posix()}",
                code=ErrorCode.UNSAFE_PATH,
            )
    return missing


def ensure_parent_directories(
    target: Path,
    plan: list[PlanEntry] | tuple[PlanEntry, ...],
    created: list[OwnedDirectory] | None = None,
    backend: FileSystemBackend | None = None,
    on_created: DirectoryCreatedHook | None = None,
) -> list[OwnedDirectory]:
    """Create predeclared missing parents and identity-record each one."""

    selected = backend or default_backend()
    if created is None:
        created = plan_parent_directories(target, plan, selected)
    elif not created:
        created.extend(plan_parent_directories(target, plan, selected))
    planned = {item.relative: item for item in created}
    for relative in _managed_parent_relatives(plan):
        reject_symlinks(target, relative, selected, allow_transaction_path=True)
        owned = planned.get(relative)
        path = target / relative
        try:
            result = selected.inspect_path(path)
        except FileNotFoundError:
            result = None
        if result is not None:
            identity = identity_from_stat(path, result)
            if identity.file_type != stat.S_IFDIR:
                raise SupportError(
                    f"managed support parent is not a directory: {relative.as_posix()}",
                    code=ErrorCode.UNSAFE_PATH,
                )
            if owned is not None and owned.identity is None:
                raise SupportError(
                    f"managed directory appeared after planning: {relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            continue
        if owned is None:
            raise SupportError(
                f"managed directory disappeared after planning: {relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )
        try:
            mode = 0o700 if path.name == "_scratch" else 0o777
            selected.mkdir(path, mode)
            owned.identity = capture_path_identity(
                path,
                expected_type=stat.S_IFDIR,
                description=f"created directory {relative.as_posix()}",
                backend=selected,
            )
            if path.name == "_scratch" and os.name == "posix":
                chmod_owned_path(
                    path,
                    owned.identity,
                    0o700,
                    expected_type=stat.S_IFDIR,
                    description=f"created directory {relative.as_posix()}",
                    backend=selected,
                )
            if on_created is not None:
                on_created(owned)
        except OSError as exc:
            raise SupportError(
                f"could not create managed directory {relative.as_posix()}",
                code=ErrorCode.FILESYSTEM,
            ) from exc
    return created


def chmod_owned_path(
    path: Path,
    identity: PathIdentity,
    mode: int,
    *,
    expected_type: int,
    description: str,
    backend: FileSystemBackend | None = None,
) -> None:
    selected = backend or default_backend()
    require_same_identity(
        path,
        identity,
        expected_type=expected_type,
        description=description,
        backend=selected,
    )
    selected.chmod(path, mode, identity)
    require_same_identity(
        path,
        identity,
        expected_type=expected_type,
        description=description,
        backend=selected,
    )


def _artifact_path(entry: PlanEntry, marker: str) -> Path:
    return entry.path.with_name(f".{entry.path.name}{marker}transaction")


def set_artifact_path(item: PreparedEntry, marker: str, path: Path) -> None:
    if marker == STAGE_TEMP_MARKER:
        item.staged = path
        item.staged_identity = None
    elif marker == RECOVERY_TEMP_MARKER:
        item.recovery = path
        item.recovery_identity = None
    else:
        raise SupportError(
            f"unknown transaction temporary marker: {marker}",
            code=ErrorCode.TRANSITION,
        )


def set_artifact_identity(
    item: PreparedEntry, marker: str, identity: PathIdentity
) -> None:
    if marker == STAGE_TEMP_MARKER:
        item.staged_identity = identity
    elif marker == RECOVERY_TEMP_MARKER:
        item.recovery_identity = identity
    else:
        raise SupportError(
            f"unknown transaction temporary marker: {marker}",
            code=ErrorCode.TRANSITION,
        )


def _require_artifact_absent(path: Path, backend: FileSystemBackend) -> None:
    try:
        backend.inspect_path(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise SupportError(
            f"could not inspect transaction path {path.name}",
            code=ErrorCode.FILESYSTEM,
        ) from exc
    raise SupportError(
        f"transaction path already exists and will not be overwritten: {path.name}",
        code=ErrorCode.CONFLICT,
    )


def write_temporary(
    item: PreparedEntry,
    content: bytes,
    marker: str,
    backend: FileSystemBackend | None = None,
) -> None:
    """Flush one exclusive, tracked, owner-private same-directory artifact."""

    selected = backend or default_backend()
    if marker not in TRANSACTION_TEMP_MARKERS:
        raise SupportError(
            f"unknown transaction temporary marker: {marker}",
            code=ErrorCode.TRANSITION,
        )
    require_parent_identities(item.parent_identities, selected)
    path, existing_identity = artifact_values(item, marker)
    if path is None:
        path = _artifact_path(item.plan, marker)
        set_artifact_path(item, marker, path)
    if existing_identity is not None:
        raise SupportError(
            "transaction temporary was already created",
            code=ErrorCode.TRANSITION,
        )
    identity = selected.create_private_file(path, content)
    set_artifact_identity(item, marker, identity)
    require_parent_identities(item.parent_identities, selected)
    selected.sync_directory(path.parent)


def planned_mode(entry: PlanEntry) -> int | None:
    if os.name != "posix":
        return None
    if not entry.before.exists:
        return 0o644
    if entry.before.mode is None:
        raise SupportError(
            f"missing original mode for {entry.relative.as_posix()}",
            code=ErrorCode.CONFLICT,
        )
    return entry.before.mode


def prepare_entry(
    item: PreparedEntry, backend: FileSystemBackend | None = None
) -> None:
    selected = backend or default_backend()
    entry = item.plan
    planned_mode(entry)
    if entry.before.exists:
        if entry.before.content is None:
            raise SupportError(
                f"missing original bytes for {entry.relative.as_posix()}",
                code=ErrorCode.CONFLICT,
            )
        write_temporary(item, entry.before.content, RECOVERY_TEMP_MARKER, selected)
        assert item.recovery is not None
        recovery_result = selected.inspect_path(item.recovery)
        if identity_from_stat(item.recovery, recovery_result) != item.recovery_identity:
            raise SupportError(
                "recovery artifact identity changed during preparation",
                code=ErrorCode.DRIFT,
            )
        if owner_from_stat(recovery_result) != entry.before.owner:
            raise SupportError(
                f"cannot preserve managed file ownership: {entry.relative.as_posix()}",
                code=ErrorCode.UNSUPPORTED,
            )
        item.phase = EntryPhase.RECOVERY_READY.value
    write_temporary(item, entry.after, STAGE_TEMP_MARKER, selected)
    item.phase = EntryPhase.STAGE_READY.value


def after_state(entry: PlanEntry) -> FileState:
    return FileState(
        exists=True,
        content=entry.after,
        mode=planned_mode(entry),
        owner=entry.before.owner if entry.before.exists else None,
    )


def is_applied_state(entry: PlanEntry, current: FileState) -> bool:
    expected = after_state(entry)
    return (
        current.exists
        and current.content == expected.content
        and current.mode in {0o600, expected.mode}
        and (not entry.before.exists or current.owner == entry.before.owner)
    )


def artifact_values(
    item: PreparedEntry, marker: str
) -> tuple[Path | None, PathIdentity | None]:
    if marker == STAGE_TEMP_MARKER:
        return item.staged, item.staged_identity
    if marker == RECOVERY_TEMP_MARKER:
        return item.recovery, item.recovery_identity
    raise SupportError(
        f"unknown transaction temporary marker: {marker}",
        code=ErrorCode.TRANSITION,
    )


def clear_artifact(item: PreparedEntry, marker: str) -> None:
    if marker == STAGE_TEMP_MARKER:
        item.staged = None
        item.staged_identity = None
    elif marker == RECOVERY_TEMP_MARKER:
        item.recovery = None
        item.recovery_identity = None
    else:
        raise SupportError(
            f"unknown transaction temporary marker: {marker}",
            code=ErrorCode.TRANSITION,
        )


def artifact_label(path: Path, target: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.name


def inspect_artifact(
    item: PreparedEntry,
    marker: str,
    target: Path,
    backend: FileSystemBackend | None = None,
) -> tuple[Path, PathIdentity] | str | None:
    selected = backend or default_backend()
    path, expected = artifact_values(item, marker)
    if path is None:
        return None
    label = artifact_label(path, target)
    try:
        require_parent_identities(item.parent_identities, selected)
    except SupportError as exc:
        return f"{label} ({exc}; transaction material was not accessed)"
    try:
        selected.inspect_path(path)
    except FileNotFoundError:
        clear_artifact(item, marker)
        return None
    except OSError:
        return f"{label} (could not verify transaction material)"
    if expected is None:
        return f"{label} (ownership was not recorded; not removed)"
    try:
        current = capture_path_identity(
            path,
            expected_type=stat.S_IFREG,
            description="transaction artifact",
            backend=selected,
        )
    except SupportError:
        return f"{label} (identity changed; not removed)"
    if current != expected or current.file_type != stat.S_IFREG:
        return f"{label} (identity changed; not removed)"
    return path, expected


def remove_owned_artifact(
    item: PreparedEntry,
    marker: str,
    target: Path,
    backend: FileSystemBackend | None = None,
) -> list[str]:
    selected = backend or default_backend()
    inspected = inspect_artifact(item, marker, target, selected)
    if inspected is None:
        return []
    if isinstance(inspected, str):
        return [inspected]
    path, expected = inspected
    expected_content = (
        item.plan.after if marker == STAGE_TEMP_MARKER else item.plan.before.content
    )
    if expected_content is None:
        return [
            f"{artifact_label(path, target)} (expected artifact bytes unavailable; "
            "not removed)"
        ]
    try:
        content = read_verified_bytes(
            path,
            expected,
            limit=MAX_MANAGED_FILE_BYTES,
            backend=selected,
        )
        if content_digest(content) != content_digest(expected_content):
            return [f"{artifact_label(path, target)} (content changed; not removed)"]
        selected.unlink(path, FileOperation.REMOVE_ARTIFACT)
        selected.sync_directory(path.parent)
    except (OSError, SupportError, KeyboardInterrupt) as exc:
        label = artifact_label(path, target)
        try:
            result = selected.inspect_path(path)
        except FileNotFoundError:
            clear_artifact(item, marker)
            return []
        except OSError:
            return [f"{label} (cleanup failed; recheck failed)"]
        try:
            current = identity_from_stat(path, result)
        except SupportError as inspect_exc:
            return [f"{label} (cleanup failed; {inspect_exc})"]
        if current != expected:
            return [f"{label} (identity changed during cleanup; not removed)"]
        return [f"{label} ({describe_failure(exc)}; retained residue)"]
    clear_artifact(item, marker)
    return []


def chmod_artifact_for_replace(
    item: PreparedEntry,
    marker: str,
    target: Path,
    backend: FileSystemBackend | None = None,
) -> tuple[Path, PathIdentity]:
    selected = backend or default_backend()
    inspected = inspect_artifact(item, marker, target, selected)
    if inspected is None:
        raise SupportError("transaction temporary is unavailable", code=ErrorCode.DRIFT)
    if isinstance(inspected, str):
        raise SupportError(inspected, code=ErrorCode.DRIFT)
    path, identity = inspected
    require_parent_identities(item.parent_identities, selected)
    require_same_identity(
        path,
        identity,
        expected_type=stat.S_IFREG,
        description=f"transaction temporary {path.name}",
        backend=selected,
    )
    return path, identity


def replace_artifact(
    item: PreparedEntry,
    marker: str,
    mode: int | None,
    target: Path,
    backend: FileSystemBackend | None = None,
) -> PathIdentity:
    selected = backend or default_backend()
    source, identity = chmod_artifact_for_replace(item, marker, target, selected)
    operation = (
        FileOperation.REPLACE_MANAGED
        if marker == STAGE_TEMP_MARKER
        else FileOperation.RESTORE_MANAGED
    )
    # This is the last operation before the destructive replacement. Earlier
    # planning and journal syncs are intentionally not trusted as a lock.
    if marker == STAGE_TEMP_MARKER:
        revalidate_entry(target, item.plan, selected)
    else:
        current = capture_file_state(target, item.plan.relative, selected)
        if (
            not is_applied_state(item.plan, current)
            or current.identity != item.applied_identity
        ):
            raise SupportError(
                f"managed file changed before restoration: "
                f"{item.plan.relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )
    if item.plan.before.exists:
        artifact_result = selected.inspect_path(source)
        if (
            identity_from_stat(source, artifact_result) != identity
            or owner_from_stat(artifact_result) != item.plan.before.owner
        ):
            raise SupportError(
                f"transaction artifact cannot preserve ownership: "
                f"{item.plan.relative.as_posix()}",
                code=ErrorCode.UNSUPPORTED,
            )
    expected_content = (
        item.plan.after if marker == STAGE_TEMP_MARKER else item.plan.before.content
    )
    if expected_content is None:
        raise SupportError(
            "recovery bytes are unavailable",
            code=ErrorCode.CONFLICT,
        )
    # This identity-checked digest read is deliberately the final operation
    # before replacement consumes the artifact.
    artifact_content = read_verified_bytes(
        source,
        identity,
        limit=MAX_MANAGED_FILE_BYTES,
        backend=selected,
    )
    if content_digest(artifact_content) != content_digest(expected_content):
        raise SupportError(
            "transaction artifact content changed before replacement",
            code=ErrorCode.DRIFT,
        )
    selected.replace(source, item.plan.path, operation)
    require_parent_identities(item.parent_identities, selected)
    require_same_identity(
        item.plan.path,
        identity,
        expected_type=stat.S_IFREG,
        description=f"managed file {item.plan.relative.as_posix()}",
        backend=selected,
    )
    if mode is not None:
        chmod_owned_path(
            item.plan.path,
            identity,
            mode,
            expected_type=stat.S_IFREG,
            description=f"managed file {item.plan.relative.as_posix()}",
            backend=selected,
        )
        require_parent_identities(item.parent_identities, selected)
    replaced = capture_file_state(target, item.plan.relative, selected)
    if marker == STAGE_TEMP_MARKER:
        exact = (
            is_applied_state(item.plan, replaced)
            and replaced.mode == planned_mode(item.plan)
            and replaced.identity == identity
        )
    else:
        exact = (
            replaced.content == item.plan.before.content
            and replaced.mode == item.plan.before.mode
            and replaced.owner == item.plan.before.owner
            and replaced.identity == identity
        )
    if not exact:
        raise SupportError(
            f"managed file did not exactly match the replacement state: "
            f"{item.plan.relative.as_posix()}",
            code=ErrorCode.DRIFT,
        )
    clear_artifact(item, marker)
    selected.sync_directory(item.plan.path.parent)
    return identity


def remove_applied_file(
    item: PreparedEntry,
    target: Path,
    backend: FileSystemBackend | None = None,
) -> list[str]:
    selected = backend or default_backend()
    entry = item.plan
    identity = item.applied_identity
    if identity is None:
        return [f"{entry.relative.as_posix()} (applied identity unavailable)"]
    try:
        require_parent_identities(item.parent_identities, selected)
        current = capture_file_state(target, entry.relative, selected)
        if not is_applied_state(entry, current) or current.identity != identity:
            return [
                f"{entry.relative.as_posix()} (changed before removal; not removed)"
            ]
        require_same_identity(
            entry.path,
            identity,
            expected_type=stat.S_IFREG,
            description=f"managed file {entry.relative.as_posix()}",
            backend=selected,
        )
        selected.unlink(entry.path, FileOperation.REMOVE_MANAGED)
        selected.sync_directory(entry.path.parent)
    except (OSError, SupportError) as exc:
        detail = (
            str(exc) if isinstance(exc, SupportError) else "filesystem operation failed"
        )
        return [f"{entry.relative.as_posix()} ({detail})"]
    return []


def _cleanup_owned_directories(
    created_directories: list[OwnedDirectory],
    backend: FileSystemBackend,
) -> list[str]:
    residues: list[str] = []
    for directory in reversed(created_directories):
        label = f"{directory.relative.as_posix()}/"
        if directory.identity is None:
            try:
                backend.inspect_path(directory.path)
            except FileNotFoundError:
                continue
            except OSError:
                residues.append(f"{label} (could not verify created directory)")
            else:
                residues.append(f"{label} (ownership was not recorded; not removed)")
            continue
        try:
            require_same_identity(
                directory.path,
                directory.identity,
                expected_type=stat.S_IFDIR,
                description=f"created directory {directory.relative.as_posix()}",
                backend=backend,
            )
            backend.rmdir(directory.path)
            backend.sync_directory(directory.path.parent)
        except FileNotFoundError:
            continue
        except (OSError, SupportError) as exc:
            detail = (
                str(exc)
                if isinstance(exc, SupportError)
                else "filesystem operation failed"
            )
            residues.append(f"{label} ({detail})")
    return residues


def rollback_transaction(
    prepared: list[PreparedEntry],
    created_directories: list[OwnedDirectory],
    target: Path,
    backend: FileSystemBackend | None = None,
) -> list[str]:
    """Best-effort rollback, retaining recovery bytes when restoration is unsafe."""

    selected = backend or default_backend()
    residues: list[str] = []
    for item in reversed(prepared):
        entry = item.plan
        retain_recovery = False
        if item.committed:
            current: FileState | None
            try:
                current = capture_file_state(target, entry.relative, selected)
            except SupportError as exc:
                residues.append(f"{entry.relative.as_posix()} ({exc})")
                current = None
                retain_recovery = entry.before.exists

            before_identity_matches = current is not None and (
                current.identity == entry.before.identity
            )
            applied_identity_matches = current is not None and (
                current.identity == item.applied_identity
            )
            if current == entry.before and before_identity_matches:
                item.committed = False
            elif (
                current is not None
                and is_applied_state(entry, current)
                and applied_identity_matches
            ):
                if entry.before.exists:
                    try:
                        replace_artifact(
                            item,
                            RECOVERY_TEMP_MARKER,
                            planned_mode(entry),
                            target,
                            selected,
                        )
                    except (OSError, SupportError) as exc:
                        detail = (
                            str(exc)
                            if isinstance(exc, SupportError)
                            else "filesystem operation failed"
                        )
                        residues.append(f"{entry.relative.as_posix()} ({detail})")
                        retain_recovery = item.recovery is not None
                else:
                    residues.extend(remove_applied_file(item, target, selected))
            elif current is not None:
                residues.append(
                    f"{entry.relative.as_posix()} (changed during rollback)"
                )
                retain_recovery = entry.before.exists

        residues.extend(
            remove_owned_artifact(item, STAGE_TEMP_MARKER, target, selected)
        )
        if retain_recovery:
            inspected = inspect_artifact(item, RECOVERY_TEMP_MARKER, target, selected)
            if isinstance(inspected, tuple):
                residues.append(artifact_label(inspected[0], target))
            elif isinstance(inspected, str):
                residues.append(inspected)
        else:
            residues.extend(
                remove_owned_artifact(item, RECOVERY_TEMP_MARKER, target, selected)
            )

    residues.extend(_cleanup_owned_directories(created_directories, selected))
    return list(dict.fromkeys(residues))


def describe_failure(exc: BaseException) -> str:
    if isinstance(exc, KeyboardInterrupt):
        return "operation interrupted"
    if isinstance(exc, SupportError):
        return str(exc)
    if isinstance(exc, OSError):
        return "local filesystem operation failed"
    return type(exc).__name__


def verify_applied_plan(
    prepared: list[PreparedEntry],
    target: Path,
    backend: FileSystemBackend | None = None,
) -> None:
    selected = backend or default_backend()
    for item in prepared:
        entry = item.plan
        require_parent_identities(item.parent_identities, selected)
        current = capture_file_state(target, entry.relative, selected)
        if (
            not is_applied_state(entry, current)
            or current.mode != planned_mode(entry)
            or current.identity != item.applied_identity
        ):
            raise SupportError(
                f"final state verification failed: {entry.relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )


def cleanup_recovery_copies(
    prepared: list[PreparedEntry],
    target: Path,
    backend: FileSystemBackend | None = None,
) -> list[str]:
    selected = backend or default_backend()
    residues: list[str] = []
    for item in prepared:
        residues.extend(
            remove_owned_artifact(item, RECOVERY_TEMP_MARKER, target, selected)
        )
    return residues


class WriteTransaction:
    """The only capability that may mutate initializer-managed paths."""

    def __init__(
        self,
        root: ReadRoot,
        plan: Plan,
        *,
        prepare_hook: PrepareHook | None = None,
        revalidate_hook: RevalidateHook | None = None,
    ) -> None:
        if plan.target != root.target or plan.target_identity != root.identity:
            raise SupportError(
                "write plan does not belong to this captured target",
                code=ErrorCode.DRIFT,
            )
        seen: set[Path] = set()
        for entry in plan.entries:
            if (
                entry.relative not in MANAGED_FILES
                or entry.relative in seen
                or entry.path != root.target / entry.relative
            ):
                raise SupportError(
                    "write plan contains a path outside the closed capability",
                    code=ErrorCode.UNSAFE_PATH,
                )
            require_replaceable_metadata(root, entry.relative, entry.before)
            seen.add(entry.relative)
        self.root = root
        self.plan = plan
        self.backend = root.backend
        self.prepare_hook = prepare_hook
        self.revalidate_hook = revalidate_hook
        self.phase = TransactionPhase.NEW
        self.sequence = -1
        self.created_directories: list[OwnedDirectory] = []
        self.prepared: list[PreparedEntry] = []
        self.journal = JournalStore(root)
        self.journal_created = False

    def _journal_record(self) -> JournalRecord:
        entries: list[JournalEntry] = []
        for item in self.prepared:
            before = item.plan.before
            stage_path = item.staged or _artifact_path(item.plan, STAGE_TEMP_MARKER)
            recovery_path = item.recovery or _artifact_path(
                item.plan, RECOVERY_TEMP_MARKER
            )
            stage = JournalArtifact(
                relative=stage_path.relative_to(self.root.target),
                digest=content_digest(item.plan.after),
                identity=item.staged_identity,
            )
            recovery = None
            if before.exists:
                assert before.content is not None
                recovery = JournalArtifact(
                    relative=recovery_path.relative_to(self.root.target),
                    digest=content_digest(before.content),
                    identity=item.recovery_identity,
                )
            entries.append(
                JournalEntry(
                    relative=item.plan.relative,
                    before_exists=before.exists,
                    before_digest=(
                        content_digest(before.content)
                        if before.content is not None
                        else None
                    ),
                    before_mode=before.mode,
                    before_owner=before.owner,
                    before_identity=before.identity,
                    after_digest=content_digest(item.plan.after),
                    after_mode=planned_mode(item.plan),
                    stage=stage,
                    recovery=recovery,
                    applied_identity=item.applied_identity,
                    phase=EntryPhase(item.phase),
                )
            )
        directories = tuple(
            JournalDirectory(item.relative, item.identity)
            for item in self.created_directories
        )
        return JournalRecord(
            sequence=self.sequence,
            target_identity=self.root.identity,
            backend_posture=self.backend.posture,
            phase=self.phase,
            entries=tuple(entries),
            created_directories=directories,
            recovery_actions=(),
        )

    def _create_journal(self) -> None:
        require_transaction_transition(self.phase, TransactionPhase.JOURNALED)
        self.phase = TransactionPhase.JOURNALED
        self.sequence = 0
        try:
            self.journal.create(self._journal_record())
        except BaseException:
            # create() captures an identity immediately after exclusive open.
            # If a later flush fails, rollback still owns and removes that
            # initial journal rather than leaving an untracked root artifact.
            self.journal_created = self.journal.identity is not None
            raise
        self.journal_created = True

    def _sync(self) -> None:
        self.sequence += 1
        self.journal.append(self._journal_record())

    def _transition(self, next_phase: TransactionPhase) -> None:
        require_transaction_transition(self.phase, next_phase)
        self.phase = next_phase
        self._sync()

    def _entry_transition(self, item: PreparedEntry, next_phase: EntryPhase) -> None:
        current = EntryPhase(item.phase)
        require_entry_transition(current, next_phase)
        item.phase = next_phase.value
        self._sync()

    def _initialize_entries(self) -> None:
        for entry in self.plan.entries:
            item = PreparedEntry(
                plan=entry,
                parent_identities=(),
                staged=_artifact_path(entry, STAGE_TEMP_MARKER),
                recovery=(
                    _artifact_path(entry, RECOVERY_TEMP_MARKER)
                    if entry.before.exists
                    else None
                ),
            )
            assert item.staged is not None
            _require_artifact_absent(item.staged, self.backend)
            if item.recovery is not None:
                _require_artifact_absent(item.recovery, self.backend)
            self.prepared.append(item)

    def _capture_entry_parents(self) -> None:
        for item in self.prepared:
            item.parent_identities = capture_parent_identities(
                self.root.target,
                item.plan.relative.parent,
                self.backend,
            )

    def run(self) -> None:
        if not self.plan.entries:
            print("No changes needed. Trellis handbook is already initialized.")
            return
        self.root.require_current()
        for entry in self.plan.entries:
            revalidate_entry(self.root.target, entry, self.backend)

        try:
            self._initialize_entries()
            self.created_directories = plan_parent_directories(
                self.root.target,
                self.plan.entries,
                self.backend,
            )
            self._create_journal()
            ensure_parent_directories(
                self.root.target,
                self.plan.entries,
                self.created_directories,
                self.backend,
                self._directory_created,
            )
            self._capture_entry_parents()
            self._transition(TransactionPhase.PREPARING)
            for item in self.prepared:
                if self.prepare_hook is None:
                    prepare_entry(item, self.backend)
                else:
                    self.prepare_hook(item)
                # Fault hooks run only after artifact names are reserved in the
                # durable record; identities are captured after each hook returns.
                item.phase = EntryPhase.STAGE_READY.value
                self._sync()
            self._transition(TransactionPhase.PREPARED)
            self._transition(TransactionPhase.APPLYING)

            for item in self.prepared:
                if self.revalidate_hook is None:
                    revalidate_entry(self.root.target, item.plan, self.backend)
                else:
                    self.revalidate_hook(self.root.target, item.plan)
                self._entry_transition(item, EntryPhase.APPLYING)
                item.committed = True
                if item.staged_identity is None:
                    raise SupportError(
                        "staged file identity is unavailable", code=ErrorCode.DRIFT
                    )
                item.applied_identity = item.staged_identity
                # Persist the identity and intent before replacement.
                self._sync()
                replace_artifact(
                    item,
                    STAGE_TEMP_MARKER,
                    planned_mode(item.plan),
                    self.root.target,
                    self.backend,
                )
                self._entry_transition(item, EntryPhase.APPLIED)

            self._transition(TransactionPhase.VERIFYING)
            verify_applied_plan(self.prepared, self.root.target, self.backend)
            for item in self.prepared:
                self._entry_transition(item, EntryPhase.VERIFIED)
            self._transition(TransactionPhase.COMMITTED)
        except BaseException as exc:
            self._rollback_and_raise(exc)

        self._finish_committed_cleanup()
        for entry in self.plan.entries:
            print(f"Wrote {entry.relative.as_posix()}")
        print("Trellis handbook initialized. No files were staged or committed.")

    def _directory_created(self, _directory: OwnedDirectory) -> None:
        # The initial journal contains every directory intent. Persist the
        # captured identity immediately after each exclusive mkdir.
        self._sync()

    def _rollback_and_raise(self, exc: BaseException) -> None:
        journal_failure: str | None = None
        if self.journal_created:
            try:
                if TransactionPhase.ROLLING_BACK in {
                    *self._allowed_transaction_transitions(),
                }:
                    self._transition(TransactionPhase.ROLLING_BACK)
                for item in self.prepared:
                    if EntryPhase.ROLLING_BACK in self._allowed_entry_transitions(item):
                        item.phase = EntryPhase.ROLLING_BACK.value
                self._sync()
            except BaseException as journal_exc:
                journal_failure = describe_failure(journal_exc)

        residues = rollback_transaction(
            self.prepared,
            self.created_directories,
            self.root.target,
            self.backend,
        )
        failure = describe_failure(exc)
        if journal_failure is not None:
            residues.append(f"transaction journal ({journal_failure})")
        if residues:
            try:
                if self.journal_created:
                    self.phase = TransactionPhase.INCOMPLETE
                    for item in self.prepared:
                        if item.phase == EntryPhase.ROLLING_BACK.value:
                            item.phase = EntryPhase.INCOMPLETE.value
                    self._sync()
            except BaseException:
                pass
            details = ", ".join(dict.fromkeys(residues))
            raise SupportError(
                f"transaction failed and rollback was incomplete: {failure}; "
                f"retained recovery or residue: {details}",
                code=ErrorCode.ROLLBACK,
            ) from exc

        if self.journal_created:
            try:
                self.phase = TransactionPhase.ROLLED_BACK
                for item in self.prepared:
                    item.phase = EntryPhase.ROLLED_BACK.value
                self._sync()
                # rollback_transaction already removed transaction-owned
                # directories. The journal is deliberately the final cleanup
                # effect so any earlier failure remains restart-visible.
                self.journal.remove()
                self.journal_created = False
            except BaseException as journal_exc:
                raise SupportError(
                    "transaction failed and file changes were rolled back, but the "
                    f"recovery journal was retained: {describe_failure(journal_exc)}",
                    code=ErrorCode.ROLLBACK,
                ) from exc
        raise SupportError(
            f"transaction failed and was fully rolled back: {failure}",
            code=ErrorCode.ROLLBACK,
        ) from exc

    def _allowed_transaction_transitions(self) -> frozenset[TransactionPhase]:
        from .phases import TRANSACTION_TRANSITIONS

        return TRANSACTION_TRANSITIONS[self.phase]

    @staticmethod
    def _allowed_entry_transitions(item: PreparedEntry) -> frozenset[EntryPhase]:
        from .phases import ENTRY_TRANSITIONS

        return ENTRY_TRANSITIONS[EntryPhase(item.phase)]

    def _finish_committed_cleanup(self) -> None:
        try:
            self._transition(TransactionPhase.CLEANING)
        except BaseException as exc:
            raise SupportError(
                "transaction committed and final state was verified, but private "
                f"recovery cleanup was incomplete; retained residue: "
                f"{self.root.journal_path.relative_to(self.root.target).as_posix()} "
                f"({describe_failure(exc)})",
                code=ErrorCode.ROLLBACK,
            ) from exc
        cleanup_residues: list[str] = []
        for item in self.prepared:
            cleanup_residues.extend(
                remove_owned_artifact(
                    item, RECOVERY_TEMP_MARKER, self.root.target, self.backend
                )
            )
            if not cleanup_residues:
                self._entry_transition(item, EntryPhase.CLEANED)
        if cleanup_residues:
            try:
                self._transition(TransactionPhase.INCOMPLETE)
            except BaseException:
                pass
            details = ", ".join(cleanup_residues)
            raise SupportError(
                "transaction committed and final state was verified, but private "
                f"recovery cleanup was incomplete; retained residue: {details}",
                code=ErrorCode.ROLLBACK,
            )
        self._transition(TransactionPhase.COMPLETE)
        try:
            self.journal.remove()
        except BaseException as exc:
            raise SupportError(
                "transaction committed and final state was verified, but private "
                f"recovery cleanup was incomplete; retained residue: "
                f"{self.root.journal_path.relative_to(self.root.target).as_posix()} "
                f"({describe_failure(exc)})",
                code=ErrorCode.ROLLBACK,
            ) from exc


@dataclass(frozen=True)
class RecoveryAction:
    kind: RecoveryActionKind
    relative: Path


def _journal_artifact_state(
    root: ReadRoot, artifact: JournalArtifact
) -> PathIdentity | None:
    path = root.target / artifact.relative
    reject_symlinks(
        root.target,
        artifact.relative,
        root.backend,
        allow_transaction_path=True,
    )
    try:
        root.backend.inspect_path(path)
    except FileNotFoundError:
        return None
    if artifact.identity is None:
        raise SupportError(
            f"recovery artifact identity was not durably recorded: "
            f"{artifact.relative.as_posix()}",
            code=ErrorCode.JOURNAL,
        )
    identity = capture_path_identity(
        path,
        expected_type=stat.S_IFREG,
        description=f"recovery artifact {artifact.relative.as_posix()}",
        backend=root.backend,
    )
    if identity != artifact.identity:
        raise SupportError(
            f"recovery artifact identity changed: {artifact.relative.as_posix()}",
            code=ErrorCode.DRIFT,
        )
    content = _read_artifact_bytes(root, path, identity)
    if content_digest(content) != artifact.digest:
        raise SupportError(
            f"recovery artifact content changed: {artifact.relative.as_posix()}",
            code=ErrorCode.DRIFT,
        )
    return identity


def _read_artifact_bytes(root: ReadRoot, path: Path, identity: PathIdentity) -> bytes:
    return read_verified_bytes(
        path, identity, limit=4 * 1024 * 1024, backend=root.backend
    )


def _state_digest(state: FileState) -> str | None:
    if not state.exists or state.content is None:
        return None
    return content_digest(state.content)


def _state_exists(state: FileState) -> bool:
    return state.exists


def _matches_before(state: FileState, entry: JournalEntry) -> bool:
    if not entry.before_exists:
        return not state.exists
    return (
        state.exists
        and _state_digest(state) == entry.before_digest
        and state.owner == entry.before_owner
        and state.identity == entry.before_identity
        and state.mode == entry.before_mode
    )


def _matches_after(state: FileState, entry: JournalEntry) -> bool:
    expected_identities = {
        identity
        for identity in (entry.applied_identity, entry.stage.identity)
        if identity is not None
    }
    return (
        state.exists
        and _state_digest(state) == entry.after_digest
        and state.mode in {0o600, entry.after_mode}
        and (not entry.before_exists or state.owner == entry.before_owner)
        and bool(expected_identities)
        and state.identity in expected_identities
    )


def _matches_restored(
    state: FileState,
    entry: JournalEntry,
    identity: PathIdentity | None = None,
    *,
    exact_mode: bool,
) -> bool:
    if not entry.before_exists or entry.recovery is None:
        return False
    expected_identities = {
        candidate
        for candidate in (entry.recovery.identity, identity)
        if candidate is not None
    }
    allowed_modes = {entry.before_mode}
    if not exact_mode:
        allowed_modes.add(0o600)
    return (
        state.exists
        and _state_digest(state) == entry.before_digest
        and state.owner == entry.before_owner
        and state.mode in allowed_modes
        and bool(expected_identities)
        and state.identity in expected_identities
    )


def _completed_actions(
    record: JournalRecord,
) -> dict[tuple[RecoveryActionKind, Path], JournalRecoveryAction]:
    return {
        (action.kind, action.relative): action for action in record.recovery_actions
    }


def _require_completed_action_state(
    root: ReadRoot,
    record: JournalRecord,
    states: dict[Path, FileState],
) -> None:
    for action in record.recovery_actions:
        if action.kind == RecoveryActionKind.RESTORE:
            entry = _entry_by_relative(record, action.relative)
            state = states[entry.relative]
            if action.identity is None or not _matches_restored(
                state, entry, action.identity, exact_mode=True
            ):
                raise SupportError(
                    f"restored managed file drifted: {entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
        elif action.kind == RecoveryActionKind.REMOVE_CREATED:
            if _state_exists(states[action.relative]):
                raise SupportError(
                    f"removed managed file reappeared: {action.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
        elif action.kind in {
            RecoveryActionKind.REMOVE_STAGE,
            RecoveryActionKind.REMOVE_RECOVERY,
        }:
            artifact = _artifact_by_relative(record, action.relative)
            if _journal_artifact_state(root, artifact) is not None:
                raise SupportError(
                    f"removed recovery artifact reappeared: "
                    f"{action.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
        elif action.kind == RecoveryActionKind.REMOVE_DIRECTORY:
            path = root.target / action.relative
            try:
                root.backend.inspect_path(path)
            except FileNotFoundError:
                continue
            raise SupportError(
                f"removed managed directory reappeared: {action.relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )


def _is_committed_record(record: JournalRecord, states: list[FileState]) -> bool:
    if record.phase in {
        TransactionPhase.COMMITTED,
        TransactionPhase.CLEANING,
        TransactionPhase.COMPLETE,
    }:
        return True
    if record.phase == TransactionPhase.INCOMPLETE:
        return all(
            entry.phase in {EntryPhase.VERIFIED, EntryPhase.CLEANED}
            and _matches_after(state, entry)
            for entry, state in zip(record.entries, states, strict=True)
        )
    return False


def plan_recovery(root: ReadRoot, record: JournalRecord) -> tuple[RecoveryAction, ...]:
    if record.target_identity != root.identity:
        raise SupportError(
            "transaction journal belongs to a different target identity",
            code=ErrorCode.DRIFT,
        )
    state_list = [root.inspect(entry.relative) for entry in record.entries]
    states = {
        entry.relative: state
        for entry, state in zip(record.entries, state_list, strict=True)
    }
    committed = _is_committed_record(record, state_list)
    actions: list[RecoveryAction] = []
    completed = _completed_actions(record)
    _require_completed_action_state(root, record, states)

    # Preflight every destination and every present artifact before proposing
    # any mutation. Recovery never partially acts on an already ambiguous set.
    for entry in record.entries:
        state = states[entry.relative]
        if committed:
            if not _matches_after(state, entry):
                raise SupportError(
                    f"verified committed file drifted: {entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
        elif not (
            _matches_before(state, entry)
            or _matches_after(state, entry)
            or _matches_restored(state, entry, exact_mode=False)
        ):
            raise SupportError(
                "managed file is ambiguous during recovery: "
                f"{entry.relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )
        _journal_artifact_state(root, entry.stage)
        if entry.recovery is not None:
            _journal_artifact_state(root, entry.recovery)

    if not committed:
        for directory in record.created_directories:
            path = root.target / directory.relative
            try:
                root.backend.inspect_path(path)
            except FileNotFoundError:
                continue
            if directory.identity is None:
                raise SupportError(
                    "managed directory creation completed before its identity "
                    f"was durably recorded: {directory.relative.as_posix()}",
                    code=ErrorCode.JOURNAL,
                )
            require_same_identity(
                path,
                directory.identity,
                expected_type=stat.S_IFDIR,
                description=f"created directory {directory.relative.as_posix()}",
                backend=root.backend,
            )

    if not committed:
        for entry in reversed(record.entries):
            state = states[entry.relative]
            if entry.before_exists:
                key = (RecoveryActionKind.RESTORE, entry.relative)
                if key not in completed and (
                    _matches_after(state, entry)
                    or _matches_restored(state, entry, exact_mode=False)
                ):
                    if entry.recovery is None:
                        raise SupportError(
                            f"verified recovery copy is unavailable: "
                            f"{entry.relative.as_posix()}",
                            code=ErrorCode.JOURNAL,
                        )
                    artifact_state = _journal_artifact_state(root, entry.recovery)
                    if _matches_after(state, entry) and artifact_state is None:
                        raise SupportError(
                            f"verified recovery copy is unavailable: "
                            f"{entry.relative.as_posix()}",
                            code=ErrorCode.JOURNAL,
                        )
                    actions.append(
                        RecoveryAction(RecoveryActionKind.RESTORE, entry.relative)
                    )
            elif (
                RecoveryActionKind.REMOVE_CREATED,
                entry.relative,
            ) not in completed and (
                _matches_after(state, entry)
                or (not state.exists and entry.applied_identity is not None)
            ):
                actions.append(
                    RecoveryAction(
                        RecoveryActionKind.REMOVE_CREATED,
                        entry.relative,
                    )
                )

    for entry in record.entries:
        stage_key = (RecoveryActionKind.REMOVE_STAGE, entry.stage.relative)
        if entry.stage.identity is not None and stage_key not in completed:
            actions.append(
                RecoveryAction(RecoveryActionKind.REMOVE_STAGE, entry.stage.relative)
            )
        if (
            entry.recovery is not None
            and entry.recovery.identity is not None
            and (RecoveryActionKind.REMOVE_RECOVERY, entry.recovery.relative)
            not in completed
        ):
            restore_pending = any(
                action.kind == RecoveryActionKind.RESTORE
                and action.relative == entry.relative
                for action in actions
            )
            restore_completed = (
                RecoveryActionKind.RESTORE,
                entry.relative,
            ) in completed
            if not restore_pending and not restore_completed:
                actions.append(
                    RecoveryAction(
                        RecoveryActionKind.REMOVE_RECOVERY,
                        entry.recovery.relative,
                    )
                )
    if not committed:
        for directory in reversed(record.created_directories):
            key = (RecoveryActionKind.REMOVE_DIRECTORY, directory.relative)
            if directory.identity is not None and key not in completed:
                actions.append(
                    RecoveryAction(
                        RecoveryActionKind.REMOVE_DIRECTORY,
                        directory.relative,
                    )
                )
    actions.append(
        RecoveryAction(
            RecoveryActionKind.REMOVE_JOURNAL,
            root.journal_path.relative_to(root.target),
        )
    )
    return tuple(actions)


def print_recovery_preview(actions: tuple[RecoveryAction, ...]) -> None:
    if not actions:
        print("No unfinished initializer transaction found.")
        return
    print("Planned recovery (not written):")
    labels = {
        RecoveryActionKind.RESTORE: "restore managed file",
        RecoveryActionKind.REMOVE_CREATED: "remove transaction-created file",
        RecoveryActionKind.REMOVE_STAGE: "remove private staged copy",
        RecoveryActionKind.REMOVE_RECOVERY: "remove private recovery copy",
        RecoveryActionKind.REMOVE_JOURNAL: "remove completed recovery journal",
        RecoveryActionKind.REMOVE_DIRECTORY: (
            "remove empty transaction-created directory"
        ),
    }
    for action in actions:
        print(f"- {labels[action.kind]}: {action.relative.as_posix()}")
    print("Rerun with --recover --write to apply this recovery plan.")


def _entry_by_relative(record: JournalRecord, relative: Path) -> JournalEntry:
    for entry in record.entries:
        if entry.relative == relative:
            return entry
    raise SupportError("recovery action has no journal entry", code=ErrorCode.JOURNAL)


def _artifact_by_relative(record: JournalRecord, relative: Path) -> JournalArtifact:
    for entry in record.entries:
        for artifact in (entry.stage, entry.recovery):
            if artifact is not None and artifact.relative == relative:
                return artifact
    raise SupportError(
        "recovery action has no journal artifact", code=ErrorCode.JOURNAL
    )


def _append_recovery_completion(
    store: JournalStore,
    record: JournalRecord,
    action: RecoveryAction,
    identity: PathIdentity | None = None,
) -> JournalRecord:
    if action.kind == RecoveryActionKind.REMOVE_JOURNAL:
        raise SupportError(
            "journal removal cannot be appended to its own record",
            code=ErrorCode.TRANSITION,
        )
    if (action.kind == RecoveryActionKind.RESTORE) != (identity is not None):
        raise SupportError(
            "recovery completion identity does not match its action",
            code=ErrorCode.TRANSITION,
        )
    completed = JournalRecoveryAction(action.kind, action.relative, identity)
    updated = replace(
        record,
        sequence=record.sequence + 1,
        recovery_actions=(*record.recovery_actions, completed),
    )
    store.append(updated)
    return updated


def apply_recovery(root: ReadRoot, store: JournalStore, record: JournalRecord) -> None:
    actions = plan_recovery(root, record)
    current_record = record
    for action in actions:
        root.require_current()
        if action.kind == RecoveryActionKind.RESTORE:
            entry = _entry_by_relative(current_record, action.relative)
            assert entry.recovery is not None
            artifact_path = root.target / entry.recovery.relative
            destination_state = root.inspect(entry.relative)
            if _matches_after(destination_state, entry):
                recovery_result = root.backend.inspect_path(artifact_path)
                if owner_from_stat(recovery_result) != entry.before_owner:
                    raise SupportError(
                        f"recovery artifact cannot preserve ownership: "
                        f"{entry.relative.as_posix()}",
                        code=ErrorCode.UNSUPPORTED,
                    )
                # This digest/identity read is the final operation before the
                # recovery artifact is consumed by replacement.
                artifact_identity = _journal_artifact_state(root, entry.recovery)
                if artifact_identity is None:
                    raise SupportError(
                        f"recovery copy disappeared: "
                        f"{entry.recovery.relative.as_posix()}",
                        code=ErrorCode.DRIFT,
                    )
                root.backend.replace(
                    artifact_path,
                    root.target / entry.relative,
                    FileOperation.RESTORE_MANAGED,
                )
                destination_state = root.inspect(entry.relative)
                if not _matches_restored(
                    destination_state,
                    entry,
                    artifact_identity,
                    exact_mode=False,
                ):
                    raise SupportError(
                        "restored file did not match the recovery artifact: "
                        f"{entry.relative.as_posix()}",
                        code=ErrorCode.DRIFT,
                    )
            elif _matches_restored(destination_state, entry, exact_mode=False):
                artifact_identity = destination_state.identity
                if _journal_artifact_state(root, entry.recovery) is not None:
                    raise SupportError(
                        "recovery artifact still exists beside a restored file: "
                        f"{entry.relative.as_posix()}",
                        code=ErrorCode.DRIFT,
                    )
            else:
                raise SupportError(
                    "managed file drifted immediately before recovery: "
                    f"{entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            assert artifact_identity is not None
            if entry.before_mode is not None:
                chmod_owned_path(
                    root.target / entry.relative,
                    artifact_identity,
                    entry.before_mode,
                    expected_type=stat.S_IFREG,
                    description=f"restored managed file {entry.relative.as_posix()}",
                    backend=root.backend,
                )
            root.backend.sync_directory((root.target / entry.relative).parent)
            restored = root.inspect(entry.relative)
            if not _matches_restored(
                restored, entry, artifact_identity, exact_mode=True
            ):
                raise SupportError(
                    f"restored file does not exactly match its before state: "
                    f"{entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            current_record = _append_recovery_completion(
                store, current_record, action, artifact_identity
            )
        elif action.kind == RecoveryActionKind.REMOVE_CREATED:
            entry = _entry_by_relative(current_record, action.relative)
            state = root.inspect(entry.relative)
            if not state.exists:
                current_record = _append_recovery_completion(
                    store, current_record, action
                )
                continue
            if not _matches_after(state, entry) or state.identity is None:
                raise SupportError(
                    "managed file drifted during recovery: "
                    f"{entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            require_same_identity(
                root.target / entry.relative,
                state.identity,
                expected_type=stat.S_IFREG,
                description=f"managed file {entry.relative.as_posix()}",
                backend=root.backend,
            )
            root.backend.unlink(
                root.target / entry.relative, FileOperation.REMOVE_MANAGED
            )
            root.backend.sync_directory((root.target / entry.relative).parent)
            if root.inspect(entry.relative).exists:
                raise SupportError(
                    f"transaction-created file still exists after removal: "
                    f"{entry.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            current_record = _append_recovery_completion(store, current_record, action)
        elif action.kind in {
            RecoveryActionKind.REMOVE_STAGE,
            RecoveryActionKind.REMOVE_RECOVERY,
        }:
            artifact = _artifact_by_relative(current_record, action.relative)
            identity = _journal_artifact_state(root, artifact)
            if identity is None:
                current_record = _append_recovery_completion(
                    store, current_record, action
                )
                continue
            require_same_identity(
                root.target / artifact.relative,
                identity,
                expected_type=stat.S_IFREG,
                description=f"recovery artifact {artifact.relative.as_posix()}",
                backend=root.backend,
            )
            root.backend.unlink(
                root.target / artifact.relative, FileOperation.REMOVE_ARTIFACT
            )
            root.backend.sync_directory((root.target / artifact.relative).parent)
            if _journal_artifact_state(root, artifact) is not None:
                raise SupportError(
                    f"recovery artifact still exists after removal: "
                    f"{artifact.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
            current_record = _append_recovery_completion(store, current_record, action)
        elif action.kind == RecoveryActionKind.REMOVE_JOURNAL:
            store.remove()
        elif action.kind == RecoveryActionKind.REMOVE_DIRECTORY:
            directory = next(
                item
                for item in current_record.created_directories
                if item.relative == action.relative
            )
            if directory.identity is None:
                raise SupportError(
                    "created directory identity is unavailable",
                    code=ErrorCode.JOURNAL,
                )
            try:
                require_same_identity(
                    root.target / directory.relative,
                    directory.identity,
                    expected_type=stat.S_IFDIR,
                    description=(f"created directory {directory.relative.as_posix()}"),
                    backend=root.backend,
                )
            except OSError as exc:
                raise SupportError(
                    f"could not inspect recovered directory "
                    f"{directory.relative.as_posix()}",
                    code=ErrorCode.ROLLBACK,
                ) from exc
            except SupportError:
                try:
                    root.backend.inspect_path(root.target / directory.relative)
                except FileNotFoundError:
                    current_record = _append_recovery_completion(
                        store, current_record, action
                    )
                    continue
                raise
            try:
                root.backend.rmdir(root.target / directory.relative)
                root.backend.sync_directory((root.target / directory.relative).parent)
            except OSError as exc:
                raise SupportError(
                    f"could not remove recovered directory "
                    f"{directory.relative.as_posix()}",
                    code=ErrorCode.ROLLBACK,
                ) from exc
            try:
                root.backend.inspect_path(root.target / directory.relative)
            except FileNotFoundError:
                current_record = _append_recovery_completion(
                    store, current_record, action
                )
            else:
                raise SupportError(
                    f"recovered directory still exists after removal: "
                    f"{directory.relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
    print("Initializer transaction recovery completed.")


def recover(
    root: ReadRoot,
    *,
    write: bool,
) -> None:
    if not root.journal_exists():
        print("No unfinished initializer transaction found.")
        return
    store = JournalStore(root)
    try:
        record = store.load()
    except SupportError as exc:
        if str(exc) != INCOMPLETE_INITIAL_JOURNAL:
            raise
        plan = build_immutable_plan(root)
        if not plan.entries:
            raise
        transaction = WriteTransaction(root, plan)
        transaction._initialize_entries()
        transaction.created_directories = plan_parent_directories(
            root.target,
            plan.entries,
            root.backend,
        )
        transaction.phase = TransactionPhase.JOURNALED
        transaction.sequence = 0
        expected = encode_record(transaction._journal_record())
        if not store.matches_incomplete_initial(expected):
            raise
        incomplete_actions = (
            RecoveryAction(
                RecoveryActionKind.REMOVE_JOURNAL,
                root.journal_path.relative_to(root.target),
            ),
        )
        if write:
            store.remove()
            print("Initializer transaction recovery completed.")
        else:
            print_recovery_preview(incomplete_actions)
        return
    actions = plan_recovery(root, record)
    if write:
        apply_recovery(root, store, record)
    else:
        print_recovery_preview(actions)

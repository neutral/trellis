"""Capability-rooted, identity-checked local filesystem access.

The POSIX backend adds final-component ``O_NOFOLLOW`` protection and safe
no-follow chmod where the interpreter exposes them. The portable backend uses
before/open/after identity checks. Neither backend claims to be an operating-
system sandbox against a malicious same-account process racing every syscall.
"""

from __future__ import annotations

import os
import stat
import sys
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .constants import JOURNAL_RELATIVE, MANAGED_FILES
from .errors import ErrorCode, SupportError
from .models import FileOwner, FileState, PathIdentity

MAX_MANAGED_FILE_BYTES = 4 * 1024 * 1024


class FileOperation(StrEnum):
    """Typed fault and audit boundaries for local filesystem effects."""

    INSPECT = "inspect"
    OPEN_READ = "open_read"
    CREATE_ARTIFACT = "create_artifact"
    CREATE_JOURNAL = "create_journal"
    APPEND_JOURNAL = "append_journal"
    CREATE_DIRECTORY = "create_directory"
    CHMOD = "chmod"
    REPLACE_MANAGED = "replace_managed"
    RESTORE_MANAGED = "restore_managed"
    REMOVE_ARTIFACT = "remove_artifact"
    REMOVE_MANAGED = "remove_managed"
    REMOVE_DIRECTORY = "remove_directory"
    REMOVE_JOURNAL = "remove_journal"
    SYNC_FILE = "sync_file"
    SYNC_DIRECTORY = "sync_directory"


class FileSystemBackend(Protocol):
    """Injectable primitive boundary used only below write capabilities."""

    posture: str
    complete_acl_xattr_visibility: bool

    def inspect_path(self, path: Path) -> os.stat_result: ...

    def open_file(
        self, path: Path, flags: int, mode: int, operation: FileOperation
    ) -> int: ...

    def create_private_file(self, path: Path, content: bytes) -> PathIdentity: ...

    def replace(
        self,
        source: Path,
        destination: Path,
        operation: FileOperation,
    ) -> None: ...

    def unlink(self, path: Path, operation: FileOperation) -> None: ...

    def mkdir(self, path: Path, mode: int) -> None: ...

    def rmdir(self, path: Path) -> None: ...

    def chmod(self, path: Path, mode: int, expected: PathIdentity) -> None: ...

    def fchmod(self, descriptor: int, mode: int) -> None: ...

    def fsync(self, descriptor: int, operation: FileOperation) -> None: ...

    def sync_directory(self, path: Path) -> None: ...


class IdentityCheckedFileSystem:
    """Portable backend with injectable, typed operations."""

    complete_acl_xattr_visibility = sys.platform.startswith("linux")
    posture = (
        "portable identity checks; ordinary drift is rejected, but the platform "
        "does not provide a directory-descriptor containment guarantee"
    )

    def inspect_path(self, path: Path) -> os.stat_result:
        return os.lstat(path)

    def open_file(
        self, path: Path, flags: int, mode: int, operation: FileOperation
    ) -> int:
        del operation
        return os.open(path, flags, mode)

    def create_private_file(self, path: Path, content: bytes) -> PathIdentity:
        descriptor = -1
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = self.open_file(
                path, flags, 0o600, FileOperation.CREATE_ARTIFACT
            )
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                result = os.fstat(handle.fileno())
                identity = identity_from_stat(path, result)
                if identity.file_type != stat.S_IFREG:
                    raise SupportError(
                        "transaction temporary is not a regular file",
                        code=ErrorCode.UNSAFE_PATH,
                    )
                self.fchmod(handle.fileno(), 0o600)
                require_supported_regular_metadata(
                    path,
                    os.fstat(handle.fileno()),
                    descriptor=handle.fileno(),
                )
                handle.write(content)
                handle.flush()
                self.fsync(handle.fileno(), FileOperation.SYNC_FILE)
            require_same_identity(
                path,
                identity,
                expected_type=stat.S_IFREG,
                description="transaction temporary",
                backend=self,
            )
            return identity
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def replace(
        self,
        source: Path,
        destination: Path,
        operation: FileOperation,
    ) -> None:
        del operation
        os.replace(source, destination)

    def unlink(self, path: Path, operation: FileOperation) -> None:
        del operation
        path.unlink()

    def mkdir(self, path: Path, mode: int) -> None:
        path.mkdir(mode=mode)

    def rmdir(self, path: Path) -> None:
        path.rmdir()

    def chmod(self, path: Path, mode: int, expected: PathIdentity) -> None:
        if os.name != "posix":
            return
        nofollow = int(getattr(os, "O_NOFOLLOW", 0))
        if not nofollow or not hasattr(os, "fchmod"):
            raise SupportError(
                "platform cannot safely change permissions",
                code=ErrorCode.UNSUPPORTED,
            )
        flags = os.O_RDONLY | nofollow | int(getattr(os, "O_CLOEXEC", 0))
        if expected.file_type == stat.S_IFDIR:
            flags |= int(getattr(os, "O_DIRECTORY", 0))
        descriptor = -1
        try:
            descriptor = self.open_file(path, flags, 0, FileOperation.CHMOD)
            result = os.fstat(descriptor)
            observed = identity_from_stat(path, result)
            if observed != expected:
                raise SupportError(
                    "permission target identity changed",
                    code=ErrorCode.DRIFT,
                )
            if expected.file_type == stat.S_IFREG:
                require_supported_regular_metadata(path, result, descriptor=descriptor)
            self.fchmod(descriptor, mode)
            if identity_from_stat(path, os.fstat(descriptor)) != expected:
                raise SupportError(
                    "permission target identity changed",
                    code=ErrorCode.DRIFT,
                )
        except OSError as exc:
            raise SupportError(
                "could not safely change permissions",
                code=ErrorCode.FILESYSTEM,
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def fchmod(self, descriptor: int, mode: int) -> None:
        if os.name != "posix":
            return
        try:
            os.fchmod(descriptor, mode)  # type: ignore[attr-defined, unused-ignore]
        except OSError as exc:
            raise SupportError(
                "could not safely change open-file permissions",
                code=ErrorCode.FILESYSTEM,
            ) from exc
        if stat.S_IMODE(os.fstat(descriptor).st_mode) != mode:
            raise SupportError(
                "open-file permissions did not match the requested mode",
                code=ErrorCode.FILESYSTEM,
            )

    def fsync(self, descriptor: int, operation: FileOperation) -> None:
        del operation
        os.fsync(descriptor)

    def sync_directory(self, path: Path) -> None:
        del path
        # Windows and several portable filesystems do not expose a safe
        # directory-fsync primitive. File bytes are still flushed; recovery is
        # identity checked but not advertised as power-loss durable here.


class PosixIdentityCheckedFileSystem(IdentityCheckedFileSystem):
    """POSIX backend adding no-follow opens and directory metadata flushes."""

    posture = (
        "POSIX identity checks with final-component no-follow opens and "
        "best-effort directory metadata fsync"
    )

    def open_file(
        self, path: Path, flags: int, mode: int, operation: FileOperation
    ) -> int:
        del operation
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        return os.open(path, flags | nofollow, mode)

    def sync_directory(self, path: Path) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = -1
        try:
            descriptor = os.open(path, flags)
            os.fsync(descriptor)
        except OSError:
            # Directory fsync is unavailable on some otherwise POSIX-like
            # filesystems. The append-only journal remains restart-readable,
            # but no universal power-loss guarantee is claimed.
            return
        finally:
            if descriptor >= 0:
                os.close(descriptor)


def default_backend() -> FileSystemBackend:
    if os.name == "posix" and bool(getattr(os, "O_NOFOLLOW", False)):
        return PosixIdentityCheckedFileSystem()
    return IdentityCheckedFileSystem()


def _is_reparse_point(result: os.stat_result) -> bool:
    attributes = int(getattr(result, "st_file_attributes", 0))
    marker = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return bool(marker and attributes & marker)


def identity_from_stat(path: Path, result: os.stat_result) -> PathIdentity:
    """Return a stable no-follow identity or fail closed."""

    inode = int(result.st_ino)
    if inode == 0:
        raise SupportError(
            f"filesystem does not expose a stable identity for {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    return PathIdentity(
        device=int(result.st_dev),
        inode=inode,
        file_type=stat.S_IFMT(result.st_mode),
    )


def owner_from_stat(result: os.stat_result) -> FileOwner | None:
    """Capture owner metadata on platforms that expose POSIX ownership."""

    if os.name != "posix":
        return None
    return FileOwner(user=int(result.st_uid), group=int(result.st_gid))


def require_supported_regular_metadata(
    path: Path,
    result: os.stat_result,
    *,
    descriptor: int | None = None,
) -> FileOwner | None:
    """Reject metadata that a content replacement cannot safely preserve."""

    if stat.S_IFMT(result.st_mode) != stat.S_IFREG:
        raise SupportError(
            f"managed support path is not a file: {path.name}",
            code=ErrorCode.UNSAFE_PATH,
        )
    if int(result.st_nlink) != 1:
        raise SupportError(
            f"managed file has multiple hard links: {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    special_mode = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
    if result.st_mode & special_mode:
        raise SupportError(
            f"managed file has unsupported special permissions: {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    if int(getattr(result, "st_flags", 0)) != 0:
        raise SupportError(
            f"managed file has unsupported filesystem flags: {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    attributes = int(getattr(result, "st_file_attributes", 0))
    allowed_attributes = int(getattr(stat, "FILE_ATTRIBUTE_ARCHIVE", 0)) | int(
        getattr(stat, "FILE_ATTRIBUTE_NORMAL", 0)
    )
    if attributes & ~allowed_attributes:
        raise SupportError(
            f"managed file has unsupported platform attributes: {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    # CPython exposes descriptor-scoped xattr inspection on Linux. Other
    # supported hosts still reject links, special modes, flags, platform
    # attributes, and foreign ownership; no unsafe path/subprocess fallback is
    # used where the standard library lacks an equivalent ACL/xattr API.
    if IdentityCheckedFileSystem.complete_acl_xattr_visibility:
        if descriptor is None:
            raise SupportError(
                "open-file metadata verification is unavailable",
                code=ErrorCode.UNSUPPORTED,
            )
        try:
            extended = os.listxattr(descriptor)  # type: ignore[attr-defined, unused-ignore]
        except OSError as exc:
            raise SupportError(
                "could not inspect ACL or extended metadata",
                code=ErrorCode.FILESYSTEM,
            ) from exc
        if extended:
            raise SupportError(
                f"managed file has unsupported ACL or extended metadata: {path.name}",
                code=ErrorCode.UNSUPPORTED,
            )
    owner = owner_from_stat(result)
    if owner is not None and owner.user != os.geteuid():  # type: ignore[attr-defined, unused-ignore]
        raise SupportError(
            f"managed file is owned by a different user: {path.name}",
            code=ErrorCode.UNSUPPORTED,
        )
    return owner


def capture_path_identity(
    path: Path,
    *,
    expected_type: int,
    description: str,
    backend: FileSystemBackend | None = None,
) -> PathIdentity:
    selected = backend or default_backend()
    try:
        result = selected.inspect_path(path)
    except OSError as exc:
        raise SupportError(
            f"could not inspect {description}", code=ErrorCode.FILESYSTEM
        ) from exc
    if stat.S_ISLNK(result.st_mode) or _is_reparse_point(result):
        raise SupportError(
            f"refusing symlinked {description}", code=ErrorCode.UNSAFE_PATH
        )
    identity = identity_from_stat(path, result)
    if identity.file_type != expected_type:
        raise SupportError(f"{description} changed type", code=ErrorCode.DRIFT)
    return identity


def require_same_identity(
    path: Path,
    expected: PathIdentity,
    *,
    expected_type: int,
    description: str,
    backend: FileSystemBackend | None = None,
) -> None:
    current = capture_path_identity(
        path,
        expected_type=expected_type,
        description=description,
        backend=backend,
    )
    if current != expected:
        raise SupportError(
            f"{description} identity changed during the transaction",
            code=ErrorCode.DRIFT,
        )


def validate_target(raw_target: Path, backend: FileSystemBackend | None = None) -> Path:
    selected = backend or default_backend()
    if not raw_target.is_absolute():
        raise SupportError(
            "selected target must be an explicit absolute path",
            code=ErrorCode.UNSAFE_PATH,
        )
    try:
        before = selected.inspect_path(raw_target)
    except FileNotFoundError as exc:
        raise SupportError(
            "selected target does not exist", code=ErrorCode.UNSAFE_PATH
        ) from exc
    except OSError as exc:
        raise SupportError(
            "could not inspect selected target", code=ErrorCode.FILESYSTEM
        ) from exc
    if stat.S_ISLNK(before.st_mode) or _is_reparse_point(before):
        raise SupportError(
            "refusing symlinked selected target", code=ErrorCode.UNSAFE_PATH
        )
    identity = identity_from_stat(raw_target, before)
    if identity.file_type != stat.S_IFDIR:
        raise SupportError(
            "selected target is not a directory", code=ErrorCode.UNSAFE_PATH
        )
    target = raw_target.resolve()
    if target == Path(target.anchor):
        raise SupportError(
            "refusing to operate on a filesystem root", code=ErrorCode.UNSAFE_PATH
        )
    require_same_identity(
        target,
        identity,
        expected_type=stat.S_IFDIR,
        description="target directory",
        backend=selected,
    )
    return target


def _validate_relative(relative: Path, *, allow_journal: bool = False) -> None:
    allowed = set(MANAGED_FILES)
    if allow_journal:
        allowed.add(JOURNAL_RELATIVE)
    if relative not in allowed:
        raise SupportError(
            f"path is outside the initializer capability: {relative.as_posix()}",
            code=ErrorCode.UNSAFE_PATH,
        )


def reject_symlinks(
    target: Path,
    relative_path: Path,
    backend: FileSystemBackend | None = None,
    *,
    allow_transaction_path: bool = False,
) -> None:
    selected = backend or default_backend()
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise SupportError(
            f"managed path escapes the target: {relative_path}",
            code=ErrorCode.UNSAFE_PATH,
        )
    if not allow_transaction_path:
        _validate_relative(relative_path)
    current = target
    for part in relative_path.parts:
        current = current / part
        try:
            result = selected.inspect_path(current)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise SupportError(
                "could not inspect managed path",
                code=ErrorCode.FILESYSTEM,
            ) from exc
        if stat.S_ISLNK(result.st_mode) or _is_reparse_point(result):
            raise SupportError(
                f"refusing symlinked support path: {relative_path}",
                code=ErrorCode.UNSAFE_PATH,
            )
    try:
        (target / relative_path).resolve(strict=False).relative_to(target)
    except ValueError as exc:
        raise SupportError(
            f"managed path escapes the target: {relative_path}",
            code=ErrorCode.UNSAFE_PATH,
        ) from exc


def _read_regular_file(
    path: Path,
    identity: PathIdentity,
    relative: Path,
    backend: FileSystemBackend,
) -> tuple[bytes, int | None, FileOwner | None]:
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        descriptor = backend.open_file(path, flags, 0o600, FileOperation.OPEN_READ)
        opened = backend.inspect_path(path)
        descriptor_result = os.fstat(descriptor)
        opened_identity = identity_from_stat(path, descriptor_result)
        if opened_identity != identity or identity_from_stat(path, opened) != identity:
            raise SupportError(
                f"managed file changed before it was read: {relative.as_posix()}",
                code=ErrorCode.DRIFT,
            )
        owner = require_supported_regular_metadata(
            path, descriptor_result, descriptor=descriptor
        )
        mode = stat.S_IMODE(descriptor_result.st_mode) if os.name == "posix" else None
        size = int(os.fstat(descriptor).st_size)
        if size > MAX_MANAGED_FILE_BYTES:
            raise SupportError(
                f"managed file exceeds the {MAX_MANAGED_FILE_BYTES}-byte limit: "
                f"{relative.as_posix()}",
                code=ErrorCode.CONFLICT,
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            content = handle.read(MAX_MANAGED_FILE_BYTES + 1)
            final_result = os.fstat(handle.fileno())
            final_owner = require_supported_regular_metadata(
                path, final_result, descriptor=handle.fileno()
            )
            final_mode = (
                stat.S_IMODE(final_result.st_mode) if os.name == "posix" else None
            )
            if (
                identity_from_stat(path, final_result) != identity
                or final_owner != owner
                or final_mode != mode
            ):
                raise SupportError(
                    f"managed file changed while it was being read: "
                    f"{relative.as_posix()}",
                    code=ErrorCode.DRIFT,
                )
        if len(content) > MAX_MANAGED_FILE_BYTES:
            raise SupportError(
                f"managed file exceeds the {MAX_MANAGED_FILE_BYTES}-byte limit: "
                f"{relative.as_posix()}",
                code=ErrorCode.CONFLICT,
            )
        return content, mode, owner
    except OSError as exc:
        raise SupportError(
            f"could not inspect {relative.as_posix()}", code=ErrorCode.FILESYSTEM
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_verified_bytes(
    path: Path,
    identity: PathIdentity,
    *,
    limit: int,
    backend: FileSystemBackend | None = None,
) -> bytes:
    """Read one already-authorized regular file with identity and size checks."""

    selected = backend or default_backend()
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        descriptor = selected.open_file(path, flags, 0o600, FileOperation.OPEN_READ)
        descriptor_result = os.fstat(descriptor)
        opened = identity_from_stat(path, descriptor_result)
        if opened != identity or opened.file_type != stat.S_IFREG:
            raise SupportError(
                "authorized file changed while opening", code=ErrorCode.DRIFT
            )
        require_supported_regular_metadata(
            path, descriptor_result, descriptor=descriptor
        )
        size = int(os.fstat(descriptor).st_size)
        if size > limit:
            raise SupportError(
                "authorized file exceeds its read limit", code=ErrorCode.CONFLICT
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            content = handle.read(limit + 1)
            final_result = os.fstat(handle.fileno())
            if identity_from_stat(path, final_result) != identity:
                raise SupportError(
                    "authorized file changed while it was read",
                    code=ErrorCode.DRIFT,
                )
            require_supported_regular_metadata(
                path, final_result, descriptor=handle.fileno()
            )
        if len(content) > limit:
            raise SupportError(
                "authorized file exceeds its read limit", code=ErrorCode.CONFLICT
            )
        require_same_identity(
            path,
            identity,
            expected_type=stat.S_IFREG,
            description="authorized file",
            backend=selected,
        )
        return content
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def capture_file_state(
    target: Path,
    relative: Path,
    backend: FileSystemBackend | None = None,
) -> FileState:
    selected = backend or default_backend()
    _validate_relative(relative)
    reject_symlinks(target, relative, selected)
    path = target / relative
    try:
        before = selected.inspect_path(path)
    except FileNotFoundError:
        return FileState(exists=False)
    except OSError as exc:
        raise SupportError(
            f"could not inspect {relative.as_posix()}", code=ErrorCode.FILESYSTEM
        ) from exc
    identity = identity_from_stat(path, before)
    if identity.file_type != stat.S_IFREG:
        raise SupportError(
            f"managed support path is not a file: {relative}",
            code=ErrorCode.UNSAFE_PATH,
        )
    content, mode, owner = _read_regular_file(path, identity, relative, selected)
    try:
        after = selected.inspect_path(path)
    except OSError as exc:
        raise SupportError(
            f"could not recheck {relative.as_posix()}", code=ErrorCode.FILESYSTEM
        ) from exc
    if identity_from_stat(path, after) != identity:
        raise SupportError(
            f"managed file changed while it was being read: {relative.as_posix()}",
            code=ErrorCode.DRIFT,
        )
    if (
        (stat.S_IMODE(after.st_mode) if os.name == "posix" else None) != mode
        or owner_from_stat(after) != owner
        or int(after.st_nlink) != 1
        or int(getattr(after, "st_flags", 0)) != 0
    ):
        raise SupportError(
            f"managed file metadata changed while it was being read: "
            f"{relative.as_posix()}",
            code=ErrorCode.DRIFT,
        )
    return FileState(
        exists=True,
        content=content,
        mode=mode,
        owner=owner,
        identity=identity,
    )


def parent_paths(target: Path, relative_parent: Path) -> tuple[Path, ...]:
    paths = [target]
    current = target
    for part in relative_parent.parts:
        current = current / part
        paths.append(current)
    return tuple(paths)


def capture_parent_identities(
    target: Path,
    relative_parent: Path,
    backend: FileSystemBackend | None = None,
) -> tuple[tuple[Path, PathIdentity], ...]:
    selected = backend or default_backend()
    identities: list[tuple[Path, PathIdentity]] = []
    for path in parent_paths(target, relative_parent):
        relative = Path(".") if path == target else path.relative_to(target)
        description = (
            "target directory"
            if relative == Path(".")
            else f"managed parent {relative.as_posix()}"
        )
        identities.append(
            (
                path,
                capture_path_identity(
                    path,
                    expected_type=stat.S_IFDIR,
                    description=description,
                    backend=selected,
                ),
            )
        )
    return tuple(identities)


def require_parent_identities(
    identities: tuple[tuple[Path, PathIdentity], ...],
    backend: FileSystemBackend | None = None,
) -> None:
    selected = backend or default_backend()
    for index, (path, expected) in enumerate(identities):
        description = (
            "target directory" if index == 0 else f"managed parent {path.name}"
        )
        require_same_identity(
            path,
            expected,
            expected_type=stat.S_IFDIR,
            description=description,
            backend=selected,
        )


class ReadRoot:
    """Read-only capability for one captured work folder."""

    def __init__(
        self,
        target: Path,
        identity: PathIdentity,
        backend: FileSystemBackend,
    ) -> None:
        self.target = target
        self.identity = identity
        self.backend = backend

    @classmethod
    def open(
        cls,
        raw_target: Path,
        backend: FileSystemBackend | None = None,
    ) -> ReadRoot:
        selected = backend or default_backend()
        target = validate_target(raw_target, selected)
        identity = capture_path_identity(
            target,
            expected_type=stat.S_IFDIR,
            description="target directory",
            backend=selected,
        )
        return cls(target, identity, selected)

    def require_current(self) -> None:
        require_same_identity(
            self.target,
            self.identity,
            expected_type=stat.S_IFDIR,
            description="target directory",
            backend=self.backend,
        )

    def inspect(self, relative: Path) -> FileState:
        self.require_current()
        return capture_file_state(self.target, relative, self.backend)

    def agents_references_handbook(self) -> bool:
        """Read the optional root instruction file without granting writes."""

        path = self.target / "AGENTS.md"
        try:
            result = self.backend.inspect_path(path)
            if stat.S_ISLNK(result.st_mode) or _is_reparse_point(result):
                return False
            identity = identity_from_stat(path, result)
            if identity.file_type != stat.S_IFREG or int(result.st_size) > 1024 * 1024:
                return False
            content = read_verified_bytes(
                path,
                identity,
                limit=1024 * 1024,
                backend=self.backend,
            )
            return "_handbook" in content.decode("utf-8-sig")
        except (FileNotFoundError, OSError, SupportError, UnicodeDecodeError):
            return False

    @property
    def journal_path(self) -> Path:
        return self.target / JOURNAL_RELATIVE

    def journal_exists(self) -> bool:
        self.require_current()
        try:
            self.backend.inspect_path(self.journal_path)
        except FileNotFoundError:
            return False
        capture_path_identity(
            self.journal_path,
            expected_type=stat.S_IFREG,
            description="initializer transaction journal",
            backend=self.backend,
        )
        return True

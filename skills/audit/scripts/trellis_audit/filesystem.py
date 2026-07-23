"""Capability-rooted, bounded, read-only filesystem access."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from .context import AuditBudget
from .diagnostics import (
    DiagnosticPath,
    Finding,
    InvocationError,
    diagnostic_path,
    finding,
    unsafe_path_character,
)
from .json_models import parse_json
from .models import FrozenJson

PathIdentity = tuple[int, int, int, int, int, int, int, int]
IdentitySnapshot = tuple[tuple[Path, PathIdentity], ...]
_FILE_ATTRIBUTE_REPARSE_POINT = int(
    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
)


class ReadBackend(Protocol):
    """Injectable primitive reads used by :class:`ReadRoot`."""

    def lstat(self, path: Path) -> os.stat_result: ...

    def resolve(self, path: Path) -> Path: ...

    def open_read(self, path: Path, flags: int) -> int: ...

    def fstat(self, descriptor: int) -> os.stat_result: ...

    def read(self, descriptor: int, size: int) -> bytes: ...

    def close(self, descriptor: int) -> None: ...

    def list_names(self, path: Path) -> Iterable[str]: ...

    def readlink(self, path: Path) -> str: ...


class OsReadBackend:
    """Standard-library backend with no-follow file opens where available."""

    def lstat(self, path: Path) -> os.stat_result:
        return os.lstat(path)

    def resolve(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def open_read(self, path: Path, flags: int) -> int:
        return os.open(path, flags)

    def fstat(self, descriptor: int) -> os.stat_result:
        return os.fstat(descriptor)

    def read(self, descriptor: int, size: int) -> bytes:
        return os.read(descriptor, size)

    def close(self, descriptor: int) -> None:
        os.close(descriptor)

    def list_names(self, path: Path) -> Iterator[str]:
        with os.scandir(path) as iterator:
            for entry in iterator:
                yield entry.name

    def readlink(self, path: Path) -> str:
        return os.readlink(path)


def filesystem_identity(metadata: os.stat_result) -> PathIdentity:
    """Return stable fields used to detect replacement during inspection."""
    if int(metadata.st_dev) == 0 or int(metadata.st_ino) == 0:
        raise InvocationError("path-identity-unavailable")
    # Windows path stat and handle stat expose different ctime semantics.
    # Birthtime is their shared stable timestamp when the runtime provides it.
    identity_time = (
        getattr(metadata, "st_birthtime_ns", None) if os.name == "nt" else None
    )
    if identity_time is None:
        identity_time = getattr(metadata, "st_ctime_ns", None)
    if identity_time is None:
        identity_time = int(float(getattr(metadata, "st_ctime", 0.0)) * 1_000_000_000)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        int(getattr(metadata, "st_file_attributes", 0)),
        int(getattr(metadata, "st_reparse_tag", 0)),
        int(identity_time),
    )


def is_link_like(metadata: os.stat_result) -> bool:
    """Treat Windows reparse points as containment-changing links."""
    return stat.S_ISLNK(metadata.st_mode) or bool(
        int(getattr(metadata, "st_file_attributes", 0)) & _FILE_ATTRIBUTE_REPARSE_POINT
    )


def identity_is_link_like(identity: PathIdentity) -> bool:
    return stat.S_ISLNK(identity[2]) or bool(
        identity[5] & _FILE_ATTRIBUTE_REPARSE_POINT
    )


@dataclass(frozen=True)
class RepoPath:
    """An unforgeable lexical path anchored to one disclosed read root."""

    root: ReadRoot
    segments: tuple[str, ...] = ()

    def __truediv__(self, value: str | PurePosixPath) -> RepoPath:
        return self.root.join(self, value)

    @property
    def name(self) -> str:
        return self.segments[-1] if self.segments else self.root.absolute.name

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.name).suffix

    @property
    def parent(self) -> RepoPath:
        if not self.segments:
            return self
        return RepoPath(self.root, self.segments[:-1])

    @property
    def parts(self) -> tuple[str, ...]:
        return self.segments

    def with_suffix(self, suffix: str) -> RepoPath:
        if not self.segments:
            raise ValueError("root path has no suffix")
        name = PurePosixPath(self.name).with_suffix(suffix).name
        return RepoPath(self.root, (*self.segments[:-1], name))

    def as_posix(self) -> str:
        return "." if not self.segments else "/".join(self.segments)

    def relative_to(self, parent: RepoPath) -> PurePosixPath:
        self.root.require_same_root(parent)
        prefix = parent.segments
        if self.segments[: len(prefix)] != prefix:
            raise ValueError("path is outside parent")
        return PurePosixPath(*self.segments[len(prefix) :])

    def __str__(self) -> str:
        return self.as_posix()


class ReadRoot:
    """The sole capability through which validators inspect repository files."""

    def __init__(
        self,
        absolute: Path,
        budget: AuditBudget,
        root_identity: PathIdentity,
        backend: ReadBackend | None = None,
    ) -> None:
        self.absolute = absolute
        self.budget = budget
        self.root_identity = root_identity
        self.backend: ReadBackend = backend or OsReadBackend()
        self._byte_cache: dict[RepoPath, tuple[IdentitySnapshot, bytes]] = {}
        self._list_cache: dict[
            RepoPath, tuple[IdentitySnapshot, tuple[RepoPath, ...]]
        ] = {}
        self._symlink_cache: dict[RepoPath, tuple[IdentitySnapshot, str]] = {}
        self._json_cache: dict[RepoPath, FrozenJson] = {}

    @classmethod
    def validate_target(
        cls, raw_target: Path, backend: ReadBackend | None = None
    ) -> tuple[Path, PathIdentity]:
        selected = backend or OsReadBackend()
        if not raw_target.is_absolute():
            raise InvocationError("target-not-absolute")
        try:
            metadata = selected.lstat(raw_target)
        except FileNotFoundError as exc:
            raise InvocationError("target-missing") from exc
        except (OSError, ValueError, UnicodeError) as exc:
            raise InvocationError("target-unavailable") from exc
        if is_link_like(metadata):
            raise InvocationError("target-symlink")
        if not stat.S_ISDIR(metadata.st_mode):
            raise InvocationError("target-not-directory")
        before_identity = filesystem_identity(metadata)
        try:
            target = selected.resolve(raw_target)
        except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
            raise InvocationError("target-unavailable") from exc
        if target == Path(target.anchor):
            raise InvocationError("target-root")
        try:
            raw_after = selected.lstat(raw_target)
            resolved_metadata = selected.lstat(target)
        except (OSError, ValueError, UnicodeError) as exc:
            raise InvocationError("target-unavailable") from exc
        if is_link_like(raw_after) or is_link_like(resolved_metadata):
            raise InvocationError("target-symlink")
        resolved_identity = filesystem_identity(resolved_metadata)
        if (
            filesystem_identity(raw_after) != before_identity
            or resolved_identity != before_identity
        ):
            raise InvocationError("path-identity-changed")
        return target, resolved_identity

    @classmethod
    def open(
        cls,
        target: Path,
        budget: AuditBudget,
        backend: ReadBackend | None = None,
    ) -> ReadRoot:
        selected = backend or OsReadBackend()
        validated, root_identity = cls.validate_target(target, selected)
        return cls(validated, budget, root_identity, selected)

    @property
    def path(self) -> RepoPath:
        return RepoPath(self)

    def require_same_root(self, path: RepoPath) -> None:
        if path.root is not self:
            raise InvocationError("path-escape")

    def join(self, base: RepoPath, value: str | PurePosixPath) -> RepoPath:
        self.require_same_root(base)
        raw = str(value).replace("\\", "/")
        if raw.startswith("/") or "\x00" in raw:
            raise InvocationError("path-malformed")
        segments = list(base.segments)
        for segment in raw.split("/"):
            if segment in {"", "."}:
                continue
            if any(unsafe_path_character(character) for character in segment):
                raise InvocationError("path-malformed")
            if segment == "..":
                if not segments:
                    raise InvocationError("path-escape")
                segments.pop()
            else:
                segments.append(segment)
        self.budget.check_depth(len(segments))
        return RepoPath(self, tuple(segments))

    def child(self, base: RepoPath, name: str) -> RepoPath:
        """Create one path from an OS directory entry without reinterpreting it."""
        self.require_same_root(base)
        if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or any(unsafe_path_character(character) for character in name)
        ):
            raise InvocationError("path-malformed")
        segments = (*base.segments, name)
        self.budget.check_depth(len(segments))
        return RepoPath(self, segments)

    def _absolute(self, path: RepoPath) -> Path:
        self.require_same_root(path)
        return self.absolute.joinpath(*path.segments)

    def display(self, path: RepoPath) -> str:
        self.require_same_root(path)
        return path.as_posix()

    def _components(self, path: RepoPath) -> Iterator[Path]:
        current = self.absolute
        yield current
        for segment in path.segments:
            current /= segment
            yield current

    def identity_snapshot(self, path: RepoPath, *, expected: str) -> IdentitySnapshot:
        self.require_same_root(path)
        self.budget.check_depth(len(path.segments))
        snapshot: list[tuple[Path, PathIdentity]] = []
        components = list(self._components(path))
        for index, component in enumerate(components):
            try:
                metadata = self.backend.lstat(component)
            except (ValueError, UnicodeError) as exc:
                raise InvocationError("path-malformed") from exc
            identity = filesystem_identity(metadata)
            if index == 0 and identity != self.root_identity:
                raise InvocationError("path-identity-changed")
            is_final = index == len(components) - 1
            if is_link_like(metadata) and (not is_final or expected != "symlink"):
                raise InvocationError("path-escape")
            snapshot.append((component, identity))
        mode = snapshot[-1][1][2]
        if expected == "file" and not stat.S_ISREG(mode):
            raise InvocationError("path-type")
        if expected == "directory" and not stat.S_ISDIR(mode):
            raise InvocationError("path-type")
        if expected == "symlink" and not identity_is_link_like(snapshot[-1][1]):
            raise InvocationError("path-type")
        return tuple(snapshot)

    def verify_snapshot(self, before: IdentitySnapshot, *, expected: str) -> None:
        final = before[-1][0]
        try:
            relative = final.relative_to(self.absolute)
        except ValueError as exc:
            raise InvocationError("path-escape") from exc
        after = self.identity_snapshot(
            RepoPath(self, tuple(relative.parts)), expected=expected
        )
        if after != before:
            raise InvocationError("path-identity-changed")

    def _final_metadata(self, path: RepoPath) -> os.stat_result:
        self.require_same_root(path)
        components = list(self._components(path))
        for index, component in enumerate(components[:-1]):
            metadata = self.backend.lstat(component)
            identity = filesystem_identity(metadata)
            if index == 0 and identity != self.root_identity:
                raise InvocationError("path-identity-changed")
            if is_link_like(metadata):
                raise InvocationError("path-escape")
        final = self.backend.lstat(components[-1])
        if len(components) == 1 and filesystem_identity(final) != self.root_identity:
            raise InvocationError("path-identity-changed")
        return final

    def exists(self, path: RepoPath) -> bool:
        try:
            self._final_metadata(path)
            return True
        except FileNotFoundError:
            return False

    def is_symlink(self, path: RepoPath) -> bool:
        try:
            return is_link_like(self._final_metadata(path))
        except FileNotFoundError:
            return False

    def is_file(self, path: RepoPath) -> bool:
        try:
            metadata = self._final_metadata(path)
            return not is_link_like(metadata) and stat.S_ISREG(metadata.st_mode)
        except FileNotFoundError:
            return False

    def is_dir(self, path: RepoPath) -> bool:
        try:
            metadata = self._final_metadata(path)
            return not is_link_like(metadata) and stat.S_ISDIR(metadata.st_mode)
        except FileNotFoundError:
            return False

    def resolve(self, path: RepoPath, *, strict: bool = False) -> RepoPath:
        try:
            before = self.identity_snapshot(path, expected="any")
            resolved = self.backend.resolve(self._absolute(path))
        except FileNotFoundError:
            if strict:
                raise
            return path
        try:
            relative = resolved.relative_to(self.absolute)
        except ValueError as exc:
            raise InvocationError("path-escape") from exc
        canonical = RepoPath(self, tuple(relative.parts))
        self.verify_snapshot(before, expected="any")
        return canonical

    def read_bytes(self, path: RepoPath) -> bytes:
        cached = self._byte_cache.get(path)
        if cached is not None:
            self.verify_snapshot(cached[0], expected="file")
            return cached[1]
        before = self.identity_snapshot(path, expected="file")
        self.budget.charge_work()
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = self.backend.open_read(self._absolute(path), flags)
        try:
            opened_identity = filesystem_identity(self.backend.fstat(descriptor))
            if opened_identity != before[-1][1]:
                raise InvocationError("path-identity-changed")
            chunks: list[bytes] = []
            remaining = self.budget.limits.max_file_bytes + 1
            while remaining:
                chunk = self.backend.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            if filesystem_identity(self.backend.fstat(descriptor)) != opened_identity:
                raise InvocationError("path-identity-changed")
        finally:
            self.backend.close(descriptor)
        self.verify_snapshot(before, expected="file")
        self.budget.charge_bytes(len(content))
        self._byte_cache[path] = (before, content)
        return content

    def read_text(self, path: RepoPath) -> str:
        return self.read_bytes(path).decode("utf-8-sig")

    def read_json(self, path: RepoPath) -> FrozenJson:
        if path not in self._json_cache:
            self._json_cache[path] = parse_json(self.read_text(path))
        return self._json_cache[path]

    def list_entries(self, path: RepoPath) -> list[RepoPath]:
        cached = self._list_cache.get(path)
        if cached is not None:
            self.verify_snapshot(cached[0], expected="directory")
            return list(cached[1])
        before = self.identity_snapshot(path, expected="directory")
        self.budget.charge_work()
        entries: list[RepoPath] = []
        for name in self.backend.list_names(self._absolute(path)):
            entry = self.child(path, name)
            self.budget.charge_entry(len(entry.segments))
            entries.append(entry)
        self.verify_snapshot(before, expected="directory")
        ordered = tuple(
            sorted(entries, key=lambda item: (item.name.casefold(), item.name))
        )
        self._list_cache[path] = (before, ordered)
        return list(ordered)

    def readlink(self, path: RepoPath) -> str:
        cached = self._symlink_cache.get(path)
        if cached is not None:
            self.verify_snapshot(cached[0], expected="symlink")
            return cached[1]
        before = self.identity_snapshot(path, expected="symlink")
        value = self.backend.readlink(self._absolute(path))
        self.verify_snapshot(before, expected="symlink")
        self._symlink_cache[path] = (before, value)
        return value

    def readlink_name(self, path: RepoPath) -> str:
        return PurePosixPath(self.readlink(path).replace("\\", "/")).name

    def is_executable(self, path: RepoPath) -> bool:
        snapshot = self.identity_snapshot(path, expected="file")
        if os.name != "posix":
            return True
        mode = snapshot[-1][1][2]
        return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    def revalidate_all(self) -> None:
        """Fail closed if any cached observation changed before reporting."""
        self.identity_snapshot(self.path, expected="directory")
        for snapshot, _content in self._byte_cache.values():
            self.verify_snapshot(snapshot, expected="file")
        for snapshot, _entries in self._list_cache.values():
            self.verify_snapshot(snapshot, expected="directory")
        for snapshot, _value in self._symlink_cache.values():
            self.verify_snapshot(snapshot, expected="symlink")


def relative(path: RepoPath, target: RepoPath) -> DiagnosticPath:
    if path.root is not target.root:
        raise InvocationError("path-escape")
    return diagnostic_path(path.root.display(path))


def is_within(path: RepoPath, parent: RepoPath) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def first_symlink_component(path: RepoPath, root: RepoPath) -> RepoPath | None:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    current = root
    for part in parts:
        current = current / part
        if current.root.is_symlink(current):
            return current
    return None


def resolve_stable_path(path: RepoPath, *, expected: str) -> RepoPath:
    before = path.root.identity_snapshot(path, expected=expected)
    resolved = path.root.resolve(path, strict=True)
    path.root.verify_snapshot(before, expected=expected)
    return resolved


def read_bytes_bounded(path: RepoPath) -> bytes:
    return path.root.read_bytes(path)


def list_entries_bounded(path: RepoPath) -> list[RepoPath]:
    return path.root.list_entries(path)


def read_text(path: RepoPath, target: RepoPath, findings: list[Finding]) -> str | None:
    try:
        return path.root.read_text(path)
    except UnicodeDecodeError:
        findings.append(finding("not-utf8", relative(path, target)))
    except OSError:
        findings.append(finding("unreadable", relative(path, target)))
    return None

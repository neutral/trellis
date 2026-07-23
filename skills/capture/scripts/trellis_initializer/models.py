"""Immutable trusted models shared by planning and transactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PathIdentity:
    """A no-follow filesystem identity used to reject substitution."""

    device: int
    inode: int
    file_type: int


@dataclass(frozen=True)
class FileOwner:
    """Stable owner metadata that must survive a managed replacement."""

    user: int
    group: int


@dataclass(frozen=True)
class FileState:
    """The exact regular-file state a plan is allowed to replace."""

    exists: bool
    content: bytes | None = None
    mode: int | None = None
    owner: FileOwner | None = None
    identity: PathIdentity | None = field(default=None, compare=False)


@dataclass(frozen=True)
class PlanEntry:
    """One closed managed-file transition."""

    relative: Path
    path: Path
    before: FileState
    after: bytes


@dataclass(frozen=True)
class Plan:
    """An immutable plan rooted at one captured work-folder identity."""

    target: Path
    target_identity: PathIdentity
    entries: tuple[PlanEntry, ...]


@dataclass
class PreparedEntry:
    """Same-directory transaction material for one planned change."""

    plan: PlanEntry
    parent_identities: tuple[tuple[Path, PathIdentity], ...]
    staged: Path | None = None
    staged_identity: PathIdentity | None = None
    recovery: Path | None = None
    recovery_identity: PathIdentity | None = None
    applied_identity: PathIdentity | None = None
    committed: bool = False
    phase: str = "planned"


@dataclass
class OwnedDirectory:
    """A directory created by this transaction and removable by identity."""

    path: Path
    relative: Path
    identity: PathIdentity | None = None

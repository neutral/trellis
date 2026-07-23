"""Read-only planning and preview presentation."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

from .constants import (
    SCRATCH_GITIGNORE,
    SCRATCH_README,
    SUGGESTED_AGENTS_LINE,
    ManagedFile,
)
from .content import decode_utf8, planned_overview, planned_policy_file
from .errors import ErrorCode, SupportError
from .filesystem import FileSystemBackend, ReadRoot, capture_file_state
from .models import FileState, Plan, PlanEntry


def require_replaceable_metadata(
    root: ReadRoot, relative: Path, before: FileState
) -> None:
    """Fail closed when replacement could discard invisible file metadata."""

    if before.exists and not root.backend.complete_acl_xattr_visibility:
        raise SupportError(
            "cannot safely replace managed file because this platform cannot "
            f"verify ACL or extended metadata: {relative.as_posix()}",
            code=ErrorCode.UNSUPPORTED,
        )


def build_immutable_plan(root: ReadRoot) -> Plan:
    managed_files: tuple[tuple[Path, str | None], ...] = (
        (ManagedFile.OVERVIEW.relative, None),
        (ManagedFile.SCRATCH_GITIGNORE.relative, SCRATCH_GITIGNORE),
        (ManagedFile.SCRATCH_README.relative, SCRATCH_README),
    )
    states = {relative: root.inspect(relative) for relative, _ in managed_files}
    entries: list[PlanEntry] = []

    overview_relative = managed_files[0][0]
    overview_path = root.target / overview_relative
    overview_before = states[overview_relative]
    overview_content = planned_overview(overview_path, overview_before)
    if overview_content is not None:
        require_replaceable_metadata(root, overview_relative, overview_before)
        entries.append(
            PlanEntry(
                relative=overview_relative,
                path=overview_path,
                before=overview_before,
                after=overview_content,
            )
        )

    for relative, expected in managed_files[1:]:
        path = root.target / relative
        before = states[relative]
        assert expected is not None
        content = planned_policy_file(path, before, expected)
        if content is not None:
            require_replaceable_metadata(root, relative, before)
            entries.append(
                PlanEntry(
                    relative=relative,
                    path=path,
                    before=before,
                    after=content,
                )
            )
    return Plan(root.target, root.identity, tuple(entries))


def revalidate_entry(
    target: Path,
    entry: PlanEntry,
    backend: FileSystemBackend | None = None,
) -> None:
    current = capture_file_state(target, entry.relative, backend)
    if current != entry.before or current.identity != entry.before.identity:
        raise SupportError(
            f"managed file changed after planning: {entry.relative.as_posix()}; "
            "rerun the preview",
            code=ErrorCode.DRIFT,
        )


def agents_references_handbook(
    target: Path, backend: FileSystemBackend | None = None
) -> bool:
    root = ReadRoot.open(target, backend)
    return root.agents_references_handbook()


def print_agents_note(target: Path, backend: FileSystemBackend | None = None) -> None:
    if agents_references_handbook(target, backend):
        print("AGENTS.md already references _handbook; Trellis left it unchanged.")
        return
    print("AGENTS.md has no _handbook reference. Trellis did not edit it.")
    print("Suggested line for the user to add manually:")
    print(SUGGESTED_AGENTS_LINE)


def display_path(path: Path, target: Path) -> str:
    return path.relative_to(target).as_posix()


def preview_text(path: Path, content: bytes) -> str:
    return decode_utf8(path, content).replace("\r\n", "\n")


def print_preview(plan: list[PlanEntry] | tuple[PlanEntry, ...], target: Path) -> None:
    if not plan:
        print("No changes needed. Trellis handbook is already initialized.")
        return
    print("Planned changes (not written):")
    for entry in plan:
        relative = entry.relative.as_posix()
        action = "update" if entry.before.exists else "create"
        before = entry.before.content or b""
        print(f"\n{action}: {relative}")
        diff = difflib.unified_diff(
            preview_text(entry.path, before).splitlines(keepends=True),
            preview_text(entry.path, entry.after).splitlines(keepends=True),
            fromfile=relative if entry.before.exists else "/dev/null",
            tofile=relative,
        )
        sys.stdout.writelines(diff)
    print("\nRerun with --write to apply this preview.")

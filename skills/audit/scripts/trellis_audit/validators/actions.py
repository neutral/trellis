"""Focused actions validators for Trellis Audit."""

from __future__ import annotations

from ..context import AuditContext
from ..diagnostics import DiagnosticPath, Finding, diagnostic_path, finding
from ..filesystem import (
    RepoPath,
    first_symlink_component,
    is_within,
    list_entries_bounded,
    read_text,
    relative,
)
from ..models import CaptureLink
from .action_docs import check_action_page, check_action_page_agreement
from .core import (
    ACTION_ID_RE,
    ACTION_SEGMENT_RE,
    RESERVED_ACTION_TOP_LEVEL,
    safe_os_error,
)
from .javascript import check_action_static_contract
from .manifest import check_action_manifest
from .runtime import (
    check_action_source_inventory,
    check_npm_policy,
    check_package,
    check_runtime_file,
)


def report_action_id_issues(
    action_id: str, location: DiagnosticPath, findings: list[Finding]
) -> None:
    if not ACTION_ID_RE.fullmatch(action_id):
        findings.append(
            finding(
                "action-id", location, f"invalid slash-delimited action id: {action_id}"
            )
        )
    top_level = action_id.split("/", 1)[0].casefold()
    if top_level in RESERVED_ACTION_TOP_LEVEL:
        findings.append(
            finding(
                "action-id-reserved",
                location,
                f"reserved top-level Action segment: {top_level}",
            )
        )


def inventory_action_directories(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> tuple[dict[str, RepoPath], dict[str, RepoPath]]:
    actions_root = target / "_handbook" / "_cli" / "actions"
    if not context.root.exists(actions_root) and not context.root.is_symlink(
        actions_root
    ):
        return {}, {}
    if (
        context.root.is_symlink(actions_root)
        or not context.root.is_dir(actions_root)
        or not is_within(context.root.resolve(actions_root), target)
    ):
        findings.append(
            finding(
                "action-area",
                relative(actions_root, target),
                "Action area must be a work-folder-local regular directory",
            )
        )
        return {}, {}
    result: dict[str, RepoPath] = {}
    topology: dict[str, RepoPath] = {}
    folded: dict[str, str] = {}
    allowed_leaf_entries = {"action.json", "run.mjs", "run.test.mjs"}

    def visit_group(group: RepoPath, segments: tuple[str, ...]) -> None:
        try:
            entries = list_entries_bounded(group)
        except OSError as exc:
            findings.append(
                finding(
                    "action-directory-malformed",
                    relative(group, target),
                    f"could not inventory Action group: {safe_os_error(exc)}",
                )
            )
            return
        for child in entries:
            child_segments = (*segments, child.name)
            child_id = "/".join(child_segments)
            location = relative(child, target)
            if context.root.is_symlink(child):
                findings.append(
                    finding(
                        "action-directory-symlink",
                        location,
                        "Action groups and leaves must not be symlinks",
                    )
                )
                continue
            if not context.root.is_dir(child):
                findings.append(
                    finding(
                        "action-group-content",
                        location,
                        "Action group directories may contain only regular subdirectories",
                    )
                )
                continue

            if not ACTION_SEGMENT_RE.fullmatch(child.name):
                findings.append(
                    finding(
                        "action-id",
                        location,
                        f"invalid Action path segment: {child.name}",
                    )
                )
            topology[child_id] = child
            if (
                len(child_segments) == 1
                and child.name.casefold() in RESERVED_ACTION_TOP_LEVEL
            ):
                findings.append(
                    finding(
                        "action-id-reserved",
                        location,
                        f"reserved top-level Action segment: {child.name}",
                    )
                )

            folded_id = child_id.casefold()
            if folded_id in folded:
                findings.append(
                    finding(
                        "action-case-collision",
                        location,
                        "Action path collides case-insensitively with "
                        f"{folded[folded_id]}",
                    )
                )
            else:
                folded[folded_id] = child_id

            try:
                child_entries = list_entries_bounded(child)
            except OSError as exc:
                findings.append(
                    finding(
                        "action-directory-malformed",
                        location,
                        f"could not inventory Action directory: {safe_os_error(exc)}",
                    )
                )
                continue
            names = {entry.name for entry in child_entries}
            action_entries = names.intersection(allowed_leaf_entries)
            directories = [
                entry
                for entry in child_entries
                if not context.root.is_symlink(entry) and context.root.is_dir(entry)
            ]
            if not child_entries:
                findings.append(
                    finding(
                        "action-group-empty",
                        location,
                        "Action group directories must not be empty",
                    )
                )
            elif action_entries:
                result[child_id] = child
                if directories:
                    findings.append(
                        finding(
                            "action-leaf-child",
                            location,
                            "Action leaf directories must not contain child groups or Actions",
                        )
                    )
            if not action_entries and child_entries:
                visit_group(child, child_segments)

    visit_group(actions_root, ())
    return result, topology


def check_action_runtime(
    context: AuditContext,
    target: RepoPath,
    action_captures: list[CaptureLink],
    findings: list[Finding],
) -> None:
    directories, directory_topology = inventory_action_directories(
        context, target, findings
    )
    cli_root = target / "_handbook" / "_cli"
    if (
        not action_captures
        and not directory_topology
        and not context.root.exists(cli_root)
        and not context.root.is_symlink(cli_root)
    ):
        return
    if (
        context.root.is_symlink(cli_root)
        or not context.root.is_dir(cli_root)
        or not is_within(context.root.resolve(cli_root), target)
    ):
        findings.append(
            finding(
                "cli-root",
                diagnostic_path("_handbook/_cli"),
                "Action runtime must be a work-folder-local regular directory",
            )
        )
    launcher = target / "trellis"
    if check_runtime_file(
        context,
        target,
        "trellis",
        findings,
        "trellis-launcher",
        "root trellis launcher",
    ):
        content = read_text(launcher, target, findings)
        if content is not None and "// trellis-action-cli-format: 4" not in content:
            findings.append(
                finding(
                    "trellis-launcher-format",
                    diagnostic_path("trellis"),
                    "v4 launcher format marker is missing",
                )
            )
        if not context.root.is_executable(launcher):
            findings.append(
                finding(
                    "trellis-launcher-mode",
                    diagnostic_path("trellis"),
                    "launcher is not executable",
                )
            )
    runner = target / "_handbook" / "_cli" / "bin" / "trellis.mjs"
    if check_runtime_file(
        context,
        target,
        "_handbook/_cli/bin/trellis.mjs",
        findings,
        "trellis-runner",
        "Node action runner",
    ):
        content = read_text(runner, target, findings)
        if content is not None and "// trellis-action-cli-format: 4" not in content:
            findings.append(
                finding(
                    "trellis-runner-format",
                    diagnostic_path("_handbook/_cli/bin/trellis.mjs"),
                    "v4 runner format marker is missing",
                )
            )
    check_runtime_file(
        context,
        target,
        "_handbook/_cli/src/cli.mjs",
        findings,
        "trellis-cli",
        "Node action CLI",
    )
    check_runtime_file(
        context,
        target,
        "_handbook/_cli/src/guard.mjs",
        findings,
        "trellis-guard",
        "Node Action guard",
    )
    check_runtime_file(
        context,
        target,
        "_handbook/_cli/test/cli.test.mjs",
        findings,
        "trellis-cli-test",
        "Node action CLI test",
    )
    check_npm_policy(context, target, findings)
    check_runtime_file(
        context,
        target,
        "_handbook/_cli/.gitignore",
        findings,
        "trellis-gitignore",
        "tool ignore policy",
    )
    check_package(context, target, findings)

    pages: dict[str, RepoPath] = {}
    namespace_folded: dict[str, tuple[str, RepoPath]] = {}
    for directory_id, directory_path in sorted(
        directory_topology.items(), key=lambda item: (item[0].casefold(), item[0])
    ):
        namespace_folded.setdefault(
            directory_id.casefold(), (directory_id, directory_path)
        )
    page_root = target / "_handbook" / "actions"
    for capture in action_captures:
        if first_symlink_component(capture.target, page_root) is not None:
            continue
        try:
            page_relative = capture.target.relative_to(page_root)
        except ValueError:
            findings.append(
                finding(
                    "action-page-location",
                    relative(capture.target, target),
                    "Action page must remain under _handbook/actions/",
                )
            )
            continue
        if page_relative.suffix != ".md":
            findings.append(
                finding(
                    "action-page-location",
                    relative(capture.target, target),
                    "Action page must be a Markdown file mirrored under _handbook/actions/",
                )
            )
            continue
        action_id = page_relative.with_suffix("").as_posix()
        report_action_id_issues(action_id, relative(capture.target, target), findings)
        segments = action_id.split("/")
        for end in range(1, len(segments) + 1):
            prefix = "/".join(segments[:end])
            folded_prefix = prefix.casefold()
            existing = namespace_folded.get(folded_prefix)
            if existing is not None and existing[0] != prefix:
                findings.append(
                    finding(
                        "action-case-collision",
                        relative(capture.target, target),
                        "Action page path collides case-insensitively at "
                        f"{prefix!r} with {existing[0]!r}",
                    )
                )
            else:
                namespace_folded.setdefault(folded_prefix, (prefix, capture.target))
        pages.setdefault(action_id, capture.target)

    for action_id in sorted(set(pages) | set(directories), key=str.casefold):
        page_path = pages.get(action_id)
        action_dir = directories.get(action_id)
        if page_path is not None:
            check_action_page(context, page_path, action_id, target, findings)
        if action_dir is None:
            findings.append(
                finding(
                    "action-implementation-missing",
                    relative(target / "_handbook/_cli/actions" / action_id, target),
                    "Action directory is missing",
                )
            )
            continue
        if page_path is None:
            findings.append(
                finding(
                    "action-orphan",
                    relative(action_dir, target),
                    "Action directory has no marked handbook entry",
                )
            )
        check_action_source_inventory(context, action_dir, target, findings)
        manifest = check_action_manifest(
            context, action_id, action_dir, page_path, target, findings
        )
        if manifest is None:
            continue
        if page_path is not None and manifest.get("format") == 2:
            page = check_action_page(context, page_path, action_id, target, [])
            if page is not None:
                check_action_page_agreement(
                    context, action_id, page, manifest, target, findings
                )
        check_action_static_contract(
            context, action_id, action_dir, manifest, target, findings
        )

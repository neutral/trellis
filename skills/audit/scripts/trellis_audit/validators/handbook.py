"""Focused handbook validators for Trellis Audit."""

from __future__ import annotations

import math
from urllib.parse import unquote, urlsplit

from ..context import WORK_UNIT_BYTES, AuditContext
from ..diagnostics import (
    Finding,
    InvocationError,
    Suggestion,
    diagnostic_path,
    finding,
    suggestion,
    unsafe_path_character,
)
from ..filesystem import (
    RepoPath,
    first_symlink_component,
    is_within,
    list_entries_bounded,
    read_text,
    relative,
    resolve_stable_path,
)
from ..models import CaptureLink
from .core import (
    CAPTURE_MARKER_RE,
    FORMAT_MARKER,
    HANDBOOK_END,
    HANDBOOK_START,
    HEADING_RE,
    LINK_RE,
    PLAYBOOK_HEADINGS,
    check_regular_file,
    safe_os_error,
)
from .markdown import markdown_structure_view


def check_agents_reference(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> Suggestion | None:
    path = target / "AGENTS.md"
    content = ""
    if context.root.is_file(path) and not context.root.is_symlink(path):
        content = read_text(path, target, findings) or ""
    if "_handbook" in content:
        return None
    return suggestion("agents-handbook-reference", diagnostic_path("AGENTS.md"))


def extract_target(raw_destination: str) -> str | None:
    destination = raw_destination.strip()
    if any(unsafe_path_character(character) for character in destination):
        raise ValueError("link destination contains a control character")
    if destination.startswith("<") and ">" in destination:
        destination = destination[1 : destination.index(">")]
    else:
        destination = destination.split(maxsplit=1)[0]
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path:
        return ""
    decoded = unquote(parsed.path).replace("\\", "/")
    if any(unsafe_path_character(character) for character in decoded):
        raise ValueError("decoded link destination contains a control character")
    return decoded


def capture_marker(
    path: RepoPath, target: RepoPath, findings: list[Finding]
) -> tuple[str, int] | None:
    content = read_text(path, target, findings)
    if content is None:
        return None
    structure = markdown_structure_view(path.root.budget, content)
    matches: list[tuple[str, str]] = []
    for match in CAPTURE_MARKER_RE.finditer(structure):
        path.root.budget.charge_work()
        matches.append((match.group(1), match.group(2)))
    if len(matches) != 1:
        findings.append(
            finding(
                "capture-marker",
                relative(path, target),
                f"expected one Trellis capture marker; found {len(matches)}",
            )
        )
        return None
    kind, raw_format = matches[0]
    expected = "1" if kind == "playbook" else "2"
    if raw_format != expected:
        findings.append(
            finding(
                "capture-format",
                relative(path, target),
                f"expected {kind} format {expected}; found an unsupported format",
            )
        )
        return kind, -1
    return kind, int(expected)


def check_playbook_page(
    context: AuditContext, path: RepoPath, target: RepoPath, findings: list[Finding]
) -> None:
    content = read_text(path, target, findings)
    if content is None:
        return
    structure = markdown_structure_view(context, content)
    heading_counts: dict[str, int] = {}
    for match in HEADING_RE.finditer(structure):
        context.budget.charge_work()
        if not match.group(0).startswith("## "):
            continue
        heading = match.group(1).strip()
        heading_counts[heading] = heading_counts.get(heading, 0) + 1
    for heading in PLAYBOOK_HEADINGS:
        count = heading_counts.get(heading, 0)
        if count != 1:
            findings.append(
                finding(
                    "playbook-page-heading",
                    relative(path, target),
                    f"Playbook page must contain one {heading} heading; found {count}",
                )
            )


def scan_managed_links(
    context: AuditContext,
    block: str,
    structure: str,
    start_line: int,
    handbook: RepoPath,
    target: RepoPath,
    findings: list[Finding],
) -> list[CaptureLink]:
    lines = structure.splitlines()
    handbook.root.budget.charge_work(
        max(1, math.ceil(len(block.encode("utf-8")) / WORK_UNIT_BYTES))
    )
    current_section: str | None = None
    headings = {"playbooks": 0, "actions": 0}
    captures: list[CaptureLink] = []
    seen: dict[RepoPath, int] = {}

    for index, line in enumerate(lines):
        handbook.root.budget.charge_work(
            max(1, math.ceil(len(line.encode("utf-8")) / 256))
        )
        heading = HEADING_RE.match(line)
        if heading:
            normalized = heading.group(1).strip().lower()
            current_section = normalized if normalized in headings else None
            if current_section:
                headings[current_section] += 1
            continue
        if current_section is None:
            continue

        for match in LINK_RE.finditer(line):
            handbook.root.budget.charge_work()
            raw = match.group(1)
            line_number = start_line + index
            location = diagnostic_path(f"_handbook/overview.md:{line_number}")
            try:
                destination = extract_target(raw)
            except (ValueError, UnicodeError):
                findings.append(
                    finding(
                        "capture-link-malformed",
                        location,
                        "capture link destination is malformed or contains control characters",
                    )
                )
                continue
            if destination is None:
                findings.append(
                    finding(
                        "capture-external",
                        location,
                        f"{current_section} capture must use a work-folder-local link; external destination redacted",
                    )
                )
                continue
            if not destination:
                findings.append(
                    finding(
                        "capture-anchor", location, "capture link has no file target"
                    )
                )
                continue

            try:
                unresolved = handbook / destination
                lexical = unresolved
                symlink_component = first_symlink_component(lexical, handbook)
                expected_root = context.root.resolve(handbook / current_section)
                resolved = context.root.resolve(unresolved)
            except InvocationError as exc:
                findings.append(
                    finding(
                        "capture-escapes"
                        if exc.code == "path-escape"
                        else "capture-link-malformed",
                        location,
                    )
                )
                continue
            except (OSError, RuntimeError, ValueError, UnicodeError):
                findings.append(
                    finding(
                        "capture-link-malformed",
                        location,
                        "capture link could not be resolved safely",
                    )
                )
                continue
            if not is_within(resolved, context.root.resolve(handbook)):
                findings.append(
                    finding(
                        "capture-escapes",
                        location,
                        "capture target leaves _handbook/; destination redacted",
                    )
                )
                continue
            if not is_within(resolved, expected_root):
                findings.append(
                    finding(
                        "capture-section",
                        location,
                        f"{current_section} entry targets a different handbook area; destination redacted",
                    )
                )
                continue
            if resolved in seen:
                findings.append(
                    finding(
                        "capture-duplicate",
                        location,
                        f"target duplicates the entry on line {seen[resolved]}; destination redacted",
                    )
                )
            else:
                seen[resolved] = line_number

            if symlink_component is not None:
                findings.append(
                    finding(
                        "capture-symlink",
                        location,
                        "capture path must not contain a symlink: "
                        f"{relative(symlink_component, target)}",
                    )
                )
            elif not context.root.exists(unresolved):
                findings.append(
                    finding(
                        "capture-missing",
                        location,
                        "capture target does not exist; destination redacted",
                    )
                )
            elif not context.root.is_file(unresolved):
                findings.append(
                    finding(
                        "capture-not-file",
                        location,
                        "capture target is not a file; destination redacted",
                    )
                )
            else:
                marker = capture_marker(unresolved, target, findings)
                expected_kind = current_section[:-1]
                if marker is not None and marker[0] != expected_kind:
                    findings.append(
                        finding(
                            "capture-kind",
                            relative(unresolved, target),
                            f"capture marker says {marker[0]}; index section says {expected_kind}",
                        )
                    )
                if current_section == "playbooks":
                    check_playbook_page(context, unresolved, target, findings)

            captures.append(
                CaptureLink(
                    section=current_section,
                    target=lexical,
                    resolved=resolved,
                    line=line_number,
                )
            )

    for name, count in headings.items():
        if count != 1:
            findings.append(
                finding(
                    "handbook-section",
                    diagnostic_path("_handbook/overview.md"),
                    f"expected one level-two {name.title()} heading in the managed block; found {count}",
                )
            )
    return captures


def check_marked_orphans(
    context: AuditContext,
    handbook: RepoPath,
    target: RepoPath,
    captures: list[CaptureLink],
    findings: list[Finding],
) -> list[CaptureLink]:
    indexed = {
        capture.resolved
        for capture in captures
        if first_symlink_component(capture.target, handbook) is None
        and context.root.is_file(capture.target)
    }
    orphans: list[CaptureLink] = []

    def regular_markdown_files(root: RepoPath) -> list[RepoPath]:
        files: list[RepoPath] = []
        pending = [root]
        while pending:
            directory = pending.pop()
            try:
                entries = list(reversed(list_entries_bounded(directory)))
            except OSError as exc:
                findings.append(
                    finding(
                        "capture-area-unreadable",
                        relative(directory, target),
                        f"could not inventory capture area: {safe_os_error(exc)}",
                    )
                )
                continue
            for entry in entries:
                if context.root.is_symlink(entry):
                    continue
                if context.root.is_dir(entry):
                    pending.append(entry)
                elif context.root.is_file(entry) and entry.suffix == ".md":
                    files.append(entry)
        return sorted(files, key=lambda item: relative(item, target).casefold())

    for section, singular in (("playbooks", "playbook"), ("actions", "action")):
        section_root = handbook / section
        if not context.root.exists(section_root):
            continue
        if context.root.is_symlink(section_root) or not context.root.is_dir(
            section_root
        ):
            findings.append(
                finding(
                    "capture-area",
                    relative(section_root, target),
                    "capture area must be a regular directory",
                )
            )
            continue
        for child in regular_markdown_files(section_root):
            content = read_text(child, target, findings)
            if content is None:
                continue
            structure = markdown_structure_view(context, content)
            markers: list[tuple[str, str]] = []
            for marker in CAPTURE_MARKER_RE.finditer(structure):
                context.budget.charge_work()
                markers.append((marker.group(1), marker.group(2)))
            if not markers:
                continue
            if len(markers) == 1 and markers[0][0] != singular:
                findings.append(
                    finding(
                        "capture-kind",
                        relative(child, target),
                        f"capture marker says {markers[0][0]}; directory expects {singular}",
                    )
                )
            try:
                resolved_child = resolve_stable_path(child, expected="file")
            except InvocationError:
                findings.append(
                    finding(
                        "capture-path-unstable",
                        relative(child, target),
                        "capture path could not be resolved with a stable local identity",
                    )
                )
                continue
            if len(markers) == 1 and resolved_child not in indexed:
                marker_kind, raw_format = markers[0]
                expected_format = "1" if marker_kind == "playbook" else "2"
                if raw_format != expected_format:
                    findings.append(
                        finding(
                            "capture-format",
                            relative(child, target),
                            f"expected {marker_kind} format {expected_format}; marker is invalid or unsupported",
                        )
                    )
            if resolved_child not in indexed:
                findings.append(
                    finding(
                        "capture-orphan",
                        relative(child, target),
                        "marked capture is not represented in the managed handbook block",
                    )
                )
                if len(markers) == 1 and markers[0][0] == singular:
                    orphans.append(
                        CaptureLink(
                            section=section,
                            target=child,
                            resolved=resolved_child,
                            line=0,
                        )
                    )
    return orphans


def check_handbook(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> list[CaptureLink]:
    handbook = target / "_handbook"
    path = handbook / "overview.md"
    if not check_regular_file(
        context, path, target, findings, "handbook", "handbook overview"
    ):
        if (
            context.root.exists(handbook)
            and context.root.is_dir(handbook)
            and not context.root.is_symlink(handbook)
        ):
            return check_marked_orphans(context, handbook, target, [], findings)
        return []
    if context.root.is_symlink(handbook):
        findings.append(
            finding(
                "handbook-symlink",
                diagnostic_path("_handbook"),
                "handbook directory must not be a symlink",
            )
        )
        return []
    content = read_text(path, target, findings)
    if content is None:
        return check_marked_orphans(context, handbook, target, [], findings)
    structure = markdown_structure_view(context, content)
    content_scan_units = max(
        1, math.ceil(len(content.encode("utf-8")) / WORK_UNIT_BYTES)
    )
    context.budget.charge_work(content_scan_units * 3)
    starts = structure.count(HANDBOOK_START)
    ends = structure.count(HANDBOOK_END)
    if starts != 1 or ends != 1:
        findings.append(
            finding(
                "handbook-markers",
                diagnostic_path("_handbook/overview.md"),
                f"expected one managed marker pair; found {starts} start and {ends} end",
            )
        )
        return check_marked_orphans(context, handbook, target, [], findings)
    start = structure.index(HANDBOOK_START)
    end = structure.index(HANDBOOK_END)
    if start > end:
        findings.append(
            finding(
                "handbook-marker-order",
                diagnostic_path("_handbook/overview.md"),
                "end marker precedes start marker",
            )
        )
        return check_marked_orphans(context, handbook, target, [], findings)
    block = content[start : end + len(HANDBOOK_END)]
    block_structure = structure[start : end + len(HANDBOOK_END)]
    context.budget.charge_work(
        max(1, math.ceil(len(block.encode("utf-8")) / WORK_UNIT_BYTES))
    )
    if block_structure.count(FORMAT_MARKER) != 1:
        findings.append(
            finding(
                "handbook-format",
                diagnostic_path("_handbook/overview.md"),
                f"expected one {FORMAT_MARKER!r} inside the managed block",
            )
        )
    start_line = content[:start].count("\n") + 1
    captures = scan_managed_links(
        context,
        block,
        block_structure,
        start_line,
        handbook,
        target,
        findings,
    )
    orphans = check_marked_orphans(context, handbook, target, captures, findings)
    return captures + orphans

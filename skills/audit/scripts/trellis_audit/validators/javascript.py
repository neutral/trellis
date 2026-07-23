"""Focused javascript validators for Trellis Audit."""

from __future__ import annotations

import json
import math
import re

from ..context import WORK_UNIT_BYTES, AuditContext
from ..diagnostics import (
    Finding,
    InvocationError,
    diagnostic_path,
    finding,
    unsafe_path_character,
)
from ..filesystem import (
    RepoPath,
    is_within,
    read_text,
    relative,
    resolve_stable_path,
)
from ..models import ActionManifest, is_json_array, is_json_object
from .core import (
    ACCESS_CHANGE_RE,
    DELETE_RE,
    DIRECT_READ_RE,
    DIRECT_WRITE_RE,
    DYNAMIC_IMPORT_RE,
    EXPORT_FROM_RE,
    FORBIDDEN_MODULES,
    FORBIDDEN_PACKAGE_MODULES,
    FS_ACCESS_CHANGE_APIS,
    FS_DELETE_APIS,
    FS_READ_APIS,
    FS_UNBOUNDED_READ_APIS,
    FS_WRITE_APIS,
    GENERATED_CODE_RE,
    IMPORT_RE,
    LITERAL_READ_RE,
    NETWORK_GLOBAL_RE,
    NODE_BUILTINS,
    PACKAGE_NAME_RE,
    PROCESS_CONTROL_RE,
    PROCESS_ENV_RE,
    REQUIRE_RE,
    RUNTIME_BYPASS_RE,
    SHELL_RE,
    TODO_TEST_RE,
    WRITE_OPEN_RE,
)
from .manifest import normalize_relative_path, valid_relative_path


class StaticAnalysisAmbiguity(Exception):
    """JavaScript syntax that the bounded tokenizer cannot classify safely."""


PROCESS_CONTROL_PROPERTIES = frozenset(
    {
        "_debugEnd",
        "_debugProcess",
        "_kill",
        "chdir",
        "execve",
        "initgroups",
        "kill",
        "loadEnvFile",
        "openStdin",
        "setegid",
        "seteuid",
        "setgid",
        "setgroups",
        "setuid",
        "umask",
    }
)
RUNTIME_BYPASS_PROPERTIES = frozenset(
    {"_linkedBinding", "binding", "dlopen", "getBuiltinModule", "kill"}
)


def javascript_inspection_view(content: str, *, mask_strings: bool) -> str:
    """Return one linear, non-executing view of code, including template expressions."""
    length = len(content)
    result = ["\n" if character == "\n" else " " for character in content]
    # Frames are (kind, expression brace depth, regex-can-start). Template text
    # and regex literals are masked; code inside ${...} is visited exactly once.
    frames: list[tuple[str, int, bool]] = [("code", 0, True)]
    index = 0

    def scan_quoted(start: int, quote: str) -> int:
        cursor = start
        while cursor < length:
            character = content[cursor]
            if not mask_strings:
                result[cursor] = character
            if character == "\\":
                cursor += 1
                if cursor < length:
                    if not mask_strings:
                        result[cursor] = content[cursor]
                    cursor += 1
                continue
            cursor += 1
            if character == quote and cursor > start + 1:
                break
        return cursor

    def scan_regex(start: int) -> int:
        cursor = start + 1
        in_character_class = False
        while cursor < length:
            character = content[cursor]
            if character in {"\n", "\r"}:
                raise InvocationError("content-malformed")
            if character == "\\":
                cursor += 2
                continue
            if character == "[":
                in_character_class = True
            elif character == "]":
                in_character_class = False
            elif character == "/" and not in_character_class:
                cursor += 1
                while cursor < length and (
                    content[cursor].isalpha() or content[cursor] in {"$", "_"}
                ):
                    cursor += 1
                return cursor
            cursor += 1
        raise InvocationError("content-malformed")

    while index < length:
        kind, expression_depth, regex_can_start = frames[-1]
        character = content[index]
        following = content[index + 1] if index + 1 < length else ""
        if kind == "template":
            if character == "\\":
                index = min(length, index + 2)
                continue
            if character == "`":
                frames.pop()
                if frames:
                    parent_kind, parent_depth, _ = frames[-1]
                    frames[-1] = (parent_kind, parent_depth, False)
                index += 1
                continue
            if character == "$" and following == "{":
                if len(frames) >= 256:
                    raise InvocationError("content-malformed")
                frames.append(("code", 1, True))
                index += 2
                continue
            index += 1
            continue

        if character == "/" and following == "/":
            newline = content.find("\n", index + 2)
            index = length if newline == -1 else newline
            continue
        if character == "/" and following == "*":
            closing = content.find("*/", index + 2)
            index = length if closing == -1 else closing + 2
            continue
        if character in {"'", '"'}:
            index = scan_quoted(index, character)
            frames[-1] = (kind, expression_depth, False)
            continue
        if character == "`":
            if len(frames) >= 256:
                raise InvocationError("content-malformed")
            frames.append(("template", 0, True))
            index += 1
            continue
        if character == "/":
            if expression_depth and not regex_can_start:
                raise StaticAnalysisAmbiguity
            if regex_can_start:
                index = scan_regex(index)
                frames[-1] = (kind, expression_depth, False)
            else:
                result[index] = character
                frames[-1] = (kind, expression_depth, True)
                index += 1
            continue
        if character.isspace():
            result[index] = character
            index += 1
            continue
        if character.isalpha() or character in {"$", "_"}:
            cursor = index + 1
            while cursor < length and (
                content[cursor].isalnum() or content[cursor] in {"$", "_"}
            ):
                cursor += 1
            result[index:cursor] = content[index:cursor]
            token = content[index:cursor]
            frames[-1] = (
                kind,
                expression_depth,
                token
                in {
                    "await",
                    "case",
                    "delete",
                    "do",
                    "else",
                    "in",
                    "instanceof",
                    "new",
                    "of",
                    "return",
                    "throw",
                    "typeof",
                    "void",
                    "yield",
                },
            )
            index = cursor
            continue
        if expression_depth and character == "{":
            frames[-1] = (kind, expression_depth + 1, True)
        elif expression_depth and character == "}":
            expression_depth -= 1
            if expression_depth == 0:
                frames.pop()
                index += 1
                continue
            frames[-1] = (kind, expression_depth, False)
        elif character in {
            "(",
            "[",
            "{",
            ",",
            ";",
            ":",
            "?",
            "=",
            "!",
            "&",
            "|",
            "+",
            "-",
            "*",
            "%",
            "^",
            "~",
            "<",
            ">",
        }:
            if character in {"+", "-"} and following == character:
                frames[-1] = (kind, expression_depth, regex_can_start)
            else:
                frames[-1] = (kind, expression_depth, True)
        else:
            frames[-1] = (kind, expression_depth, False)
        result[index] = character
        index += 1
    if len(frames) != 1 or frames[0][0] != "code":
        raise InvocationError("content-malformed")
    return "".join(result)


def package_root(specifier: str) -> str:
    if specifier.startswith("@"):
        return "/".join(specifier.split("/")[:2])
    return specifier.split("/", 1)[0]


def static_imports(content: str) -> tuple[list[str], bool]:
    without_comments = javascript_inspection_view(content, mask_strings=False)
    imports = IMPORT_RE.findall(without_comments) + EXPORT_FROM_RE.findall(
        without_comments
    )
    dynamic = False
    for expression in DYNAMIC_IMPORT_RE.findall(without_comments):
        literal = re.fullmatch(r"[\"']([^\"']+)[\"']", expression.strip())
        if literal:
            imports.append(literal.group(1))
        else:
            dynamic = True
    for expression in REQUIRE_RE.findall(without_comments):
        literal = re.fullmatch(r"[\"']([^\"']+)[\"']", expression.strip())
        if literal:
            imports.append(literal.group(1))
        else:
            dynamic = True
    return imports, dynamic


def charge_text_scan(context: AuditContext, content: str, *, passes: int = 1) -> None:
    """Charge for one or more complete scans of already-read text."""
    if passes < 0:
        raise ValueError("scan passes must not be negative")
    if passes == 0:
        return
    units = max(1, math.ceil(len(content.encode("utf-8")) / WORK_UNIT_BYTES))
    context.budget.charge_work(units * passes)


def static_bracket_properties(
    context: AuditContext, content: str, owners: set[str]
) -> tuple[set[str], bool]:
    """Return visible static bracket properties and whether any are computed."""
    source = javascript_inspection_view(content, mask_strings=False)
    code = javascript_inspection_view(content, mask_strings=True)
    charge_text_scan(context, source)
    properties: set[str] = set()
    computed = False
    pattern = re.compile(
        r"\b(?P<owner>[A-Za-z_$][A-Za-z0-9_$]*)\s*(?:\?\.\s*)?\[\s*(?P<value>[^\]\r\n]+)\s*\]"
    )
    for match in pattern.finditer(source):
        owner = match.group("owner")
        if owner not in owners:
            continue
        owner_start, owner_end = match.span("owner")
        if code[owner_start:owner_end] != source[owner_start:owner_end]:
            continue
        context.budget.charge_work()
        value = match.group("value").strip()
        literal = re.fullmatch(r"([\"'])([A-Za-z_$][A-Za-z0-9_$]*)\1", value)
        if literal is None:
            computed = True
        else:
            properties.add(literal.group(2))
    return properties, computed


def static_dot_properties(
    context: AuditContext, content: str, owners: set[str]
) -> set[str]:
    """Return visible dot or optional-chain properties for selected owners."""
    if not owners:
        return set()
    code = javascript_inspection_view(content, mask_strings=True)
    charge_text_scan(context, code)
    owner_pattern = "|".join(re.escape(owner) for owner in sorted(owners))
    return {
        match.group("property")
        for match in re.finditer(
            rf"\b(?:{owner_pattern})\s*(?:\?\.|\.)\s*(?P<property>[A-Za-z_$][A-Za-z0-9_$]*)",
            code,
        )
    }


def destructured_properties(
    context: AuditContext, content: str, owners: set[str]
) -> tuple[set[str], bool]:
    """Return properties visibly destructured from selected capability owners."""
    if not owners:
        return set(), False
    source = javascript_inspection_view(content, mask_strings=False)
    code = javascript_inspection_view(content, mask_strings=True)
    owner_pattern = "|".join(re.escape(owner) for owner in sorted(owners))
    pattern = re.compile(
        rf"\b(?P<keyword>const|let|var)\s*\{{(?P<bindings>[^}}]*)\}}\s*=\s*(?:{owner_pattern})\b"
    )
    charge_text_scan(context, source)
    properties: set[str] = set()
    unresolved = False
    for match in pattern.finditer(source):
        keyword_start, keyword_end = match.span("keyword")
        if code[keyword_start:keyword_end] != source[keyword_start:keyword_end]:
            continue
        for raw_binding in match.group("bindings").split(","):
            context.budget.charge_work()
            parsed = re.fullmatch(
                r"\s*([A-Za-z_$][A-Za-z0-9_$]*)(?:\s*:\s*[A-Za-z_$][A-Za-z0-9_$]*)?\s*",
                raw_binding,
            )
            if parsed is None:
                unresolved = True
            else:
                properties.add(parsed.group(1))
    return properties, unresolved


def aliases_runtime_owner(context: AuditContext, content: str) -> bool:
    """Return whether a runtime capability root is assigned to another name."""
    code = javascript_inspection_view(content, mask_strings=True)
    charge_text_scan(context, code)
    return bool(
        re.search(
            r"\b(?:const|let|var)\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*(?:process|Deno|Bun)\b",
            code,
        )
    )


def aliases_filesystem_namespace(
    context: AuditContext, content: str, namespaces: set[str]
) -> bool:
    """Return whether an inspected fs namespace is assigned to another name."""
    if not namespaces:
        return False
    code = javascript_inspection_view(content, mask_strings=True)
    charge_text_scan(context, code)
    namespace_pattern = "|".join(
        re.escape(namespace) for namespace in sorted(namespaces)
    )
    return bool(
        re.search(
            rf"\b(?:const|let|var)\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*(?:{namespace_pattern})\b",
            code,
        )
    )


def called_aliased_filesystem_apis(
    context: AuditContext, content: str
) -> tuple[set[str], bool]:
    """Return fs APIs invoked through a statically named import alias."""
    source = javascript_inspection_view(content, mask_strings=False)
    code = javascript_inspection_view(content, mask_strings=True)
    called: set[str] = set()
    unresolved = False
    filesystem_apis = (
        FS_READ_APIS | FS_WRITE_APIS | FS_DELETE_APIS | FS_ACCESS_CHANGE_APIS
    )
    pattern = re.compile(
        r"(?:^|\n)\s*import\s*\{([^}]*)\}\s*from\s*[\"'](?:node:)?fs(?:/promises)?[\"']",
        re.MULTILINE,
    )
    charge_text_scan(context, source)
    for match in pattern.finditer(source):
        import_offset = match.start() + match.group(0).find("import")
        if code[import_offset : import_offset + 6] != "import":
            continue
        for raw_binding in match.group(1).split(","):
            context.budget.charge_work()
            binding = raw_binding.strip()
            parsed = re.fullmatch(
                r"([A-Za-z_$][A-Za-z0-9_$]*)(?:\s+as\s+([A-Za-z_$][A-Za-z0-9_$]*))?",
                binding,
            )
            if parsed is None:
                unresolved = True
                continue
            imported_name = parsed.group(1)
            if imported_name in filesystem_apis:
                called.add(imported_name)

    namespaces: set[str] = set()
    namespace_patterns = (
        re.compile(
            r"(?:^|\n)\s*import\s+\*\s+as\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s+from\s*[\"'](?:node:)?fs(?:/promises)?[\"']",
            re.MULTILINE,
        ),
        re.compile(
            r"(?:^|\n)\s*import\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*(?:,|\s+from\s*)[^;\n]*[\"'](?:node:)?fs(?:/promises)?[\"']",
            re.MULTILINE,
        ),
        re.compile(
            r"\b(?:const|let|var)\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*require\s*\(\s*[\"'](?:node:)?fs(?:/promises)?[\"']\s*\)"
        ),
    )
    for namespace_pattern in namespace_patterns:
        charge_text_scan(context, source)
        for match in namespace_pattern.finditer(source):
            start, end = match.span("name")
            if code[start:end] == source[start:end]:
                context.budget.charge_work()
                namespaces.add(match.group("name"))

    bracket_properties, bracket_computed = static_bracket_properties(
        context, content, namespaces
    )
    called.update(bracket_properties.intersection(filesystem_apis))
    called.update(
        static_dot_properties(context, content, namespaces).intersection(
            filesystem_apis
        )
    )
    unresolved = (
        unresolved
        or bracket_computed
        or aliases_filesystem_namespace(context, content, namespaces)
    )

    destructuring_patterns = [
        re.compile(
            rf"\b(?P<keyword>const|let|var)\s*\{{(?P<bindings>[^}}]*)\}}\s*=\s*(?P<namespace>{'|'.join(re.escape(name) for name in sorted(namespaces))})(?:\s*\.\s*promises)?\b"
        )
        if namespaces
        else None,
        re.compile(
            r"\b(?P<keyword>const|let|var)\s*\{(?P<bindings>[^}]*)\}\s*=\s*require\s*\(\s*[\"'](?:node:)?fs(?:/promises)?[\"']\s*\)"
        ),
    ]
    for destructuring_pattern in destructuring_patterns:
        if destructuring_pattern is None:
            continue
        charge_text_scan(context, source)
        for match in destructuring_pattern.finditer(source):
            keyword_start, keyword_end = match.span("keyword")
            if code[keyword_start:keyword_end] != source[keyword_start:keyword_end]:
                continue
            for raw_binding in match.group("bindings").split(","):
                context.budget.charge_work()
                binding = raw_binding.strip()
                parsed = re.fullmatch(
                    r"([A-Za-z_$][A-Za-z0-9_$]*)(?:\s*:\s*([A-Za-z_$][A-Za-z0-9_$]*))?",
                    binding,
                )
                if parsed is None:
                    unresolved = True
                    continue
                imported_name = parsed.group(1)
                if imported_name in filesystem_apis:
                    called.add(imported_name)
    return called, unresolved


def check_javascript_module(
    context: AuditContext,
    path: RepoPath,
    *,
    action_dir: RepoPath,
    target: RepoPath,
    findings: list[Finding],
    production: bool,
    visited: set[RepoPath],
) -> tuple[set[str], bool]:
    resolved_path = resolve_stable_path(path, expected="file")
    resolved_action_dir = resolve_stable_path(action_dir, expected="directory")
    if resolved_path in visited:
        return set(), False
    visited.add(resolved_path)
    content = read_text(path, target, findings)
    if content is None:
        return set(), False
    location = relative(path, target)
    dependencies: set[str] = set()
    try:
        imports, dynamic = static_imports(content)
        called_fs_aliases, unresolved_fs_alias = called_aliased_filesystem_apis(
            context, content
        )
    except StaticAnalysisAmbiguity:
        visited.discard(resolved_path)
        findings.append(
            finding(
                "action-static-validation",
                location,
                "ambiguous JavaScript slash syntax needs manual validation",
                "validation-needed",
            )
        )
        return set(), True
    imports_filesystem = any(
        specifier.removeprefix("node:") in {"fs", "fs/promises"}
        for specifier in imports
    )
    imports_process_control = any(
        specifier.removeprefix("node:") == "child_process"
        or package_root(specifier) in FORBIDDEN_PACKAGE_MODULES
        for specifier in imports
        if not specifier.startswith(("./", "../", "/"))
    )
    if dynamic:
        findings.append(
            finding(
                "action-static-validation",
                location,
                "dynamic import or require needs manual validation; Audit did not execute it",
                "validation-needed",
            )
        )
    for specifier in imports:
        path.root.budget.charge_work()
        if any(unsafe_path_character(character) for character in specifier):
            findings.append(
                finding(
                    "action-import-malformed",
                    location,
                    "Action import contains control characters; specifier redacted",
                )
            )
            continue
        if specifier.startswith(("./", "../")):
            try:
                unresolved_import = path.parent / specifier
                lexical_import = unresolved_import
            except (OSError, ValueError, UnicodeError):
                findings.append(
                    finding(
                        "action-import-malformed",
                        location,
                        "local Action import path is malformed; specifier redacted",
                    )
                )
                continue
            if not is_within(lexical_import, resolved_action_dir):
                findings.append(
                    finding(
                        "action-local-import",
                        location,
                        "local import leaves the Action directory; specifier redacted",
                    )
                )
                continue
            if context.root.is_symlink(unresolved_import) or not context.root.is_file(
                unresolved_import
            ):
                findings.append(
                    finding(
                        "action-local-import",
                        location,
                        "local import is missing or not a regular file; specifier redacted",
                    )
                )
                continue
            try:
                imported = resolve_stable_path(unresolved_import, expected="file")
            except InvocationError:
                findings.append(
                    finding(
                        "action-local-import",
                        location,
                        "local import path is symlinked, unstable, or unsafe; specifier redacted",
                    )
                )
                continue
            permitted_test_import = (
                not production
                and resolved_path
                == resolve_stable_path(action_dir / "run.test.mjs", expected="file")
                and specifier == "./run.mjs"
                and imported
                == resolve_stable_path(action_dir / "run.mjs", expected="file")
            )
            if not permitted_test_import:
                findings.append(
                    finding(
                        "action-local-import",
                        location,
                        "Action source imports a prohibited local helper; specifier redacted",
                    )
                )
                continue
            if imported.suffix in {".js", ".mjs", ".cjs"}:
                nested_dependencies, nested_dynamic = check_javascript_module(
                    context,
                    imported,
                    action_dir=action_dir,
                    target=target,
                    findings=findings,
                    production=production,
                    visited=visited,
                )
                dependencies.update(nested_dependencies)
                dynamic = dynamic or nested_dynamic
            continue
        if specifier.startswith(("/", "file:", "http:", "https:", "data:")):
            findings.append(
                finding(
                    "action-import-forbidden",
                    location,
                    "absolute, URL, or external import is forbidden; specifier redacted",
                )
            )
            continue
        builtin_specifier = specifier.removeprefix("node:")
        builtin = builtin_specifier.split("/", 1)[0]
        if specifier.startswith("node:") and builtin not in NODE_BUILTINS:
            findings.append(
                finding(
                    "action-import-malformed",
                    location,
                    "Action imports a Node built-in outside the reviewed allowlist; specifier redacted",
                    "validation-needed",
                )
            )
            continue
        if specifier.startswith("node:") or builtin_specifier in NODE_BUILTINS:
            if builtin in FORBIDDEN_MODULES and not (
                not production and builtin == "os"
            ):
                findings.append(
                    finding(
                        "action-capability-forbidden",
                        location,
                        "Action imports a forbidden network, process, or concurrency module; specifier redacted",
                    )
                )
            elif not specifier.startswith("node:"):
                findings.append(
                    finding(
                        "action-import-builtin-prefix",
                        location,
                        "Node built-in imports must use the explicit node: prefix; specifier redacted",
                    )
                )
            continue
        dependency = package_root(specifier)
        if dependency in FORBIDDEN_PACKAGE_MODULES:
            findings.append(
                finding(
                    "action-capability-forbidden",
                    location,
                    "Action imports a package whose purpose is network or process access; package redacted",
                )
            )
        if PACKAGE_NAME_RE.fullmatch(dependency):
            dependencies.add(dependency)
        else:
            findings.append(
                finding(
                    "action-import-malformed",
                    location,
                    "Action import is not a valid registry package specifier; value redacted",
                )
            )

    without_comments = javascript_inspection_view(content, mask_strings=False)
    code = javascript_inspection_view(content, mask_strings=True)
    process_properties, computed_process_property = static_bracket_properties(
        context, content, {"Bun", "Deno", "process"}
    )
    process_properties.update(
        static_dot_properties(context, content, {"Bun", "Deno", "process"})
    )
    destructured_process, unresolved_process_destructure = destructured_properties(
        context, content, {"Bun", "Deno", "process"}
    )
    process_properties.update(destructured_process)
    if production and (PROCESS_ENV_RE.search(code) or "env" in process_properties):
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action accesses process environment or secrets",
            )
        )
    if production and (
        computed_process_property
        or unresolved_process_destructure
        or aliases_runtime_owner(context, content)
        or unresolved_fs_alias
    ):
        findings.append(
            finding(
                "action-static-validation",
                location,
                "computed runtime or filesystem capability access needs manual validation",
                "validation-needed",
            )
        )
    controls_process = bool(
        PROCESS_CONTROL_RE.search(code)
        or process_properties.intersection(PROCESS_CONTROL_PROPERTIES)
    )
    if controls_process:
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action controls process state, identity, or another process",
            )
        )
    if (
        RUNTIME_BYPASS_RE.search(code)
        or process_properties.intersection(RUNTIME_BYPASS_PROPERTIES)
    ) and not controls_process:
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action accesses a runtime bypass API",
            )
        )
    if NETWORK_GLOBAL_RE.search(code) or re.search(
        r"\b(?:fetch|WebSocket|EventSource)\b", code
    ):
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action uses a network-capable global",
            )
        )
    if imports_filesystem and (
        re.search(r"\b(?:glob|globSync|watch|watchFile)\s*\(", code)
        or called_fs_aliases.intersection(FS_UNBOUNDED_READ_APIS)
    ):
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action uses an unbounded filesystem discovery or watch API",
            )
        )
    if GENERATED_CODE_RE.search(code):
        findings.append(
            finding(
                "action-static-validation",
                location,
                "generated code cannot be established through static inspection",
                "validation-needed",
            )
        )
    if imports_process_control and SHELL_RE.search(code):
        findings.append(
            finding(
                "action-capability-forbidden",
                location,
                "Action invokes an external program, process, or shell",
            )
        )
    if (
        production
        and imports_filesystem
        and (DELETE_RE.search(code) or called_fs_aliases.intersection(FS_DELETE_APIS))
    ):
        findings.append(
            finding(
                "action-delete-forbidden",
                location,
                "Action code performs a forbidden delete",
            )
        )
    if (
        production
        and imports_filesystem
        and (
            ACCESS_CHANGE_RE.search(code)
            or called_fs_aliases.intersection(FS_ACCESS_CHANGE_APIS)
        )
    ):
        findings.append(
            finding(
                "action-access-change-forbidden",
                location,
                "Action code performs a forbidden access or ownership change",
            )
        )
    if (
        production
        and imports_filesystem
        and (
            DIRECT_WRITE_RE.search(code)
            or WRITE_OPEN_RE.search(without_comments)
            or called_fs_aliases.intersection(FS_WRITE_APIS)
        )
    ):
        findings.append(
            finding(
                "action-direct-write-forbidden",
                location,
                "Action implementation writes directly; only the trusted runner may apply reviewed plan bytes",
            )
        )
    return dependencies, dynamic


def manifest_dependency_map(manifest: ActionManifest) -> dict[str, str]:
    return dict(manifest.dependency_versions())


def package_dependency_map(context: AuditContext, target: RepoPath) -> dict[str, str]:
    path = target / "_handbook" / "_cli" / "package.json"
    try:
        package = context.root.read_json(path)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ):
        return {}
    result: dict[str, str] = {}
    if not is_json_object(package):
        return result
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        values = package.get(section, {})
        if is_json_object(values):
            for name, version in values.items():
                if isinstance(name, str) and isinstance(version, str):
                    result[name] = version
    return result


def declared_effect_scopes(
    manifest: ActionManifest, effect: str
) -> tuple[list[str], list[str]]:
    scopes = manifest.effect_scopes(effect)
    return (
        [scope.path for scope in scopes if scope.path is not None],
        [scope.input_name for scope in scopes if scope.input_name is not None],
    )


def static_scope_covers(scope: str, candidate: str) -> bool:
    scope_parts = tuple(
        part
        for part in normalize_relative_path(scope).split("/")
        if part not in ("", ".")
    )
    candidate_parts = tuple(
        part
        for part in normalize_relative_path(candidate).split("/")
        if part not in ("", ".")
    )
    return candidate_parts[: len(scope_parts)] == scope_parts


def covered_by_static_scope(
    context: AuditContext, scopes: list[str], candidate: str
) -> bool:
    for scope in scopes:
        context.budget.charge_work()
        if static_scope_covers(scope, candidate):
            return True
    return False


def check_action_static_contract(
    context: AuditContext,
    action_id: str,
    action_dir: RepoPath,
    manifest: ActionManifest,
    target: RepoPath,
    findings: list[Finding],
) -> None:
    entrypoint = action_dir / "run.mjs"
    test_path = action_dir / "run.test.mjs"
    production_dependencies: set[str] = set()
    production_dynamic = False
    production_files: set[RepoPath] = set()
    if context.root.is_file(entrypoint) and not context.root.is_symlink(entrypoint):
        production_dependencies, production_dynamic = check_javascript_module(
            context,
            entrypoint,
            action_dir=action_dir,
            target=target,
            findings=findings,
            production=True,
            visited=production_files,
        )
    test_dependencies: set[str] = set()
    if context.root.is_file(test_path) and not context.root.is_symlink(test_path):
        test_files = set(production_files)
        test_dependencies, _ = check_javascript_module(
            context,
            test_path,
            action_dir=action_dir,
            target=target,
            findings=findings,
            production=False,
            visited=test_files,
        )

    declared = manifest_dependency_map(manifest)
    package_dependencies = package_dependency_map(context, target)
    imported = production_dependencies | test_dependencies
    for name in sorted(imported):
        context.budget.charge_work()
        if name not in declared:
            findings.append(
                finding(
                    "action-dependency-undeclared",
                    relative(
                        entrypoint if name in production_dependencies else test_path,
                        target,
                    ),
                    "static import is absent from manifest dependencies; package redacted",
                )
            )
        if name not in package_dependencies:
            findings.append(
                finding(
                    "action-package-dependency-missing",
                    diagnostic_path("_handbook/_cli/package.json"),
                    "static Action import is absent from package dependencies; package redacted",
                )
            )
        if name in declared and name in package_dependencies:
            findings.append(
                finding(
                    "action-dependency-opaque",
                    relative(
                        entrypoint if name in production_dependencies else test_path,
                        target,
                    ),
                    "dependency internals were not inspected or executed; package redacted",
                    "validation-needed",
                )
            )
    for name, version in declared.items():
        context.budget.charge_work()
        if package_dependencies.get(name) != version:
            findings.append(
                finding(
                    "action-dependency-drift",
                    relative(action_dir / "action.json", target),
                    "manifest dependency does not match package.json; package details redacted",
                )
            )
        if name not in imported and not production_dynamic:
            findings.append(
                finding(
                    "action-dependency-unused",
                    relative(action_dir / "action.json", target),
                    "declared dependency has no static import in Action code or test; package redacted",
                    "validation-needed",
                )
            )

    read_paths, read_inputs = declared_effect_scopes(manifest, "reads")
    for production_file in sorted(production_files, key=lambda item: item.as_posix()):
        context.budget.charge_work()
        content = read_text(production_file, target, findings) or ""
        imports, _ = static_imports(content)
        imports_fs = any(
            specifier.removeprefix("node:") in {"fs", "fs/promises"}
            for specifier in imports
        )
        code = javascript_inspection_view(content, mask_strings=True)
        called_fs_apis, _ = called_aliased_filesystem_apis(context, content)
        calls_read = bool(
            DIRECT_READ_RE.search(code) or called_fs_apis.intersection(FS_READ_APIS)
        )
        if not imports_fs or not calls_read:
            continue
        if not read_paths and not read_inputs:
            findings.append(
                finding(
                    "action-effect-undeclared",
                    relative(production_file, target),
                    "implementation uses filesystem read APIs but manifest effects.reads is empty",
                )
            )
            continue
        literals = [
            match.group(2)
            for match in LITERAL_READ_RE.finditer(
                javascript_inspection_view(content, mask_strings=False)
            )
        ]
        for literal in literals:
            context.budget.charge_work()
            if not valid_relative_path(literal):
                findings.append(
                    finding(
                        "action-read-path-forbidden",
                        relative(production_file, target),
                        "literal filesystem read is unsafe or outside the work folder; path redacted",
                    )
                )
            elif not covered_by_static_scope(context, read_paths, literal):
                findings.append(
                    finding(
                        "action-effect-unproven",
                        relative(production_file, target),
                        "literal read is not covered by a static declared scope; path redacted",
                        "validation-needed" if read_inputs else "integrity",
                    )
                )
        if not literals and not read_inputs:
            findings.append(
                finding(
                    "action-effect-unproven",
                    relative(production_file, target),
                    "dynamic filesystem read could not be tied to a declared named path input",
                    "validation-needed",
                )
            )
    mode = None
    execution = manifest.get("execution")
    if is_json_object(execution):
        mode = execution.get("mode")
    entrypoint_text = ""
    if context.root.is_file(entrypoint) and not context.root.is_symlink(entrypoint):
        entrypoint_text = read_text(entrypoint, target, findings) or ""
    try:
        entrypoint_visible = javascript_inspection_view(
            entrypoint_text, mask_strings=False
        )
    except StaticAnalysisAmbiguity:
        entrypoint_visible = ""
    manifest_inputs = manifest.get("inputs")
    declared_input_names: set[str] = set()
    if is_json_array(manifest_inputs):
        for item in manifest_inputs:
            context.budget.charge_work()
            if not is_json_object(item):
                continue
            input_name = item.get("name")
            if isinstance(input_name, str):
                declared_input_names.add(input_name)
    implementation_flags = set(
        re.findall(
            r"[\"']--([a-z][a-z0-9]*(?:-[a-z0-9]+)*)[\"']",
            entrypoint_visible,
        )
    )
    if "apply" in implementation_flags:
        findings.append(
            finding(
                "action-execution-drift",
                relative(entrypoint, target),
                "Action implementation contains forbidden --apply handling; apply belongs to the trusted runner",
            )
        )
    if "trellis-plan" in implementation_flags and mode != "plan-apply":
        findings.append(
            finding(
                "action-execution-drift",
                relative(entrypoint, target),
                "read-only Action implementation handles the runner-reserved --trellis-plan flag",
            )
        )
    for _name in sorted(declared_input_names - implementation_flags):
        findings.append(
            finding(
                "action-input-implementation-mismatch",
                relative(entrypoint, target),
                "implementation does not statically handle a declared input; name redacted",
                "validation-needed"
                if production_dynamic or production_dependencies
                else "integrity",
            )
        )
    for _name in sorted(
        implementation_flags - declared_input_names - {"apply", "trellis-plan"}
    ):
        findings.append(
            finding(
                "action-input-implementation-mismatch",
                relative(entrypoint, target),
                "implementation handles an undeclared input; name redacted",
            )
        )
    expected_schema = (
        "trellis.action-result/v1" if mode == "read-only" else "trellis.action-plan/v1"
    )
    if (
        mode in {"read-only", "plan-apply"}
        and expected_schema not in entrypoint_visible
    ):
        findings.append(
            finding(
                "action-envelope-missing",
                relative(entrypoint, target),
                f"implementation does not statically expose the required {expected_schema} envelope",
                "validation-needed",
            )
        )
    if mode == "read-only" and "trellis.action-plan/v1" in entrypoint_visible:
        findings.append(
            finding(
                "action-execution-drift",
                relative(entrypoint, target),
                "read-only implementation emits a plan envelope",
            )
        )
    if mode == "plan-apply" and "trellis.action-result/v1" in entrypoint_visible:
        findings.append(
            finding(
                "action-execution-drift",
                relative(entrypoint, target),
                "plan-apply implementation emits a read-only result envelope",
            )
        )
    if mode == "read-only":
        manifest_outputs = manifest.get("outputs")
        declared_output_names: set[str] = set()
        if is_json_array(manifest_outputs):
            for item in manifest_outputs:
                context.budget.charge_work()
                if not is_json_object(item):
                    continue
                output_name = item.get("name")
                if isinstance(output_name, str):
                    declared_output_names.add(output_name)
        implementation_output_names = set(
            re.findall(
                r"(?:\bname|[\"']name[\"'])\s*:\s*[\"']([a-z][a-z0-9]*(?:-[a-z0-9]+)*)[\"']",
                entrypoint_visible,
            )
        )
        for _name in sorted(declared_output_names - implementation_output_names):
            findings.append(
                finding(
                    "action-output-implementation-mismatch",
                    relative(entrypoint, target),
                    "read-only result does not statically expose a declared output; name redacted",
                    "validation-needed",
                )
            )
        for _name in sorted(implementation_output_names - declared_output_names):
            findings.append(
                finding(
                    "action-output-implementation-mismatch",
                    relative(entrypoint, target),
                    "read-only result exposes an undeclared output; name redacted",
                    "validation-needed",
                )
            )
        if not re.search(
            r"(?:\bverification|[\"']verification[\"'])\s*:|\bverification\s*(?:,|})",
            entrypoint_visible,
        ):
            findings.append(
                finding(
                    "action-verification-implementation-mismatch",
                    relative(entrypoint, target),
                    "read-only result does not statically expose verification evidence",
                    "validation-needed",
                )
            )
    if mode == "plan-apply":
        for property_name in ("summary", "operations", "verification"):
            charge_text_scan(context, entrypoint_visible)
            if not re.search(
                rf"(?:\b{property_name}|[\"']{property_name}[\"'])\s*:|\b{property_name}\s*(?:,|}})",
                entrypoint_visible,
            ):
                findings.append(
                    finding(
                        "action-plan-implementation-unproven",
                        relative(entrypoint, target),
                        f"plan envelope does not statically expose {property_name}",
                        "validation-needed",
                    )
                )
        manifest_outputs = manifest.get("outputs")
        for output in manifest_outputs if is_json_array(manifest_outputs) else []:
            if not is_json_object(output):
                continue
            path_value = output.get("path")
            if not isinstance(path_value, str):
                continue
            output_path = normalize_relative_path(path_value)
            charge_text_scan(context, entrypoint_visible, passes=2)
            if (
                output_path not in entrypoint_visible
                and path_value not in entrypoint_visible
            ):
                findings.append(
                    finding(
                        "action-plan-output-unproven",
                        relative(entrypoint, target),
                        "plan implementation does not statically expose a declared output path; value redacted",
                        "validation-needed",
                    )
                )

    if context.root.is_file(test_path) and not context.root.is_symlink(test_path):
        test_text = read_text(test_path, target, findings) or ""
        try:
            test_imports, _ = static_imports(test_text)
            test_code = javascript_inspection_view(test_text, mask_strings=True)
            test_ambiguous = False
        except StaticAnalysisAmbiguity:
            test_imports = []
            test_code = ""
            test_ambiguous = True
        imported_entrypoint = any(
            specifier in {"./run.mjs", "./" + str(manifest.get("entrypoint"))}
            for specifier in test_imports
        )
        if not test_ambiguous and not imported_entrypoint:
            findings.append(
                finding(
                    "action-test-drift",
                    relative(test_path, target),
                    "focused test does not statically import the declared entrypoint",
                )
            )
        if not test_ambiguous and TODO_TEST_RE.search(test_code):
            findings.append(
                finding(
                    "action-test-incomplete",
                    relative(test_path, target),
                    "test contains a skip, TODO, FIXME, or placeholder marker",
                    "validation-needed",
                )
            )
        readiness = manifest.get("readiness")
        readiness_status = (
            readiness.get("status") if is_json_object(readiness) else None
        )
        if not test_ambiguous and readiness_status in {"tests-passed", "validated"}:
            if "node:test" not in test_imports or not re.search(
                r"\btest\s*\(",
                test_code,
            ):
                findings.append(
                    finding(
                        "action-test-drift",
                        relative(test_path, target),
                        f"{readiness_status} readiness is not supported by a focused node:test body",
                    )
                )
            has_assert_import = any(
                specifier in {"node:assert", "node:assert/strict"}
                for specifier in test_imports
            )
            has_assertion = bool(
                re.search(
                    r"\b(?:assert(?:\.[A-Za-z][A-Za-z0-9]*)?|deepEqual|equal|"
                    r"fail|match|notDeepEqual|notEqual|notStrictEqual|ok|rejects|"
                    r"strictEqual|throws)\s*\(",
                    test_code,
                )
            )
            if not has_assert_import or not has_assertion:
                findings.append(
                    finding(
                        "action-test-drift",
                        relative(test_path, target),
                        f"{readiness_status} readiness is not supported by a static assertion",
                    )
                )

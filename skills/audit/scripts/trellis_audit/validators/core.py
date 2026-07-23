#!/usr/bin/env python3
"""Run a structural audit of Trellis-managed handbook support."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path as LocalPath
from typing import NoReturn

from ..context import (
    DEFAULT_LIMITS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_FINDINGS,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_TOTAL_BYTES,
    DEFAULT_MAX_WORK_UNITS,
    AuditContext,
    AuditLimits,
)
from ..diagnostics import (
    JSON_SCHEMA,
    Finding,
    InvocationError,
    ResourceLimitError,
    Suggestion,
    finding,
)
from ..filesystem import (
    RepoPath,
    is_within,
    relative,
)

FORMAT_MARKER = "<!-- trellis-format: 2 -->"
DEFAULT_MAX_ERROR_MESSAGE_BYTES = 4 * 1024
HANDBOOK_START = "<!-- trellis:handbook:start -->"
HANDBOOK_END = "<!-- trellis:handbook:end -->"
CAPTURE_MARKER_RE = re.compile(
    r"<!--\s*trellis-capture:\s*(playbook|action)\s+format=([0-9]+)\s*-->"
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
ENTRY_RE = re.compile(r"^\s*-\s+\[")
ACTION_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ACTION_ID_RE = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:/[a-z][a-z0-9]*(?:-[a-z0-9]+)*)*$"
)
RESERVED_ACTION_TOP_LEVEL = {
    "apply",
    "doctor",
    "help",
    "list",
    "plan",
    "run",
    "scaffold",
    "show",
    "show-plan",
    "test",
    "validate",
    "version",
}
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HOST_RE = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::[0-9]{1,5})?$")
PROCESS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
EXACT_VERSION_RE = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
PACKAGE_NAME_PATTERN = r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*"
PACKAGE_NAME_RE = re.compile(rf"^{PACKAGE_NAME_PATTERN}$")
PINNED_SCRIPT_RE = re.compile(
    rf"^({PACKAGE_NAME_PATTERN})@([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$"
)
INPUT_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IMPORT_RE = re.compile(
    r"(?:^|\n)\s*import\s+(?:[^;]*?\s+from\s+)?[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
EXPORT_FROM_RE = re.compile(
    r"(?:^|\n)\s*export\s+(?:\*|\{[^}]*\})\s+from\s+[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
DYNAMIC_IMPORT_RE = re.compile(r"\bimport\s*\(\s*([^)]+?)\s*\)")
REQUIRE_RE = re.compile(r"\brequire\s*\(\s*([^)]+?)\s*\)")
PROCESS_ENV_RE = re.compile(
    r"\b(?:process|Deno|Bun)\s*(?:\.\s*env\b|\[\s*[\"']env[\"']\s*\])"
)
PROCESS_CONTROL_RE = re.compile(
    r"\bprocess\s*\.\s*(?:_debugEnd|_debugProcess|_kill|chdir|execve|initgroups|"
    r"kill|loadEnvFile|openStdin|setegid|seteuid|setgid|setgroups|setuid|umask)\s*\("
)
RUNTIME_BYPASS_RE = re.compile(
    r"\bprocess\s*\.\s*(?:_linkedBinding|binding|dlopen|getBuiltinModule|kill)\b"
)
GENERATED_CODE_RE = re.compile(r"\b(?:eval|Function)\s*\(|\bnew\s+Function\b")
NETWORK_GLOBAL_RE = re.compile(r"\b(?:fetch|WebSocket|EventSource)\s*\(")
DIRECT_WRITE_RE = re.compile(
    r"\b(?:appendFile|appendFileSync|copyFile|copyFileSync|cp|cpSync|createWriteStream|"
    r"link|linkSync|mkdir|mkdirSync|mkdtemp|mkdtempSync|rename|renameSync|symlink|"
    r"symlinkSync|truncate|truncateSync|utimes|utimesSync|writeFile|writeFileSync)\s*\("
)
DIRECT_READ_RE = re.compile(
    r"\b(?:access|accessSync|createReadStream|exists|existsSync|glob|globSync|lstat|"
    r"lstatSync|open|openAsBlob|openSync|opendir|opendirSync|readFile|readFileSync|readdir|readdirSync|"
    r"readlink|readlinkSync|realpath|realpathSync|stat|statfs|statfsSync|statSync|watch|watchFile)\s*\("
)
LITERAL_READ_RE = re.compile(
    r"\b(?:access|accessSync|createReadStream|exists|existsSync|glob|globSync|lstat|"
    r"lstatSync|open|openAsBlob|openSync|opendir|opendirSync|readFile|readFileSync|readdir|readdirSync|"
    r"readlink|readlinkSync|realpath|realpathSync|stat|statfs|statfsSync|statSync|watch|watchFile)\s*\(\s*([\"'])([^\"']+)\1"
)
WRITE_OPEN_RE = re.compile(
    r"\bopen(?:Sync)?\s*\([^,]+,\s*[\"'][^\"']*[wax+][^\"']*[\"']"
)
DELETE_RE = re.compile(
    r"\b(?:rm|rmSync|rmdir|rmdirSync|truncate|truncateSync|unlink|unlinkSync)\s*\("
)
ACCESS_CHANGE_RE = re.compile(
    r"\b(?:chmod|chmodSync|chown|chownSync|fchmod|fchmodSync|fchown|fchownSync|"
    r"lchmod|lchmodSync|lchown|lchownSync)\s*\("
)
FS_READ_APIS = {
    "access",
    "accessSync",
    "createReadStream",
    "exists",
    "existsSync",
    "glob",
    "globSync",
    "lstat",
    "lstatSync",
    "open",
    "openAsBlob",
    "openSync",
    "opendir",
    "opendirSync",
    "readFile",
    "readFileSync",
    "readdir",
    "readdirSync",
    "readlink",
    "readlinkSync",
    "realpath",
    "realpathSync",
    "stat",
    "statfs",
    "statfsSync",
    "statSync",
    "watch",
    "watchFile",
}
FS_WRITE_APIS = {
    "appendFile",
    "appendFileSync",
    "copyFile",
    "copyFileSync",
    "cp",
    "cpSync",
    "createWriteStream",
    "link",
    "linkSync",
    "mkdir",
    "mkdirSync",
    "mkdtemp",
    "mkdtempSync",
    "rename",
    "renameSync",
    "symlink",
    "symlinkSync",
    "truncate",
    "truncateSync",
    "utimes",
    "utimesSync",
    "writeFile",
    "writeFileSync",
}
FS_DELETE_APIS = {
    "rm",
    "rmSync",
    "rmdir",
    "rmdirSync",
    "truncate",
    "truncateSync",
    "unlink",
    "unlinkSync",
}
FS_ACCESS_CHANGE_APIS = {
    "chmod",
    "chmodSync",
    "chown",
    "chownSync",
    "fchmod",
    "fchmodSync",
    "fchown",
    "fchownSync",
    "lchmod",
    "lchmodSync",
    "lchown",
    "lchownSync",
}
FS_UNBOUNDED_READ_APIS = {"glob", "globSync", "watch", "watchFile"}
SHELL_RE = re.compile(
    r"\b(?:exec|execFile|execFileSync|execSync|fork|spawn|spawnSync)\s*\("
)
TODO_TEST_RE = re.compile(
    r"\b(?:test|it|describe)\.(?:skip|todo)\b|\bTODO\b|\bFIXME\b|\bplaceholder\b",
    re.I,
)

EXPECTED_NPMRC = {
    "registry": "https://registry.npmjs.org/",
    "strict-ssl": "true",
    "package-lock": "true",
    "lockfile-version": "3",
    "save-exact": "true",
    "omit-lockfile-registry-resolved": "false",
    "engine-strict": "true",
    "strict-peer-deps": "true",
    "legacy-peer-deps": "false",
    "bin-links": "false",
    "allow-directory": "none",
    "allow-file": "none",
    "allow-git": "none",
    "allow-remote": "none",
    "min-release-age": "7",
    "ignore-scripts": "true",
    "strict-allow-scripts": "true",
    "allow-scripts-pin": "true",
    "dangerously-allow-all-scripts": "false",
    "audit": "true",
    "audit-level": "high",
    "force": "false",
    "fund": "false",
    "update-notifier": "false",
}
EXPECTED_RUNTIME_SHA256 = {
    "trellis": "e889b31bb5680c7e7508bf50951da3d1c15b58f9a6365e21a81c5d781a8ee1c7",
    "_handbook/_cli/.gitignore": "9425899862bc40f572da4686b2a3e10ded1f73049a39c1049b1c426288eaa683",
    "_handbook/_cli/bin/trellis.mjs": "d2a694dc5a898cbe9ccfbc91ceb068f41e7caefe51917d7382f5363293c83d0d",
    "_handbook/_cli/src/cli.mjs": "1beaefe9608e5db2fde59975dab147586f5b8abf86486c54c113bccf45989ca2",
    "_handbook/_cli/src/guard.mjs": "640f53ec445872e3e96f7507027b65dd305de842e32a6b0508db0c649e43a787",
    "_handbook/_cli/test/cli.test.mjs": "95196bf8bb094079b455f29f0f9044c1a2a2145d9143257979ffe9ee8c0b36d0",
    "_handbook/_scratch/.gitignore": "ca6cf70d24ab97e47c3befa11f763c702242c1deaaebe7327ec5ca1bfdf88328",
    "_handbook/_scratch/README.md": "a9a6890fafbd2cb967edbd6bf5e15aeb5b2e4e509569b7581cf82e34fe283778",
}
PACKAGE_ALLOWED_KEYS = {
    "name",
    "version",
    "private",
    "license",
    "type",
    "packageManager",
    "engines",
    "devEngines",
    "allowScripts",
    "scripts",
    "dependencies",
    "devDependencies",
    "optionalDependencies",
}
EFFECT_KEYS = ("reads", "creates", "updates", "temporary")
FORBIDDEN_EFFECT_KEYS = ("writes", "network", "environment", "processes", "deletes")
MANIFEST_KEYS = {
    "format",
    "version",
    "id",
    "title",
    "summary",
    "entrypoint",
    "test",
    "docs",
    "methodConfidence",
    "readiness",
    "lifecycle",
    "inputs",
    "outputs",
    "effects",
    "execution",
    "success",
    "dependencies",
    "digests",
}
REQUIRED_MANIFEST_KEYS = MANIFEST_KEYS
FORBIDDEN_MANIFEST_KEYS = {
    "communication",
    "delete",
    "deletes",
    "environment",
    "network",
    "permissions",
    "process",
    "processes",
    "publish",
    "remote",
    "shell",
}
INPUT_TYPES = {
    "string",
    "boolean",
    "integer",
    "number",
    "path",
    "file",
    "directory",
    "string-list",
}
PATH_INPUT_TYPES = {"path", "file", "directory"}
OUTPUT_TYPES = {"text", "json", "number", "boolean", "file", "files"}
FORBIDDEN_MODULES = {
    "child_process",
    "cluster",
    "dgram",
    "dns",
    "http",
    "http2",
    "https",
    "inspector",
    "module",
    "net",
    "os",
    "quic",
    "repl",
    "sqlite",
    "tls",
    "vm",
    "wasi",
    "worker_threads",
}
FORBIDDEN_PACKAGE_MODULES = {
    "axios",
    "execa",
    "got",
    "node-fetch",
    "shelljs",
    "superagent",
    "undici",
    "ws",
}
NODE_BUILTINS = FORBIDDEN_MODULES | {
    "assert",
    "assert/strict",
    "async_hooks",
    "buffer",
    "console",
    "constants",
    "crypto",
    "diagnostics_channel",
    "events",
    "fs",
    "fs/promises",
    "module",
    "os",
    "path",
    "perf_hooks",
    "process",
    "querystring",
    "readline",
    "readline/promises",
    "repl",
    "stream",
    "string_decoder",
    "test",
    "timers",
    "timers/promises",
    "tty",
    "url",
    "util",
    "util/types",
    "v8",
    "vm",
    "wasi",
    "zlib",
}
FORBIDDEN_PATH_PARTS = {".git", ".ssh", ".gnupg", ".aws"}
FORBIDDEN_SECRET_BASENAMES = {
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
}
HARD_RESERVED_SCOPE_ROOTS = {
    ".claude",
    ".codex",
    ".cursor",
    ".git",
    "agents.md",
    "claude.md",
    "gemini.md",
    "trellis",
}
SOFT_PROTECTED_SCOPE_ROOTS = {"_handbook", "handbook", "instructions"}
HARD_RESERVED_HANDBOOK_CHILDREN = {"_cli", "_scratch"}
PLAYBOOK_HEADINGS = ("Use When", "Outcome", "Method", "Boundaries", "Verification")
ACTION_HEADINGS = (
    "Purpose",
    "Use When",
    "Inputs",
    "Outputs",
    "Run",
    "Effects",
    "Success And Failure",
    "Verification",
)


class AuditArgumentParser(argparse.ArgumentParser):
    """Convert parser failures into the audit's stable error contract."""

    def error(self, message: str) -> NoReturn:
        del message
        raise InvocationError(
            "invalid-arguments", "invalid command-line arguments; use --help"
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = AuditArgumentParser(
        description="Audit Trellis handbook structure without changing the work folder.",
        epilog=(
            "Default ceilings: "
            f"{DEFAULT_MAX_FILE_BYTES} bytes/file, "
            f"{DEFAULT_MAX_TOTAL_BYTES} bytes total, "
            f"{DEFAULT_MAX_ENTRIES} directory entries, depth {DEFAULT_MAX_DEPTH}, "
            f"{DEFAULT_MAX_FINDINGS} findings, {DEFAULT_MAX_WORK_UNITS} work units, "
            f"and {DEFAULT_MAX_OUTPUT_BYTES} output bytes."
        ),
    )
    parser.add_argument(
        "--target",
        type=LocalPath,
        required=True,
        help="Absolute work-folder path to inspect.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    return parser.parse_args(argv)


def safe_os_error(exc: OSError) -> str:
    """Describe an operating-system failure without echoing an absolute path."""
    return exc.strerror or exc.__class__.__name__


def check_regular_file(
    context: AuditContext,
    path: RepoPath,
    target: RepoPath,
    findings: list[Finding],
    code: str,
    label: str,
) -> bool:
    location = relative(path, target)
    if not context.root.exists(path):
        findings.append(finding(f"{code}-missing", location, f"{label} is missing"))
        return False
    if context.root.is_symlink(path):
        findings.append(
            finding(f"{code}-symlink", location, f"{label} must not be a symlink")
        )
        return False
    if not context.root.is_file(path):
        findings.append(
            finding(f"{code}-not-file", location, f"{label} must be a regular file")
        )
        return False
    if not is_within(context.root.resolve(path), target):
        findings.append(
            finding(f"{code}-escapes", location, f"{label} leaves the work folder")
        )
        return False
    return True


def run(context: AuditContext) -> tuple[list[Finding], list[Suggestion]]:
    from .actions import check_action_runtime
    from .handbook import check_agents_reference, check_handbook
    from .runtime import check_private_scratch

    root = context.root.path
    findings: list[Finding] = context.findings
    captures = check_handbook(context, root, findings)
    check_private_scratch(context, root, findings)
    actions = [capture for capture in captures if capture.section == "actions"]
    check_action_runtime(context, root, actions, findings)
    suggestion = check_agents_reference(context, root, findings)
    context.root.revalidate_all()
    suggestions = [suggestion] if suggestion else []
    return (
        sorted(findings, key=lambda item: (item.path, item.code, item.message)),
        suggestions,
    )


def print_result(
    target: LocalPath,
    findings: list[Finding],
    suggestions: list[Suggestion],
    as_json: bool,
    limits: AuditLimits = DEFAULT_LIMITS,
) -> None:
    if as_json:
        payload = {
            "schema": JSON_SCHEMA,
            "status": "findings" if findings else "ok",
            "target": ".",
            "limits": {
                "maxDepth": limits.max_depth,
                "maxEntries": limits.max_entries,
                "maxFileBytes": limits.max_file_bytes,
                "maxFindings": limits.max_findings,
                "maxOutputBytes": limits.max_output_bytes,
                "maxTotalBytes": limits.max_total_bytes,
                "maxWorkUnits": limits.max_work_units,
            },
            "findings": [asdict(finding) for finding in findings],
            "suggestions": [asdict(suggestion) for suggestion in suggestions],
        }
        output = json.dumps(payload, indent=2, sort_keys=True)
    else:
        lines: list[str] = []
        if not findings:
            lines.append("Trellis structural audit: OK")
        else:
            lines.append(f"Trellis structural audit: {len(findings)} finding(s)")
            for kind, heading in (
                ("integrity", "Integrity failures"),
                ("validation-needed", "Validation needed"),
            ):
                selected = [finding for finding in findings if finding.kind == kind]
                if not selected:
                    continue
                lines.extend(("", f"{heading}:"))
                lines.extend(
                    f"- [{finding.code}] {finding.path}: {finding.message}"
                    for finding in selected
                )
        if suggestions:
            lines.extend(("", "Owner-controlled instruction suggestion (not written):"))
            for suggestion in suggestions:
                lines.append(
                    f"- [{suggestion.code}] {suggestion.path}: {suggestion.message}"
                )
                lines.append(f"  {suggestion.suggested_line}")
        output = "\n".join(lines)
    if len(output.encode("utf-8")) > limits.max_output_bytes:
        raise ResourceLimitError(
            "output-limit",
            f"audit output exceeds {limits.max_output_bytes} bytes",
        )
    print(output)


def json_requested(argv: Sequence[str] | None) -> bool:
    values = tuple(sys.argv[1:] if argv is None else argv)
    return "--json" in values


def bounded_error_message(message: str) -> str:
    encoded = message.encode("utf-8")
    if len(encoded) <= DEFAULT_MAX_ERROR_MESSAGE_BYTES:
        return message
    prefix = encoded[: DEFAULT_MAX_ERROR_MESSAGE_BYTES - 3].decode(
        "utf-8", errors="ignore"
    )
    return prefix + "..."


def print_error(exc: InvocationError, as_json: bool) -> None:
    message = bounded_error_message(str(exc))
    if as_json:
        payload = {
            "schema": JSON_SCHEMA,
            "status": "error",
            "error": {"code": exc.code, "message": message},
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"error: {message}", file=sys.stderr)


def main(
    argv: Sequence[str] | None = None, limits: AuditLimits = DEFAULT_LIMITS
) -> int:
    as_json = json_requested(argv)
    # This shipped helper can be invoked before the repository's dev gate runs.
    if sys.implementation.name != "cpython" or sys.version_info < (3, 11):
        print_error(
            InvocationError(
                "unsupported-python",
                "Trellis Audit requires CPython 3.11 or newer",
            ),
            as_json,
        )
        return 2
    try:
        args = parse_args(argv)
        as_json = args.json
        context = AuditContext.open(args.target, limits)
        target = context.root.absolute
        findings, suggestions = run(context)
        print_result(target, findings, suggestions, args.json, limits)
    except InvocationError as exc:
        print_error(exc, as_json)
        return 2
    except OSError as exc:
        print_error(
            InvocationError(
                "filesystem-error",
                f"could not inspect the target: {safe_os_error(exc)}",
            ),
            as_json,
        )
        return 2
    except (RecursionError, UnicodeError, ValueError):
        print_error(
            InvocationError(
                "content-malformed",
                "target content could not be parsed safely",
            ),
            as_json,
        )
        return 2

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

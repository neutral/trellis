"""Fixed, privacy-preserving diagnostics for the Trellis audit."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import NoReturn

JSON_SCHEMA = "trellis.audit-result.v1"
MAX_DIAGNOSTIC_PATH_BYTES = 1024
UNSAFE_PATH_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})


def unsafe_path_character(character: str) -> bool:
    """Return whether a character can alter terminal or line-oriented output."""
    return unicodedata.category(character) in UNSAFE_PATH_CATEGORIES


_SUGGESTED_LINES = MappingProxyType(
    {
        "agents-handbook-reference": (
            "When relevant, read [`_handbook/overview.md`](_handbook/overview.md) "
            "for project Playbooks and Actions."
        )
    }
)

_MESSAGE_OVERRIDES = MappingProxyType(
    {
        "action-run-missing": (
            "Action Run instructions are missing a required command, including "
            "show-plan when applicable"
        ),
        "agents-handbook-reference": "AGENTS.md does not reference the handbook",
        "playbook-page-heading": (
            "Playbook page is missing a required heading, including Boundaries"
        ),
    }
)

_FINDING_CODES = frozenset(
    """
action-access-change-forbidden action-area action-capability-forbidden action-case-collision action-delete-forbidden action-dependency action-dependency-drift action-dependency-opaque action-dependency-undeclared action-dependency-unused action-digest action-digest-drift action-direct-write-forbidden action-directory-content action-directory-malformed action-directory-symlink action-docs action-docs-escapes action-docs-mismatch action-docs-missing action-docs-not-file action-docs-symlink action-effect-scope action-effect-undeclared action-effect-unproven action-effects action-effects-mismatch action-entrypoint action-entrypoint-escapes action-entrypoint-missing action-entrypoint-not-file action-entrypoint-symlink action-envelope-missing action-execution action-execution-drift action-execution-effects action-execution-output action-group-content action-group-empty action-id action-id-reserved action-implementation-missing action-import-builtin-prefix action-import-forbidden action-import-malformed action-input action-input-implementation-mismatch action-input-mismatch action-input-path action-kitchen-sink action-leaf-child action-lifecycle action-lifecycle-mismatch action-local-import action-manifest action-manifest-escapes action-manifest-field action-manifest-format action-manifest-json action-manifest-missing action-manifest-not-file action-manifest-symlink action-manifest-version action-method-confidence action-orphan action-output action-output-implementation-mismatch action-output-mismatch action-package-dependency-missing action-page-heading action-page-location action-page-state action-page-state-evidence action-page-title action-path-forbidden action-plan-implementation-unproven action-plan-output-unproven action-read-path-forbidden action-readiness action-readiness-drift action-responsibility-forbidden action-review-trigger action-review-trigger-mismatch action-run-input-mismatch action-run-mismatch action-run-missing action-source-inventory action-source-undigested action-state-mismatch action-static-validation action-success action-success-mismatch action-temporary-forbidden action-test action-test-drift action-test-escapes action-test-incomplete action-test-mismatch action-test-missing action-test-not-file action-test-symlink action-title-mismatch action-untested action-verification-implementation-mismatch action-verification-mismatch capture-anchor capture-area capture-area-unreadable capture-duplicate capture-escapes capture-external capture-format capture-kind capture-link-malformed capture-marker capture-missing capture-not-file capture-orphan capture-path-unstable capture-section capture-symlink cli-root dependency-not-exact dependency-policy handbook-escapes handbook-format handbook-marker-order handbook-markers handbook-missing handbook-not-file handbook-section handbook-symlink lockfile-drift lockfile-escapes lockfile-integrity lockfile-json lockfile-missing lockfile-not-file lockfile-policy lockfile-source lockfile-symlink not-utf8 npmrc npmrc-credential npmrc-duplicate npmrc-escapes npmrc-missing npmrc-not-file npmrc-policy npmrc-symlink npmrc-syntax npmrc-unexpected package package-dev-engines package-engines package-escapes package-json package-lifecycle-script package-missing package-not-file package-policy package-scripts package-scripts-policy package-symlink package-unexpected playbook-page-heading scratch-gitignore scratch-gitignore-drift scratch-gitignore-escapes scratch-gitignore-missing scratch-gitignore-not-file scratch-gitignore-symlink scratch-missing scratch-readme scratch-readme-drift scratch-readme-escapes scratch-readme-missing scratch-readme-not-file scratch-readme-symlink scratch-root trellis-cli trellis-cli-drift trellis-cli-escapes trellis-cli-missing trellis-cli-not-file trellis-cli-symlink trellis-cli-test trellis-cli-test-drift trellis-cli-test-escapes trellis-cli-test-missing trellis-cli-test-not-file trellis-cli-test-symlink trellis-gitignore trellis-gitignore-drift trellis-gitignore-escapes trellis-gitignore-missing trellis-gitignore-not-file trellis-gitignore-symlink trellis-guard trellis-guard-drift trellis-guard-escapes trellis-guard-missing trellis-guard-not-file trellis-guard-symlink trellis-launcher trellis-launcher-drift trellis-launcher-escapes trellis-launcher-format trellis-launcher-missing trellis-launcher-mode trellis-launcher-not-file trellis-launcher-symlink trellis-runner trellis-runner-drift trellis-runner-escapes trellis-runner-format trellis-runner-missing trellis-runner-not-file trellis-runner-symlink unreadable
    """.split()
)


def fixed_message(code: str) -> str:
    """Return catalog text without incorporating inspected values."""
    if code not in _FINDING_CODES and code != "agents-handbook-reference":
        raise ValueError(f"unknown audit finding code: {code}")
    override = _MESSAGE_OVERRIDES.get(code)
    if override is not None:
        return override
    return f"Trellis audit rule {code} was not satisfied"


_ERROR_MESSAGES = MappingProxyType(
    {
        "content-malformed": "target content could not be parsed safely",
        "depth-limit": "audit path depth exceeds its configured limit",
        "entry-limit": "audit directory entries exceed the configured limit",
        "file-size-limit": "a file exceeds the configured audit limit",
        "filesystem-error": "the target could not be inspected safely",
        "finding-limit": "audit findings exceed the configured limit",
        "invalid-arguments": "invalid command-line arguments; use --help",
        "output-limit": "audit output exceeds the configured limit",
        "path-escape": "audit attempted to inspect outside its target",
        "path-identity-changed": (
            "audit path identity changed during inspection; retry on a stable folder"
        ),
        "path-identity-unavailable": (
            "audit path identity is unavailable on this filesystem"
        ),
        "path-malformed": "refusing a malformed audit path",
        "path-type": "audit path has an unexpected filesystem type",
        "target-missing": "target does not exist",
        "target-not-directory": "target is not a directory",
        "target-not-absolute": "target must be an explicit absolute path",
        "target-root": "refusing to inspect a filesystem root",
        "target-symlink": "refusing to inspect a symlinked target",
        "target-unavailable": "target could not be resolved safely",
        "total-size-limit": "files read by the audit exceed the configured total limit",
        "unsupported-python": "Trellis Audit requires CPython 3.11 or newer",
        "work-limit": "audit work exceeds the configured operation limit",
    }
)


class InvocationError(Exception):
    """The requested target cannot be audited safely."""

    def __init__(self, code: str, message: str | None = None) -> None:
        del message
        fixed = _ERROR_MESSAGES.get(code)
        if fixed is None:
            raise ValueError(f"unknown audit error code: {code}")
        super().__init__(fixed)
        self.code = code


class ResourceLimitError(InvocationError):
    """The audit stopped before deterministic resource ceilings were crossed."""


class DiagnosticPath(str):
    """A validated repository-relative display path safe for report output."""

    def __new__(cls, value: str) -> DiagnosticPath:
        if (
            not value
            or len(value.encode("utf-8")) > MAX_DIAGNOSTIC_PATH_BYTES
            or "\\" in value
            or any(unsafe_path_character(character) for character in value)
        ):
            raise ValueError("unsafe diagnostic path")
        base, separator, line = value.rpartition(":")
        if separator:
            if not line.isascii() or not line.isdigit() or not base:
                raise ValueError("unsafe diagnostic path")
        else:
            base = value
        if base != ".":
            parsed = PurePosixPath(base)
            if (
                parsed.is_absolute()
                or parsed.parts[0].endswith(":")
                or any(part in {"", ".", ".."} for part in parsed.parts)
                or parsed.as_posix() != base
            ):
                raise ValueError("unsafe diagnostic path")
        return str.__new__(cls, value)


def diagnostic_path(value: str) -> DiagnosticPath:
    """Validate one canonical repository-relative path without echoing failures."""
    return DiagnosticPath(value)


@dataclass(frozen=True, init=False)
class Finding:
    """One catalog-backed finding; caller text is intentionally discarded."""

    code: str
    path: str
    message: str
    kind: str

    def __init__(
        self,
        code: str,
        path: DiagnosticPath,
        message: str | None = None,
        kind: str = "integrity",
    ) -> None:
        del message
        if kind not in {"integrity", "validation-needed"}:
            raise ValueError("unknown audit finding kind")
        if not isinstance(path, DiagnosticPath):
            raise ValueError("unvalidated diagnostic path")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "path", str(path))
        object.__setattr__(self, "message", fixed_message(code))
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True, init=False)
class Suggestion:
    """One catalog-backed, non-mutating owner suggestion."""

    code: str
    path: str
    message: str
    suggested_line: str

    def __init__(self, code: str, path: DiagnosticPath) -> None:
        if not isinstance(path, DiagnosticPath):
            raise ValueError("unvalidated diagnostic path")
        suggested_line = _SUGGESTED_LINES.get(code)
        if suggested_line is None:
            raise ValueError("unknown audit suggestion code")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "path", str(path))
        object.__setattr__(self, "message", fixed_message(code))
        object.__setattr__(self, "suggested_line", suggested_line)


def finding(
    code: str,
    path: DiagnosticPath,
    _discarded_message: str | None = None,
    kind: str = "integrity",
) -> Finding:
    """Construct a finding only through the closed diagnostic catalog."""
    return Finding(code, path, None, kind)


def suggestion(code: str, path: DiagnosticPath) -> Suggestion:
    """Construct a suggestion only through the closed diagnostic catalog."""
    return Suggestion(code, path)


class FindingList(list[Finding]):
    """A list that fails closed before report construction becomes unbounded."""

    def __init__(self, limit: int, max_output_bytes: int) -> None:
        super().__init__()
        self.limit = limit
        self.max_output_bytes = max_output_bytes
        self.output_bytes = 0

    def append(self, finding: Finding) -> None:
        if len(self) >= self.limit:
            raise ResourceLimitError("finding-limit")
        estimated_bytes = sum(
            len(value.encode("utf-8"))
            for value in (finding.code, finding.path, finding.message, finding.kind)
        )
        self.output_bytes += estimated_bytes
        if self.output_bytes > self.max_output_bytes:
            raise ResourceLimitError("output-limit")
        super().append(finding)


class AuditArgumentError(InvocationError):
    """Marker subtype used by the non-exiting argument parser."""


def unreachable() -> NoReturn:
    """Make impossible catalog states explicit to type checkers."""
    raise RuntimeError("unreachable audit state")

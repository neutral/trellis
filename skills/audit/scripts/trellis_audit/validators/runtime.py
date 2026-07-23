"""Focused runtime validators for Trellis Audit."""

from __future__ import annotations

import hashlib
import re

from ..context import AuditContext
from ..diagnostics import Finding, diagnostic_path, finding
from ..filesystem import (
    RepoPath,
    is_within,
    list_entries_bounded,
    read_bytes_bounded,
    read_text,
    relative,
)
from ..models import is_json_object
from .core import (
    EXACT_VERSION_RE,
    EXPECTED_NPMRC,
    EXPECTED_RUNTIME_SHA256,
    PACKAGE_ALLOWED_KEYS,
    PACKAGE_NAME_RE,
    PINNED_SCRIPT_RE,
    check_regular_file,
    safe_os_error,
)
from .manifest import read_json

SCRATCH_LOCATION = diagnostic_path("_handbook/_scratch")
NPMRC_LOCATION = diagnostic_path("_handbook/_cli/.npmrc")
PACKAGE_LOCATION = diagnostic_path("_handbook/_cli/package.json")
LOCKFILE_LOCATION = diagnostic_path("_handbook/_cli/package-lock.json")


def check_private_scratch(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> None:
    scratch = target / "_handbook" / "_scratch"
    location = SCRATCH_LOCATION
    if not context.root.exists(scratch) and not context.root.is_symlink(scratch):
        findings.append(
            finding(
                "scratch-missing",
                location,
                "private Trellis scratch directory is missing",
            )
        )
        return
    if context.root.is_symlink(scratch) or not context.root.is_dir(scratch):
        findings.append(
            finding(
                "scratch-root",
                location,
                "private Trellis scratch must be a regular local directory, not a symlink",
            )
        )
        return
    if not is_within(context.root.resolve(scratch), target):
        findings.append(
            finding(
                "scratch-root",
                location,
                "private Trellis scratch leaves the work folder",
            )
        )
        return
    check_runtime_file(
        context,
        target,
        "_handbook/_scratch/.gitignore",
        findings,
        "scratch-gitignore",
        "Trellis scratch ignore policy",
    )
    check_runtime_file(
        context,
        target,
        "_handbook/_scratch/README.md",
        findings,
        "scratch-readme",
        "Trellis scratch privacy guidance",
    )


def check_action_source_inventory(
    context: AuditContext,
    action_dir: RepoPath,
    target: RepoPath,
    findings: list[Finding],
) -> None:
    """Require the closed three-file Action directory covered by the contract."""
    allowed = {"action.json", "run.mjs", "run.test.mjs"}
    try:
        candidates = list_entries_bounded(action_dir)
        names = {candidate.name for candidate in candidates}
        for missing in sorted(allowed - names):
            findings.append(
                finding(
                    "action-directory-content",
                    relative(action_dir / missing, target),
                    f"Action directory is missing required regular file: {missing}",
                )
            )
        for candidate in candidates:
            if candidate.name in allowed:
                if context.root.is_symlink(candidate) or not context.root.is_file(
                    candidate
                ):
                    findings.append(
                        finding(
                            "action-directory-content",
                            relative(candidate, target),
                            f"required Action entry must be a regular file: {candidate.name}",
                        )
                    )
                continue
            executable = candidate.suffix.casefold() in {".js", ".mjs", ".cjs"}
            findings.append(
                finding(
                    "action-source-undigested"
                    if executable
                    else "action-directory-content",
                    relative(candidate, target),
                    (
                        "executable Action helper source is outside the manifest digest contract"
                        if executable
                        else "Action directory may contain only regular action.json, run.mjs, and run.test.mjs files"
                    ),
                )
            )
    except OSError as exc:
        findings.append(
            finding(
                "action-source-inventory",
                relative(action_dir, target),
                f"could not inventory Action source: {safe_os_error(exc)}",
            )
        )


def parse_npmrc(
    context: AuditContext,
    path: RepoPath,
    target: RepoPath,
    findings: list[Finding],
) -> dict[str, str]:
    content = read_text(path, target, findings)
    if content is None:
        return {}
    parsed: dict[str, str] = {}
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        context.budget.charge_work()
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if "=" not in line:
            findings.append(
                finding(
                    "npmrc-syntax",
                    diagnostic_path(f"_handbook/_cli/.npmrc:{line_number}"),
                    "expected key=value",
                )
            )
            continue
        raw_key, value = (part.strip() for part in line.split("=", 1))
        key = raw_key.lower()
        if key in parsed:
            findings.append(
                finding(
                    "npmrc-duplicate",
                    diagnostic_path(f"_handbook/_cli/.npmrc:{line_number}"),
                    "duplicate npm setting; key redacted",
                )
            )
        parsed[key] = value
        if re.search(
            r"(?:^|:)(?:_auth|_authtoken|username|password|certfile|keyfile|cafile)$",
            key,
            re.I,
        ):
            findings.append(
                finding(
                    "npmrc-credential",
                    diagnostic_path(f"_handbook/_cli/.npmrc:{line_number}"),
                    "committed npm policy must not contain credentials",
                )
            )
        if key not in EXPECTED_NPMRC:
            findings.append(
                finding(
                    "npmrc-unexpected",
                    diagnostic_path(f"_handbook/_cli/.npmrc:{line_number}"),
                    "unexpected project npm setting; key and value redacted",
                )
            )
    return parsed


def check_npm_policy(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> None:
    npmrc = target / "_handbook" / "_cli" / ".npmrc"
    if not check_regular_file(context, npmrc, target, findings, "npmrc", "npm policy"):
        return
    parsed = parse_npmrc(context, npmrc, target, findings)
    for key, expected in EXPECTED_NPMRC.items():
        actual = parsed.get(key)
        if actual != expected:
            findings.append(
                finding(
                    "npmrc-policy",
                    NPMRC_LOCATION,
                    f"npm setting {key} differs from the required policy value",
                )
            )


def check_runtime_file(
    context: AuditContext,
    target: RepoPath,
    relative_path: str,
    findings: list[Finding],
    code: str,
    label: str,
) -> bool:
    path = target / relative_path
    location = relative(path, target)
    if not check_regular_file(context, path, target, findings, code, label):
        return False
    try:
        digest = hashlib.sha256(read_bytes_bounded(path)).hexdigest()
    except OSError as exc:
        findings.append(
            finding(
                code,
                location,
                f"could not hash {label}: {safe_os_error(exc)}",
            )
        )
        return False
    if digest != EXPECTED_RUNTIME_SHA256[relative_path]:
        findings.append(
            finding(
                f"{code}-drift",
                location,
                f"{label} differs from the reviewed Trellis runtime",
            )
        )
        return False
    return True


def check_package(
    context: AuditContext, target: RepoPath, findings: list[Finding]
) -> None:
    path = target / "_handbook" / "_cli" / "package.json"
    if not check_regular_file(
        context, path, target, findings, "package", "tool package manifest"
    ):
        return
    package = read_json(context, path, target, findings, "package-json")
    if package is None:
        return
    if not is_json_object(package):
        findings.append(
            finding(
                "package-json",
                PACKAGE_LOCATION,
                "tool package manifest must contain a JSON object",
            )
        )
        return
    extra_keys = sorted(set(package) - PACKAGE_ALLOWED_KEYS)
    if extra_keys:
        findings.append(
            finding(
                "package-unexpected",
                PACKAGE_LOCATION,
                f"tool package manifest contains {len(extra_keys)} unexpected field(s); names redacted",
            )
        )
    expected = {
        "name": "trellis-local-actions",
        "version": "0.0.0",
        "private": True,
        "license": "CC0-1.0",
        "type": "module",
        "packageManager": "npm@11.16.0",
    }
    for key, value in expected.items():
        if package.get(key) != value:
            findings.append(
                finding(
                    "package-policy",
                    PACKAGE_LOCATION,
                    f"package field {key} differs from the required policy value",
                )
            )
    if package.get("engines") != {
        "node": ">=22.23.1 <23 || >=24.18.0 <25",
        "npm": "11.16.0",
    }:
        findings.append(
            finding(
                "package-engines",
                PACKAGE_LOCATION,
                "Node/npm engine policy drifted",
            )
        )
    dev_engines = package.get("devEngines")
    if (
        not is_json_object(dev_engines)
        or dev_engines.get("runtime")
        != {
            "name": "node",
            "version": ">=22.23.1 <23 || >=24.18.0 <25",
            "onFail": "error",
        }
        or dev_engines.get("packageManager")
        != {
            "name": "npm",
            "version": "11.16.0",
            "onFail": "error",
        }
    ):
        findings.append(
            finding(
                "package-dev-engines",
                PACKAGE_LOCATION,
                "npm devEngines policy drifted",
            )
        )
    allow_scripts = package.get("allowScripts")
    approved_script_pins: list[tuple[str, str]] = []
    if not is_json_object(allow_scripts):
        findings.append(
            finding(
                "package-scripts-policy",
                PACKAGE_LOCATION,
                "allowScripts must be an object",
            )
        )
    else:
        for package_spec, decision in allow_scripts.items():
            context.budget.charge_work()
            pin = PINNED_SCRIPT_RE.fullmatch(package_spec)
            valid_approval = decision is True and pin is not None
            valid_denial = decision is False and PACKAGE_NAME_RE.fullmatch(package_spec)
            if not (valid_approval or valid_denial):
                findings.append(
                    finding(
                        "package-scripts-policy",
                        PACKAGE_LOCATION,
                        "allowScripts entries must be exact-version approvals or name-only denials",
                    )
                )
            elif valid_approval and pin is not None:
                approved_script_pins.append((pin.group(1), pin.group(2)))
    scripts = package.get("scripts")
    required_scripts = {
        "test": "node --test --experimental-test-isolation=none",
        "trellis": "node ./bin/trellis.mjs",
    }
    if not is_json_object(scripts):
        findings.append(
            finding(
                "package-scripts",
                PACKAGE_LOCATION,
                "scripts must be an object",
            )
        )
    elif scripts != required_scripts:
        findings.append(
            finding(
                "package-scripts",
                PACKAGE_LOCATION,
                "scripts must contain only the reviewed test and trellis commands",
            )
        )
    if is_json_object(scripts):
        lifecycle_names = {
            "preinstall",
            "install",
            "postinstall",
            "prepare",
            "prepublish",
            "prepublishOnly",
            "prepack",
            "postpack",
            "pretest",
            "posttest",
            "pretrellis",
            "posttrellis",
        }
        prohibited = sorted(lifecycle_names.intersection(scripts))
        if prohibited:
            findings.append(
                finding(
                    "package-lifecycle-script",
                    PACKAGE_LOCATION,
                    f"lifecycle hooks are not allowed: {', '.join(prohibited)}",
                )
            )
    dependency_sections: dict[str, str] = {}
    dependency_versions: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        dependencies = package.get(section, {})
        if not is_json_object(dependencies):
            findings.append(
                finding(
                    "dependency-policy",
                    PACKAGE_LOCATION,
                    f"{section} must be an object",
                )
            )
            continue
        for name, version in dependencies.items():
            context.budget.charge_work()
            if not PACKAGE_NAME_RE.fullmatch(name):
                findings.append(
                    finding(
                        "dependency-policy",
                        PACKAGE_LOCATION,
                        f"{section} contains an invalid registry package name; value redacted",
                    )
                )
            if name in dependency_sections:
                findings.append(
                    finding(
                        "dependency-policy",
                        PACKAGE_LOCATION,
                        f"a dependency appears in both {dependency_sections[name]} and {section}; package name redacted",
                    )
                )
            else:
                dependency_sections[name] = section
            if not isinstance(version, str) or not EXACT_VERSION_RE.fullmatch(version):
                findings.append(
                    finding(
                        "dependency-not-exact",
                        PACKAGE_LOCATION,
                        f"{section} contains a dependency without one exact registry version; values redacted",
                    )
                )
            else:
                dependency_versions[name] = version
    if "peerDependencies" in package:
        findings.append(
            finding(
                "dependency-policy",
                PACKAGE_LOCATION,
                "local Action tools must not declare peerDependencies",
            )
        )

    lock = target / "_handbook" / "_cli" / "package-lock.json"
    if check_regular_file(context, lock, target, findings, "lockfile", "tool lockfile"):
        lock_data = read_json(context, lock, target, findings, "lockfile-json")
        if not is_json_object(lock_data) or lock_data.get("lockfileVersion") != 3:
            findings.append(
                finding(
                    "lockfile-policy",
                    LOCKFILE_LOCATION,
                    "expected lockfileVersion 3",
                )
            )
        elif not is_json_object(packages_value := lock_data.get("packages")):
            findings.append(
                finding(
                    "lockfile-policy",
                    LOCKFILE_LOCATION,
                    "packages map is missing",
                )
            )
        else:
            packages = packages_value
            locked_versions: dict[str, set[str]] = {}
            if lock_data.get("name") != package.get("name") or lock_data.get(
                "version"
            ) != package.get("version"):
                findings.append(
                    finding(
                        "lockfile-drift",
                        LOCKFILE_LOCATION,
                        "lockfile name or version does not match package.json",
                    )
                )
            if lock_data.get("requires") is not True:
                findings.append(
                    finding(
                        "lockfile-policy",
                        LOCKFILE_LOCATION,
                        "lockfile must declare requires=true",
                    )
                )
            root_entry = packages.get("")
            if not is_json_object(root_entry):
                findings.append(
                    finding(
                        "lockfile-policy",
                        LOCKFILE_LOCATION,
                        "root package entry is missing",
                    )
                )
            else:
                for key in ("name", "version", "license", "engines"):
                    if root_entry.get(key) != package.get(key):
                        findings.append(
                            finding(
                                "lockfile-drift",
                                LOCKFILE_LOCATION,
                                f"root {key} does not match package.json",
                            )
                        )
                for section in (
                    "dependencies",
                    "devDependencies",
                    "optionalDependencies",
                ):
                    if root_entry.get(section, {}) != package.get(section, {}):
                        findings.append(
                            finding(
                                "lockfile-drift",
                                LOCKFILE_LOCATION,
                                f"root {section} does not match package.json",
                            )
                        )
            for package_path, entry in packages.items():
                context.budget.charge_work()
                if package_path == "":
                    continue
                if not is_json_object(entry):
                    findings.append(
                        finding(
                            "lockfile-policy",
                            LOCKFILE_LOCATION,
                            "lock entry must be an object; package path redacted",
                        )
                    )
                    continue
                resolved = entry.get("resolved")
                integrity = entry.get("integrity")
                package_tail = package_path.rpartition("node_modules/")[2]
                package_parts = package_tail.split("/")
                if package_tail.startswith("@") and len(package_parts) >= 2:
                    locked_name = "/".join(package_parts[:2])
                else:
                    locked_name = package_parts[0]
                locked_version = entry.get("version")
                if locked_name and isinstance(locked_version, str):
                    locked_versions.setdefault(locked_name, set()).add(locked_version)
                if entry.get("link") is True or not (
                    isinstance(resolved, str)
                    and resolved.startswith("https://registry.npmjs.org/")
                ):
                    findings.append(
                        finding(
                            "lockfile-source",
                            LOCKFILE_LOCATION,
                            "non-registry package source; package path and URL redacted",
                        )
                    )
                if not isinstance(integrity, str) or not integrity.startswith(
                    "sha512-"
                ):
                    findings.append(
                        finding(
                            "lockfile-integrity",
                            LOCKFILE_LOCATION,
                            "sha512 integrity is missing; package path redacted",
                        )
                    )
            for approved_name, approved_version in approved_script_pins:
                context.budget.charge_work()
                if approved_version not in locked_versions.get(approved_name, set()):
                    findings.append(
                        finding(
                            "package-scripts-policy",
                            PACKAGE_LOCATION,
                            "an approved script release is not locked; package details redacted",
                        )
                    )
            for dependency_name, expected_version in dependency_versions.items():
                context.budget.charge_work()
                direct_entry = packages.get(f"node_modules/{dependency_name}")
                if (
                    not is_json_object(direct_entry)
                    or direct_entry.get("version") != expected_version
                ):
                    findings.append(
                        finding(
                            "lockfile-drift",
                            LOCKFILE_LOCATION,
                            "a direct dependency is not locked at its declared version; package details redacted",
                        )
                    )

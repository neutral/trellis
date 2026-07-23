"""Focused manifest validators for Trellis Audit."""

from __future__ import annotations

import hashlib
import json
import math
import posixpath
import re
from collections.abc import Mapping, Set
from datetime import datetime
from typing import TypeGuard

from ..context import AuditContext
from ..diagnostics import Finding, finding, unsafe_path_character
from ..filesystem import RepoPath, is_within, read_bytes_bounded, relative
from ..models import (
    ActionManifest,
    is_json_array,
    is_json_object,
    json_fingerprint,
)
from .core import (
    DIGEST_RE,
    EFFECT_KEYS,
    EXACT_VERSION_RE,
    FORBIDDEN_EFFECT_KEYS,
    FORBIDDEN_MANIFEST_KEYS,
    FORBIDDEN_PATH_PARTS,
    FORBIDDEN_SECRET_BASENAMES,
    HARD_RESERVED_HANDBOOK_CHILDREN,
    HARD_RESERVED_SCOPE_ROOTS,
    INPUT_NAME_RE,
    INPUT_TYPES,
    MANIFEST_KEYS,
    OUTPUT_TYPES,
    PACKAGE_NAME_RE,
    PATH_INPUT_TYPES,
    REQUIRED_MANIFEST_KEYS,
    SOFT_PROTECTED_SCOPE_ROOTS,
    check_regular_file,
    safe_os_error,
)


def read_json(
    context: AuditContext,
    path: RepoPath,
    target: RepoPath,
    findings: list[Finding],
    code: str,
) -> object | None:
    try:
        parsed: object = context.root.read_json(path)
        return parsed
    except json.JSONDecodeError as exc:
        findings.append(
            finding(
                code,
                relative(path, target),
                f"invalid JSON: {exc.msg} at line {exc.lineno}",
            )
        )
        return None
    except RecursionError:
        findings.append(
            finding(
                code,
                relative(path, target),
                "invalid JSON: nesting exceeds the supported parser depth",
            )
        )
        return None
    except ValueError:
        findings.append(
            finding(
                code,
                relative(path, target),
                "invalid JSON: numeric or parser limit exceeded",
            )
        )
        return None


def valid_relative_path(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or any(unsafe_path_character(character) for character in value)
    ):
        return False
    normalized = value.replace("\\", "/")
    if (
        normalized.startswith("/")
        or re.match(r"^[A-Za-z]:/", normalized)
        or ".." in normalized.split("/")
        or re.search(r"[$*?\[\]{}]", normalized)
    ):
        return False
    for segment in (part for part in normalized.split("/") if part):
        if segment == ".":
            continue
        base = segment.split(".", 1)[0].upper()
        if (
            re.search(r"[<>:\"|]", segment)
            or segment.endswith((" ", "."))
            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", base)
        ):
            return False
    return True


def valid_scope(scope: object) -> bool:
    return (
        valid_relative_path(scope)
        and isinstance(scope, str)
        and normalize_relative_path(scope) != "."
    )


def normalize_relative_path(scope: str) -> str:
    normalized = scope.replace("\\", "/")
    directory_hint = normalized.endswith("/")
    result = posixpath.normpath(normalized)
    if result == "":
        result = "."
    if directory_hint and result != ".":
        result += "/"
    return result


def scope_stays_in_repository(
    context: AuditContext, scope: str, target: RepoPath
) -> bool:
    return is_within(context.root.resolve(target / scope), target)


def forbidden_scope_reason(scope: str) -> str | None:
    normalized = scope.replace("\\", "/").rstrip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    lowered = [part.lower() for part in parts]
    if any(part in FORBIDDEN_PATH_PARTS for part in lowered):
        return "scope targets repository metadata or a credential directory"
    if lowered:
        basename = lowered[-1]
        if (
            basename in FORBIDDEN_SECRET_BASENAMES
            or basename == ".env"
            or basename.startswith(".env.")
            or re.search(
                r"(?:^|[-_.])(password|secret|token|private[-_]?key)(?:$|[-_.])",
                basename,
            )
        ):
            return "scope targets a likely credential or secret file"
    return None


def reserved_scope_reason(
    scope: str, effect: str, *, dynamic: bool = False
) -> str | None:
    normalized = scope.replace("\\", "/")
    parts = [
        part for part in normalized.rstrip("/").split("/") if part not in ("", ".")
    ]
    if not parts:
        return "scope is the whole work folder"
    first = parts[0].casefold()
    if first in HARD_RESERVED_SCOPE_ROOTS:
        return "scope targets runner, agent, or repository control material"
    if first == "_handbook":
        if len(parts) == 1:
            return "scope contains private Trellis runtime or scratch state"
        if parts[1].casefold() in HARD_RESERVED_HANDBOOK_CHILDREN:
            return "scope targets private Trellis runtime or scratch state"
    if effect != "reads" and first in SOFT_PROTECTED_SCOPE_ROOTS:
        explicit_single_file = (
            not dynamic and len(parts) > 1 and not normalized.endswith("/")
        )
        if not explicit_single_file:
            return (
                "write scope broadly targets protected handbook or instruction material"
            )
    return None


def string_list_status(
    context: AuditContext, value: object, *, require_nonempty: bool
) -> tuple[bool, bool]:
    """Validate a JSON string list once while charging for every item."""
    if not is_json_array(value):
        return False, False
    valid = bool(value) or not require_nonempty
    duplicate = False
    seen: set[str] = set()
    for item in value:
        context.budget.charge_work()
        if not isinstance(item, str) or not item.strip():
            valid = False
            continue
        if item in seen:
            duplicate = True
        else:
            seen.add(item)
    return valid, duplicate


def nonempty_string_list(context: AuditContext, value: object) -> bool:
    valid, duplicate = string_list_status(context, value, require_nonempty=True)
    return valid and not duplicate


def is_integral_number(value: object) -> TypeGuard[int | float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value) and value.is_integer()


def is_safe_integer(value: object) -> TypeGuard[int | float]:
    return is_integral_number(value) and abs(value) <= 9_007_199_254_740_991


def input_value_matches_type(
    context: AuditContext, value: object, input_type: object
) -> bool:
    if input_type in {"string", "path", "file", "directory"}:
        return isinstance(value, str) and bool(value.strip())
    if input_type == "boolean":
        return isinstance(value, bool)
    if input_type == "integer":
        return is_safe_integer(value)
    if input_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    if input_type == "string-list":
        if not is_json_array(value):
            return False
        seen: set[str] = set()
        valid = True
        for item in value:
            context.budget.charge_work()
            if not isinstance(item, str) or not item.strip() or item in seen:
                valid = False
            elif isinstance(item, str):
                seen.add(item)
        return valid
    return False


def valid_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def mapping_shape(
    context: AuditContext,
    value: object,
    *,
    required: Set[str],
    optional: Set[str] = frozenset(),
) -> tuple[Mapping[str, object] | None, list[str], list[str]]:
    if not is_json_object(value):
        return None, sorted(required), []
    missing = sorted(key for key in required if key not in value)
    extras: list[str] = []
    for key in value:
        context.budget.charge_work()
        if key not in required and key not in optional:
            extras.append(key)
    extras.sort()
    return value, missing, extras


def check_action_manifest(
    context: AuditContext,
    action_id: str,
    action_dir: RepoPath,
    page_path: RepoPath | None,
    target: RepoPath,
    findings: list[Finding],
) -> ActionManifest | None:
    manifest_path = action_dir / "action.json"
    if not check_regular_file(
        context, manifest_path, target, findings, "action-manifest", "action manifest"
    ):
        return None
    parsed_manifest = read_json(
        context, manifest_path, target, findings, "action-manifest-json"
    )
    if not is_json_object(parsed_manifest):
        return None
    manifest = parsed_manifest
    manifest_location = relative(manifest_path, target)
    manifest_format = manifest.get("format")
    if (
        not isinstance(manifest_format, int)
        or isinstance(manifest_format, bool)
        or manifest_format != 2
    ):
        findings.append(
            finding(
                "action-manifest-format",
                manifest_location,
                "expected format=2; unsupported value redacted",
            )
        )
        return None
    validation_start = len(findings)
    extras: list[str] = []
    for key in manifest:
        context.budget.charge_work()
        if key not in MANIFEST_KEYS:
            extras.append(key)
    extras.sort()
    if extras:
        findings.append(
            finding(
                "action-manifest-field",
                manifest_location,
                f"manifest contains {len(extras)} unsupported action field(s); names redacted",
            )
        )
        forbidden_extras = sorted(
            key for key in extras if key in FORBIDDEN_MANIFEST_KEYS
        )
        if forbidden_extras:
            findings.append(
                finding(
                    "action-capability-forbidden",
                    manifest_location,
                    f"manifest declares permanently forbidden capabilities: {', '.join(forbidden_extras)}",
                )
            )
    missing = sorted(key for key in REQUIRED_MANIFEST_KEYS if key not in manifest)
    if missing:
        findings.append(
            finding(
                "action-manifest-field",
                manifest_location,
                f"missing required action fields: {', '.join(missing)}",
            )
        )
    version = manifest.get("version")
    if not is_safe_integer(version) or version < 1:
        findings.append(
            finding(
                "action-manifest-version",
                manifest_location,
                "version must be a safe integer greater than or equal to 1",
            )
        )
    for field, expected in (
        ("id", action_id),
        ("entrypoint", "run.mjs"),
        ("test", "run.test.mjs"),
    ):
        if manifest.get(field) != expected:
            findings.append(
                finding(
                    "action-manifest-field",
                    manifest_location,
                    f"manifest field {field} differs from its required value",
                )
            )
    for field in ("title", "summary"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(
                finding(
                    "action-manifest-field",
                    manifest_location,
                    f"{field} must be a non-empty string",
                )
            )
    expected_docs = f"_handbook/actions/{action_id}.md"
    docs = manifest.get("docs")
    if not isinstance(docs, str) or not valid_scope(docs):
        findings.append(
            finding(
                "action-docs-mismatch",
                manifest_location,
                "docs must be a safe work-folder-relative path",
            )
        )
    elif not docs.casefold().endswith(".md"):
        findings.append(
            finding(
                "action-docs-mismatch",
                manifest_location,
                "docs must point to a Markdown file",
            )
        )
    elif docs != expected_docs:
        findings.append(
            finding(
                "action-docs-mismatch",
                manifest_location,
                "docs must mirror the Action ID; supplied path redacted",
            )
        )
    elif page_path is None:
        check_regular_file(
            context,
            target / docs,
            target,
            findings,
            "action-docs",
            "Action documentation",
        )

    method, method_missing, method_extras = mapping_shape(
        context,
        manifest.get("methodConfidence"),
        required={"status", "basis", "reviewTriggers"},
    )
    if method is None or method_missing or method_extras:
        findings.append(
            finding(
                "action-method-confidence",
                manifest_location,
                "methodConfidence has an invalid shape; unsupported field names redacted",
            )
        )
    else:
        if method.get("status") not in {"provisional", "established"}:
            findings.append(
                finding(
                    "action-method-confidence",
                    manifest_location,
                    "methodConfidence.status must be provisional or established",
                )
            )
        if not nonempty_string_list(context, method.get("basis")):
            findings.append(
                finding(
                    "action-method-confidence",
                    manifest_location,
                    "methodConfidence.basis must contain a privacy-safe method basis",
                )
            )
        if not nonempty_string_list(context, method.get("reviewTriggers")):
            findings.append(
                finding(
                    "action-review-trigger",
                    manifest_location,
                    "methodConfidence.reviewTriggers must name at least one change-based trigger",
                )
            )

    readiness, readiness_missing, readiness_extras = mapping_shape(
        context,
        manifest.get("readiness"),
        required={"status", "evidence", "validatedAt", "validatedOn"},
    )
    readiness_status: str | None = None
    if readiness is None or readiness_missing or readiness_extras:
        findings.append(
            finding(
                "action-readiness",
                manifest_location,
                "readiness has an invalid shape; unsupported field names redacted",
            )
        )
    else:
        raw_status = readiness.get("status")
        readiness_status = raw_status if isinstance(raw_status, str) else None
        if readiness_status not in {"untested", "tests-passed", "validated"}:
            findings.append(
                finding(
                    "action-readiness",
                    manifest_location,
                    "readiness.status must be untested, tests-passed, or validated",
                )
            )
        evidence = readiness.get("evidence")
        validated_on = readiness.get("validatedOn")
        validated_at = readiness.get("validatedAt")
        evidence_valid, evidence_duplicate = string_list_status(
            context, evidence, require_nonempty=False
        )
        validated_on_valid, validated_on_duplicate = string_list_status(
            context, validated_on, require_nonempty=False
        )
        if not evidence_valid:
            findings.append(
                finding(
                    "action-readiness",
                    manifest_location,
                    "readiness.evidence must be an array of non-empty strings",
                )
            )
        if not validated_on_valid:
            findings.append(
                finding(
                    "action-readiness",
                    manifest_location,
                    "readiness.validatedOn must be an array of non-empty strings",
                )
            )
        for field, duplicate in (
            ("evidence", evidence_duplicate),
            ("validatedOn", validated_on_duplicate),
        ):
            if duplicate:
                findings.append(
                    finding(
                        "action-readiness",
                        manifest_location,
                        f"readiness.{field} must not contain duplicates",
                    )
                )
        if validated_at is not None and not (
            isinstance(validated_at, str) and valid_iso_datetime(validated_at)
        ):
            findings.append(
                finding(
                    "action-readiness",
                    manifest_location,
                    "readiness.validatedAt must be null or an ISO datetime",
                )
            )
        if readiness_status == "untested":
            if validated_at is not None or validated_on:
                findings.append(
                    finding(
                        "action-readiness-drift",
                        manifest_location,
                        "untested readiness must not claim validatedAt or validatedOn metadata",
                    )
                )
            findings.append(
                finding(
                    "action-untested",
                    manifest_location,
                    "implementation is explicitly untested; static validation does not establish readiness",
                    "validation-needed",
                )
            )
        elif readiness_status in {"tests-passed", "validated"} and not evidence:
            findings.append(
                finding(
                    "action-readiness-drift",
                    manifest_location,
                    f"{readiness_status} readiness requires execution evidence",
                )
            )
        if readiness_status == "tests-passed" and (
            validated_at is not None or validated_on
        ):
            findings.append(
                finding(
                    "action-readiness-drift",
                    manifest_location,
                    "tests-passed readiness leaves validatedAt null and validatedOn empty",
                )
            )
        if readiness_status == "validated" and (not validated_at or not validated_on):
            findings.append(
                finding(
                    "action-readiness-drift",
                    manifest_location,
                    "validated readiness requires validatedAt and representative validatedOn evidence",
                )
            )

    lifecycle, lifecycle_missing, lifecycle_extras = mapping_shape(
        context,
        manifest.get("lifecycle"),
        required={"status", "reason", "replacement"},
    )
    lifecycle_status: str | None = None
    if lifecycle is None or lifecycle_missing or lifecycle_extras:
        findings.append(
            finding(
                "action-lifecycle",
                manifest_location,
                "lifecycle has an invalid shape; unsupported field names redacted",
            )
        )
    else:
        raw_status = lifecycle.get("status")
        lifecycle_status = raw_status if isinstance(raw_status, str) else None
        if lifecycle_status not in {"draft", "active", "deprecated"}:
            findings.append(
                finding(
                    "action-lifecycle",
                    manifest_location,
                    "lifecycle.status must be draft, active, or deprecated",
                )
            )
        for key in ("reason", "replacement"):
            lifecycle_value = lifecycle.get(key)
            if lifecycle_value is not None and not (
                isinstance(lifecycle_value, str) and lifecycle_value.strip()
            ):
                findings.append(
                    finding(
                        "action-lifecycle",
                        manifest_location,
                        f"lifecycle.{key} must be null or a non-empty string",
                    )
                )
        if lifecycle_status == "deprecated" and not lifecycle.get("reason"):
            findings.append(
                finding(
                    "action-lifecycle",
                    manifest_location,
                    "deprecated lifecycle requires a reason",
                )
            )
        if (
            lifecycle_status != "deprecated"
            and lifecycle.get("replacement") is not None
        ):
            findings.append(
                finding(
                    "action-lifecycle",
                    manifest_location,
                    "only a deprecated Action may name a replacement",
                )
            )
    declared_inputs: dict[str, str] = {}
    declared_path_values: dict[str, list[str]] = {}
    inputs = manifest.get("inputs")
    if not is_json_array(inputs):
        findings.append(
            finding("action-input", manifest_location, "inputs must be an array")
        )
    else:
        for index, value in enumerate(inputs):
            context.budget.charge_work()
            item, item_missing, item_extras = mapping_shape(
                context,
                value,
                required={"name", "type", "required", "description"},
                optional={"default", "examples"},
            )
            label = f"inputs[{index}]"
            if item is None or item_missing or item_extras:
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label} has an invalid shape; unsupported field names redacted",
                    )
                )
                continue
            name = item.get("name")
            input_type = item.get("type")
            if not isinstance(name, str) or not INPUT_NAME_RE.fullmatch(name):
                findings.append(
                    finding(
                        "action-input", manifest_location, f"{label}.name is invalid"
                    )
                )
                continue
            if name in declared_inputs:
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.name duplicates an earlier input; name redacted",
                    )
                )
            if input_type not in INPUT_TYPES:
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.type is invalid; value redacted",
                    )
                )
            else:
                declared_inputs[name] = str(input_type)
            if not isinstance(item.get("required"), bool):
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.required must be boolean",
                    )
                )
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.description must be non-empty",
                    )
                )
            if item.get("required") is True and "default" in item:
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label} cannot be required and declare a default",
                    )
                )
            examples = item.get("examples")
            if is_json_array(examples):
                context.budget.charge_work(len(examples))
            if examples is not None and (not is_json_array(examples) or not examples):
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.examples must be a non-empty array when present",
                    )
                )
            if "default" in item and not input_value_matches_type(
                context, item.get("default"), input_type
            ):
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.default does not match the declared input type; value redacted",
                    )
                )
            if is_json_array(examples) and any(
                not input_value_matches_type(context, example, input_type)
                for example in examples
            ):
                findings.append(
                    finding(
                        "action-input",
                        manifest_location,
                        f"{label}.examples contains a value that does not match the declared input type; value redacted",
                    )
                )
            if input_type in PATH_INPUT_TYPES:
                path_values: list[object] = []
                if "default" in item:
                    path_values.append(item.get("default"))
                if is_json_array(examples):
                    path_values.extend(examples)
                declared_path_values[name] = list(
                    dict.fromkeys(
                        path_value
                        for path_value in path_values
                        if isinstance(path_value, str)
                    )
                )
                for path_value in path_values:
                    context.budget.charge_work()
                    if not isinstance(path_value, str) or not (
                        path_value in (".", "./") or valid_scope(path_value)
                    ):
                        findings.append(
                            finding(
                                "action-input-path",
                                manifest_location,
                                f"{label} contains an unsafe path default or example; value redacted",
                            )
                        )
                    elif reason := forbidden_scope_reason(path_value):
                        findings.append(
                            finding(
                                "action-path-forbidden",
                                manifest_location,
                                f"{label} {reason}; value redacted",
                            )
                        )
            if re.search(
                r"(?:password|secret|token|credential|private[-_]?key)", name, re.I
            ):
                findings.append(
                    finding(
                        "action-capability-forbidden",
                        manifest_location,
                        "Action inputs must not solicit secrets or credentials; input name redacted",
                    )
                )

    outputs = manifest.get("outputs")
    output_names: set[str] = set()
    if not is_json_array(outputs):
        findings.append(
            finding("action-output", manifest_location, "outputs must be an array")
        )
    else:
        for index, value in enumerate(outputs):
            context.budget.charge_work()
            item, item_missing, item_extras = mapping_shape(
                context,
                value,
                required={"name", "type", "description"},
                optional={"path"},
            )
            label = f"outputs[{index}]"
            if item is None or item_missing or item_extras:
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label} has an invalid shape; unsupported field names redacted",
                    )
                )
                continue
            name = item.get("name")
            if not isinstance(name, str) or not INPUT_NAME_RE.fullmatch(name):
                findings.append(
                    finding(
                        "action-output", manifest_location, f"{label}.name is invalid"
                    )
                )
            elif name in output_names:
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.name duplicates an earlier output; name redacted",
                    )
                )
            else:
                output_names.add(name)
            if item.get("type") not in OUTPUT_TYPES:
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.type is invalid; value redacted",
                    )
                )
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.description must be non-empty",
                    )
                )
            output_path = item.get("path")
            if output_path is not None and (
                not isinstance(output_path, str)
                or not valid_relative_path(output_path)
                or forbidden_scope_reason(output_path)
                or reserved_scope_reason(output_path, "creates")
            ):
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.path is unsafe or too broad",
                    )
                )
            if output_path is not None and item.get("type") not in {"file", "files"}:
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.path is valid only for file or files outputs",
                    )
                )
            if (
                isinstance(output_path, str)
                and item.get("type") == "file"
                and output_path.replace("\\", "/").endswith("/")
            ):
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.path must name one file",
                    )
                )
            if (
                isinstance(output_path, str)
                and item.get("type") == "files"
                and not output_path.replace("\\", "/").endswith("/")
            ):
                findings.append(
                    finding(
                        "action-output",
                        manifest_location,
                        f"{label}.path must name a directory scope ending in /",
                    )
                )

    effects = manifest.get("effects")
    if not is_json_object(effects):
        findings.append(
            finding("action-effects", manifest_location, "effects must be an object")
        )
    else:
        forbidden = sorted(set(effects).intersection(FORBIDDEN_EFFECT_KEYS))
        if forbidden:
            findings.append(
                finding(
                    "action-capability-forbidden",
                    manifest_location,
                    f"forbidden effect fields are never allowed: {', '.join(forbidden)}",
                )
            )
        extras = sorted(set(effects) - set(EFFECT_KEYS))
        if extras:
            findings.append(
                finding(
                    "action-effects",
                    manifest_location,
                    f"effects contains {len(extras)} unsupported field(s); names redacted",
                )
            )
        for key in EFFECT_KEYS:
            context.budget.charge_work()
            values = effects.get(key)
            if not is_json_array(values):
                findings.append(
                    finding(
                        "action-effects",
                        manifest_location,
                        f"effects.{key} must be an array of scope objects",
                    )
                )
                continue
            serialized = [
                json_fingerprint(
                    {"path": normalize_relative_path(path_value)}
                    if is_json_object(value)
                    and isinstance(path_value := value.get("path"), str)
                    else value
                )
                for value in values
            ]
            context.budget.charge_work(len(values))
            if len(serialized) != len(set(serialized)):
                findings.append(
                    finding(
                        "action-effects",
                        manifest_location,
                        f"effects.{key} contains duplicates",
                    )
                )
            for index, scope in enumerate(values):
                context.budget.charge_work()
                label = f"effects.{key}[{index}]"
                if not is_json_object(scope) or len(scope) != 1:
                    findings.append(
                        finding(
                            "action-effect-scope",
                            manifest_location,
                            f"{label} must contain exactly one path or input",
                        )
                    )
                    continue
                if "path" in scope:
                    value = scope["path"]
                    if not isinstance(value, str) or not valid_scope(value):
                        findings.append(
                            finding(
                                "action-effect-scope",
                                manifest_location,
                                f"{label}.path is unsafe, broad, templated, or invalid",
                            )
                        )
                    elif not scope_stays_in_repository(context, value, target):
                        findings.append(
                            finding(
                                "action-effect-scope",
                                manifest_location,
                                f"{label}.path resolves outside the work folder",
                            )
                        )
                    elif reason := reserved_scope_reason(value, key):
                        findings.append(
                            finding(
                                "action-path-forbidden",
                                manifest_location,
                                f"{label}.path {reason}; value redacted",
                            )
                        )
                    elif reason := forbidden_scope_reason(value):
                        findings.append(
                            finding(
                                "action-path-forbidden",
                                manifest_location,
                                f"{label}.path {reason}; value redacted",
                            )
                        )
                elif "input" in scope:
                    value = scope["input"]
                    if (
                        not isinstance(value, str)
                        or declared_inputs.get(value) not in PATH_INPUT_TYPES
                    ):
                        findings.append(
                            finding(
                                "action-effect-scope",
                                manifest_location,
                                f"{label}.input must name a declared path, file, or directory input",
                            )
                        )
                    else:
                        for path_value in declared_path_values.get(value, []):
                            context.budget.charge_work()
                            if reason := reserved_scope_reason(
                                path_value, key, dynamic=True
                            ):
                                findings.append(
                                    finding(
                                        "action-path-forbidden",
                                        manifest_location,
                                        f"{label}.input example {reason}; value redacted",
                                    )
                                )
                else:
                    findings.append(
                        finding(
                            "action-effect-scope",
                            manifest_location,
                            f"{label} must contain path or input",
                        )
                    )

    execution, execution_missing, execution_extras = mapping_shape(
        context,
        manifest.get("execution"),
        required={"mode", "receipt", "timeoutMs", "maxOutputBytes"},
    )
    if execution is None or execution_missing or execution_extras:
        findings.append(
            finding(
                "action-execution",
                manifest_location,
                "execution has an invalid shape; unsupported field names redacted",
            )
        )
    else:
        mode = execution.get("mode")
        if mode not in {"read-only", "plan-apply"}:
            findings.append(
                finding(
                    "action-execution",
                    manifest_location,
                    "execution.mode must be read-only or plan-apply",
                )
            )
        if execution.get("receipt") != "json-v1":
            findings.append(
                finding(
                    "action-execution",
                    manifest_location,
                    "execution.receipt must be json-v1",
                )
            )
        timeout = execution.get("timeoutMs")
        if not is_integral_number(timeout) or not 100 <= timeout <= 300_000:
            findings.append(
                finding(
                    "action-execution",
                    manifest_location,
                    "execution.timeoutMs must be an integer from 100 through 300000",
                )
            )
        output_limit = execution.get("maxOutputBytes")
        if (
            not is_integral_number(output_limit)
            or not 1_024 <= output_limit <= 4_194_304
        ):
            findings.append(
                finding(
                    "action-execution",
                    manifest_location,
                    "execution.maxOutputBytes must be an integer from 1024 through 4194304",
                )
            )
        creates = effects.get("creates", []) if is_json_object(effects) else []
        updates = effects.get("updates", []) if is_json_object(effects) else []
        temporary = effects.get("temporary", []) if is_json_object(effects) else []
        if mode == "read-only" and (creates or updates or temporary):
            findings.append(
                finding(
                    "action-execution-effects",
                    manifest_location,
                    "read-only execution cannot create, update, or use temporary files",
                )
            )
        if mode == "plan-apply" and not (creates or updates):
            findings.append(
                finding(
                    "action-execution-effects",
                    manifest_location,
                    "plan-apply execution must declare a create or update scope",
                )
            )
        if mode == "plan-apply" and (
            not is_json_array(outputs)
            or not outputs
            or any(
                not is_json_object(output)
                or output.get("type") not in {"file", "files"}
                for output in outputs
            )
        ):
            findings.append(
                finding(
                    "action-execution-output",
                    manifest_location,
                    "plan-apply execution requires at least one file/files output and no non-file outputs",
                )
            )
        if temporary:
            findings.append(
                finding(
                    "action-temporary-forbidden",
                    manifest_location,
                    "effects.temporary is reserved for trusted runner state and must be empty",
                )
            )

    success, success_missing, success_extras = mapping_shape(
        context, manifest.get("success"), required={"postconditions"}
    )
    if (
        success is None
        or success_missing
        or success_extras
        or not nonempty_string_list(
            context, success.get("postconditions") if success else None
        )
    ):
        findings.append(
            finding(
                "action-success",
                manifest_location,
                "success must contain a non-empty postconditions array and no unsupported fields",
            )
        )

    dependencies = manifest.get("dependencies")
    dependency_names: set[str] = set()
    if not is_json_array(dependencies):
        findings.append(
            finding(
                "action-dependency", manifest_location, "dependencies must be an array"
            )
        )
    else:
        for index, value in enumerate(dependencies):
            context.budget.charge_work()
            item, item_missing, item_extras = mapping_shape(
                context, value, required={"name", "version"}
            )
            label = f"dependencies[{index}]"
            if item is None or item_missing or item_extras:
                findings.append(
                    finding(
                        "action-dependency",
                        manifest_location,
                        f"{label} has an invalid shape; unsupported field names redacted",
                    )
                )
                continue
            name = item.get("name")
            version_value = item.get("version")
            if not isinstance(name, str) or not PACKAGE_NAME_RE.fullmatch(name):
                findings.append(
                    finding(
                        "action-dependency",
                        manifest_location,
                        f"{label}.name is invalid",
                    )
                )
            elif name in dependency_names:
                findings.append(
                    finding(
                        "action-dependency",
                        manifest_location,
                        f"{label}.name duplicates an earlier dependency; name redacted",
                    )
                )
            else:
                dependency_names.add(name)
            if not isinstance(version_value, str) or not EXACT_VERSION_RE.fullmatch(
                version_value
            ):
                findings.append(
                    finding(
                        "action-dependency",
                        manifest_location,
                        f"{label}.version must be exact",
                    )
                )

    for filename, code in (
        ("run.mjs", "action-entrypoint"),
        ("run.test.mjs", "action-test"),
    ):
        check_regular_file(
            context, action_dir / filename, target, findings, code, filename
        )
    digests, digest_missing, digest_extras = mapping_shape(
        context, manifest.get("digests"), required={"entrypoint", "test"}
    )
    if digests is None or digest_missing or digest_extras:
        findings.append(
            finding(
                "action-digest",
                manifest_location,
                "digests has an invalid shape; unsupported field names redacted",
            )
        )
    else:
        for field, filename in (("entrypoint", "run.mjs"), ("test", "run.test.mjs")):
            expected_digest = digests.get(field)
            if not isinstance(expected_digest, str) or not DIGEST_RE.fullmatch(
                expected_digest
            ):
                findings.append(
                    finding(
                        "action-digest",
                        manifest_location,
                        f"digests.{field} must be sha256:<64 lowercase hex>",
                    )
                )
                continue
            artifact = action_dir / filename
            if context.root.is_file(artifact) and not context.root.is_symlink(artifact):
                try:
                    actual_digest = (
                        "sha256:"
                        + hashlib.sha256(read_bytes_bounded(artifact)).hexdigest()
                    )
                except OSError as exc:
                    findings.append(
                        finding(
                            "action-digest",
                            relative(artifact, target),
                            f"could not hash {filename}: {safe_os_error(exc)}",
                        )
                    )
                    continue
                if actual_digest != expected_digest:
                    findings.append(
                        finding(
                            "action-digest-drift",
                            relative(artifact, target),
                            f"{filename} no longer matches manifest digests.{field}",
                        )
                    )
    new_findings = findings[validation_start:]
    if any(item.code != "action-untested" for item in new_findings):
        return None
    return ActionManifest.from_validated_json(manifest)

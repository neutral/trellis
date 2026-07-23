"""Focused action docs validators for Trellis Audit."""

from __future__ import annotations

import math
import re
import shlex

from ..context import WORK_UNIT_BYTES, AuditContext
from ..diagnostics import Finding, finding
from ..filesystem import RepoPath, read_text, relative
from ..models import (
    ActionManifest,
    ActionPage,
    immutable_sections,
    is_json_array,
    is_json_object,
)
from .core import (
    ACTION_HEADINGS,
    CAPTURE_MARKER_RE,
    HEADING_RE,
)
from .manifest import normalize_relative_path
from .markdown import markdown_structure_view


def parse_headings(
    context: AuditContext, content: str, structure: str
) -> tuple[dict[str, int], list[str], dict[str, str]]:
    """Count headings and build level-two sections in one bounded pass."""
    counts: dict[str, int] = {}
    titles: list[str] = []
    sections: dict[str, str] = {}
    active_section: str | None = None
    active_start = 0
    for match in HEADING_RE.finditer(structure):
        context.budget.charge_work()
        if active_section is not None:
            sections[active_section] = content[active_start : match.start()].strip()
            active_section = None
        heading = match.group(1).strip()
        if match.group(0).startswith("# "):
            titles.append(heading)
        elif match.group(0).startswith("## "):
            counts[heading] = counts.get(heading, 0) + 1
            active_section = heading
            active_start = match.end()
    if active_section is not None:
        sections[active_section] = content[active_start:].strip()
    return counts, titles, sections


def match_state(content: str, label: str, choices: str) -> str | None:
    match = re.search(
        rf"^{re.escape(label)}:\s*({choices})\b",
        content,
        re.MULTILINE | re.I,
    )
    return match.group(1).lower() if match else None


def action_command_path(action_id: str) -> str:
    return " ".join(action_id.split("/"))


def check_action_page(
    context: AuditContext,
    path: RepoPath,
    action_id: str,
    target: RepoPath,
    findings: list[Finding],
) -> ActionPage | None:
    content = read_text(path, target, findings)
    if content is None:
        return None
    structure = markdown_structure_view(context, content)
    markers: list[tuple[str, str]] = []
    for marker in CAPTURE_MARKER_RE.finditer(structure):
        context.budget.charge_work()
        markers.append((marker.group(1), marker.group(2)))
    if markers != [("action", "2")]:
        return None
    heading_counts, titles, sections = parse_headings(context, content, structure)
    if len(titles) != 1:
        findings.append(
            finding(
                "action-page-title",
                relative(path, target),
                f"Action page must contain exactly one level-one title; found {len(titles)}",
            )
        )
    for heading in ACTION_HEADINGS:
        count = heading_counts.get(heading, 0)
        if count != 1:
            findings.append(
                finding(
                    "action-page-heading",
                    relative(path, target),
                    f"Action page must contain one {heading} heading; found {count}",
                )
            )
    test_command = f"./trellis test {action_command_path(action_id)}"
    test_matches = matching_tool_commands(
        context, tool_commands(context, content), "test", action_id
    )
    exact_test_matches = [
        match
        for match in test_matches
        if len(match[2]) == action_command_prefix_length(action_id, "test")
    ]
    if not exact_test_matches:
        findings.append(
            finding(
                "action-test-missing",
                relative(path, target),
                f"action page must document {test_command}",
            )
        )
    elif len(exact_test_matches) != 1 or len(test_matches) != 1:
        findings.append(
            finding(
                "action-test-mismatch",
                relative(path, target),
                f"action page must contain one exact {test_command} command",
            )
        )
    method_confidence = match_state(
        content, "Method confidence", "Provisional|Established"
    )
    readiness = match_state(
        content,
        "Implementation readiness",
        "Untested|Tests passed|Validated(?: on representative data)?",
    )
    lifecycle = match_state(content, "Lifecycle", "Draft|Active|Deprecated")
    for label, value in (
        ("Method confidence", method_confidence),
        ("Implementation readiness", readiness),
        ("Lifecycle", lifecycle),
    ):
        if value is None:
            findings.append(
                finding(
                    "action-page-state",
                    relative(path, target),
                    f"Action format 2 page is missing a valid {label} line",
                )
            )
    for label, value, choices in (
        ("Method confidence", method_confidence, "Provisional|Established"),
        (
            "Implementation readiness",
            readiness,
            "Untested|Tests passed|Validated(?: on representative data)?",
        ),
    ):
        if value is None:
            continue
        if label == "Implementation readiness" and value == "untested":
            continue
        line = re.search(
            rf"^{re.escape(label)}:\s*(?:{choices})\b(.*)$",
            content,
            re.MULTILINE | re.I,
        )
        remainder = line.group(1) if line else ""
        if not re.search(r"[A-Za-z0-9]", remainder):
            findings.append(
                finding(
                    "action-page-state-evidence",
                    relative(path, target),
                    f"{label} line must include its evidence basis",
                )
            )
    return ActionPage(
        path=path,
        title=titles[0] if titles else None,
        method_confidence=method_confidence,
        readiness=readiness,
        lifecycle=lifecycle,
        sections=immutable_sections(sections.items()),
        content=content,
    )


def normalized_prose(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def charge_text_comparison(context: AuditContext, *values: str) -> None:
    context.budget.charge_work(
        max(
            1,
            sum(
                math.ceil(len(value.encode("utf-8")) / WORK_UNIT_BYTES)
                for value in values
            ),
        )
    )


def section_mentions(section: str, value: str) -> bool:
    return normalized_prose(value) in normalized_prose(section)


def contract_terms(value: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "within",
    }
    result: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", value.casefold()):
        if token in stopwords:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                token = token[: -len(suffix)]
                break
        result.add(token)
    return result


def materially_mentions(section: str, value: str) -> bool:
    expected = contract_terms(value)
    if not expected:
        return True
    actual = contract_terms(section)
    required = max(1, (len(expected) + 1) // 2)
    return len(expected.intersection(actual)) >= required


def tool_commands(context: AuditContext, section: str) -> list[str]:
    context.budget.charge_work(
        max(1, math.ceil(len(section.encode("utf-8")) / WORK_UNIT_BYTES))
    )
    commands: list[str] = []
    fenced_ranges: list[tuple[int, int]] = []
    for fence in re.finditer(r"```[^\n]*\n(.*?)```", section, re.DOTALL):
        fenced_ranges.append(fence.span())
        for line in fence.group(1).splitlines():
            candidate = line.strip()
            if candidate.startswith("./trellis "):
                commands.append(candidate)
    fenced_index = 0
    for match in re.finditer(r"(?<!`)`([^`\n]+)`(?!`)", section):
        while (
            fenced_index < len(fenced_ranges)
            and fenced_ranges[fenced_index][1] <= match.start()
        ):
            fenced_index += 1
        if (
            fenced_index < len(fenced_ranges)
            and fenced_ranges[fenced_index][0] <= match.start()
        ):
            continue
        candidate = match.group(1).strip()
        if candidate.startswith("./trellis "):
            commands.append(candidate)
    return commands


def tool_command_tokens(command: str) -> list[str] | None:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    return tokens if tokens[:1] == ["./trellis"] else None


def matching_tool_commands(
    context: AuditContext, commands: list[str], verb: str | None, action_id: str
) -> list[tuple[int, str, list[str]]]:
    prefix = ["./trellis"]
    if verb is not None:
        prefix.append(verb)
    prefix.extend(action_id.split("/"))
    matches: list[tuple[int, str, list[str]]] = []
    for index, command in enumerate(commands):
        context.budget.charge_work()
        charge_text_comparison(context, command)
        tokens = tool_command_tokens(command)
        if tokens is not None and tokens[: len(prefix)] == prefix:
            matches.append((index, command, tokens))
    return matches


def action_command_prefix_length(action_id: str, verb: str | None) -> int:
    return 1 + (1 if verb is not None else 0) + len(action_id.split("/"))


def primary_command_issue(
    tokens: list[str], *, action_id: str, verb: str | None, has_inputs: bool
) -> str | None:
    tail = tokens[action_command_prefix_length(action_id, verb) :]
    separator_count = tail.count("--")
    if separator_count > 1:
        return "command contains more than one input separator"
    if separator_count:
        separator = tail.index("--")
        runner_options = tail[:separator]
        input_tokens = tail[separator + 1 :]
    else:
        runner_options = tail
        input_tokens = []
    if runner_options not in ([], ["--json"]):
        return "command contains unsupported runner options before the input separator"
    if has_inputs and not separator_count:
        return "command must place typed named inputs after a literal -- separator"
    if has_inputs and not input_tokens:
        return "command input separator is not followed by named inputs"
    if not has_inputs and separator_count:
        return "command has an unnecessary caller-input separator"
    if any(token in {"&&", "||", ";", "|"} for token in input_tokens):
        return "command must contain only named Action inputs"
    return None


def reviewed_plan_command(
    tokens: list[str], verb: str, action_id: str
) -> tuple[str | None, str | None]:
    tail = tokens[action_command_prefix_length(action_id, verb) :]
    plan: str | None = None
    json_seen = False
    index = 0
    while index < len(tail):
        token = tail[index]
        if token == "--plan":
            if plan is not None or index + 1 >= len(tail):
                return None, f"{verb} command must contain one --plan identifier"
            plan = tail[index + 1]
            index += 2
            continue
        if token == "--json" and not json_seen:
            json_seen = True
            index += 1
            continue
        if token == "--":
            return None, f"{verb} command must not contain caller inputs"
        return (
            None,
            f"{verb} command contains an unsupported runner option; value redacted",
        )
    if plan is None:
        return None, f"{verb} command must contain --plan <plan-id>"
    if not re.fullmatch(
        r"(?:<plan-id>|<sha256>|sha256:[0-9a-f]{64}|[0-9a-f]{64})", plan
    ):
        return None, f"{verb} command plan identifier is not a SHA-256 plan reference"
    return plan, None


def documented_input_issues(
    context: AuditContext, tokens: list[str], input_types: dict[str, str]
) -> list[str]:
    if "--" not in tokens:
        return []
    tail = tokens[tokens.index("--") + 1 :]
    issues: list[str] = []
    seen: set[str] = set()
    index = 0
    while index < len(tail):
        context.budget.charge_work()
        token = tail[index]
        if not token.startswith("--") or token == "--":
            issues.append("caller input must be named; value redacted")
            index += 1
            continue
        raw = token[2:]
        name, separator, inline_value = raw.partition("=")
        input_type = input_types.get(name)
        if input_type is None:
            issues.append("command documents an undeclared input; name redacted")
        elif name in seen and input_type != "string-list":
            issues.append(
                "command supplies a non-list input more than once; name redacted"
            )
        seen.add(name)
        if separator:
            if inline_value == "":
                issues.append(
                    "command gives a named input an empty inline value; name redacted"
                )
            index += 1
            continue
        if input_type == "boolean" and (
            index + 1 == len(tail) or tail[index + 1].startswith("--")
        ):
            index += 1
            continue
        if index + 1 >= len(tail) or tail[index + 1].startswith("--"):
            issues.append("command does not give a named input a value; name redacted")
            index += 1
            continue
        index += 2
    return issues


def check_action_page_agreement(
    context: AuditContext,
    action_id: str,
    page: ActionPage,
    manifest: ActionManifest,
    target: RepoPath,
    findings: list[Finding],
) -> None:
    location = relative(page.path, target)
    title = manifest.get("title")
    if (
        isinstance(title, str)
        and page.title is not None
        and normalized_prose(title) != normalized_prose(page.title)
    ):
        findings.append(
            finding(
                "action-title-mismatch",
                location,
                "page title does not match manifest title; both values redacted",
            )
        )

    method = manifest.get("methodConfidence")
    if is_json_object(method):
        status = method.get("status")
        if isinstance(status, str) and page.method_confidence != status:
            findings.append(
                finding(
                    "action-state-mismatch",
                    location,
                    "page Method confidence does not match manifest state",
                )
            )
        review_text = "\n".join(
            page.sections.get(name, "") for name in ("Use When", "Success And Failure")
        )
        review_triggers = method.get("reviewTriggers")
        for trigger in review_triggers if is_json_array(review_triggers) else []:
            context.budget.charge_work()
            if isinstance(trigger, str):
                charge_text_comparison(context, review_text, trigger)
            if isinstance(trigger, str) and not section_mentions(review_text, trigger):
                findings.append(
                    finding(
                        "action-review-trigger-mismatch",
                        location,
                        "page does not disclose a manifest review trigger; trigger text redacted",
                    )
                )

    readiness = manifest.get("readiness")
    if is_json_object(readiness) and isinstance(readiness.get("status"), str):
        page_readiness = page.readiness
        if page_readiness and page_readiness.startswith("validated"):
            page_readiness = "validated"
        elif page_readiness == "tests passed":
            page_readiness = "tests-passed"
        if page_readiness != readiness["status"]:
            findings.append(
                finding(
                    "action-state-mismatch",
                    location,
                    "page Implementation readiness does not match manifest state",
                )
            )

    lifecycle = manifest.get("lifecycle")
    if is_json_object(lifecycle) and isinstance(lifecycle.get("status"), str):
        if page.lifecycle != lifecycle["status"]:
            findings.append(
                finding(
                    "action-state-mismatch",
                    location,
                    "page Lifecycle does not match manifest state",
                )
            )
        for field in ("reason", "replacement"):
            value = lifecycle.get(field)
            if (
                isinstance(value, str)
                and value.strip()
                and not section_mentions(page.content, value)
            ):
                findings.append(
                    finding(
                        "action-lifecycle-mismatch",
                        location,
                        f"page does not disclose lifecycle {field}; value redacted",
                    )
                )

    inputs_text = page.sections.get("Inputs", "")
    run_text = page.sections.get("Run", "")
    inputs = manifest.get("inputs")
    page_commands = tool_commands(context, run_text)
    execution_for_inputs = manifest.get("execution")
    mode_for_inputs = (
        execution_for_inputs.get("mode")
        if is_json_object(execution_for_inputs)
        else None
    )
    input_matches = matching_tool_commands(context, page_commands, None, action_id)
    if mode_for_inputs == "plan-apply":
        input_matches += matching_tool_commands(
            context, page_commands, "plan", action_id
        )
    input_commands = [command for _, command, _ in input_matches]
    if is_json_array(inputs):
        for item in inputs:
            context.budget.charge_work()
            if not is_json_object(item):
                continue
            name = item.get("name")
            if not isinstance(name, str):
                continue
            charge_text_comparison(context, inputs_text, name)
            if not re.search(
                rf"(?<![A-Za-z0-9-]){re.escape(name)}(?![A-Za-z0-9-])", inputs_text
            ):
                findings.append(
                    finding(
                        "action-input-mismatch",
                        location,
                        "Inputs section does not name a manifest input; name redacted",
                    )
                )
            context.budget.charge_work(len(input_commands))
            if input_commands:
                charge_text_comparison(context, *input_commands)
            maps_input = any(
                (tokens := tool_command_tokens(command)) is not None
                and "--" in tokens
                and any(
                    token == f"--{name}" or token.startswith(f"--{name}=")
                    for token in tokens[tokens.index("--") + 1 :]
                )
                for command in input_commands
            )
            if not maps_input:
                findings.append(
                    finding(
                        "action-run-input-mismatch",
                        location,
                        "Run section does not map a manifest input after --; name redacted",
                    )
                )

    outputs_text = page.sections.get("Outputs", "")
    charge_text_comparison(context, outputs_text)
    output_contract_terms = contract_terms(outputs_text)
    outputs = manifest.get("outputs")
    if is_json_array(outputs):
        for item in outputs:
            context.budget.charge_work()
            if not is_json_object(item):
                continue
            name = item.get("name")
            if not isinstance(name, str):
                continue
            charge_text_comparison(context, name)
            if not contract_terms(name).issubset(output_contract_terms):
                findings.append(
                    finding(
                        "action-output-mismatch",
                        location,
                        "Outputs section does not name a manifest output; name redacted",
                    )
                )
            path = item.get("path")
            if isinstance(path, str):
                charge_text_comparison(context, outputs_text, path)
            if isinstance(path, str) and path not in outputs_text:
                findings.append(
                    finding(
                        "action-output-mismatch",
                        location,
                        "Outputs section does not disclose a manifest path; value redacted",
                    )
                )

    effects_text = page.sections.get("Effects", "")
    charge_text_comparison(context, effects_text)
    effects_contract_terms = contract_terms(effects_text)
    effects = manifest.get("effects")
    input_descriptions: dict[str, str] = {}
    input_description_terms: dict[str, set[str]] = {}
    if is_json_array(inputs):
        for item in inputs:
            context.budget.charge_work()
            if not is_json_object(item):
                continue
            name = item.get("name")
            description = item.get("description")
            if isinstance(name, str):
                input_descriptions[name] = (
                    description if isinstance(description, str) else ""
                )
                if isinstance(description, str):
                    charge_text_comparison(context, description)
                    input_description_terms[name] = contract_terms(description)
    if is_json_object(effects):
        effect_patterns = {
            "reads": r"\bread(?:s|ing)?\b",
            "creates": r"\bcreat(?:e|es|ed|ing)\b",
            "updates": r"\bupdat(?:e|es|ed|ing)\b",
            "temporary": r"\btemporary\b",
        }
        for key, pattern in effect_patterns.items():
            charge_text_comparison(context, effects_text)
            if not re.search(pattern, effects_text, re.I):
                findings.append(
                    finding(
                        "action-effects-mismatch",
                        location,
                        f"Effects section does not explicitly address {key}",
                    )
                )
            values = effects.get(key)
            if not is_json_array(values):
                continue
            for scope in values:
                context.budget.charge_work()
                if not is_json_object(scope):
                    continue
                value = scope.get("path")
                if isinstance(value, str):
                    normalized_value = normalize_relative_path(value)
                    charge_text_comparison(
                        context,
                        effects_text,
                        effects_text,
                        value,
                        normalized_value,
                    )
                else:
                    normalized_value = ""
                if (
                    isinstance(value, str)
                    and value not in effects_text
                    and normalized_value not in effects_text
                ):
                    findings.append(
                        finding(
                            "action-effects-mismatch",
                            location,
                            f"Effects section does not disclose a {key} scope; value redacted",
                        )
                    )
                input_name = scope.get("input")
                if isinstance(input_name, str):
                    charge_text_comparison(context, effects_text, input_name)
                names_input = isinstance(input_name, str) and re.search(
                    rf"(?<![A-Za-z0-9-]){re.escape(input_name)}(?![A-Za-z0-9-])",
                    effects_text,
                )
                describes_input = (
                    isinstance(input_name, str)
                    and input_name in input_descriptions
                    and len(
                        effects_contract_terms.intersection(
                            input_description_terms.get(input_name, set())
                        )
                    )
                    >= 2
                )
                if isinstance(input_name, str) and not (names_input or describes_input):
                    findings.append(
                        finding(
                            "action-effects-mismatch",
                            location,
                            f"Effects section does not disclose a {key} input scope; name redacted",
                        )
                    )

    execution = manifest.get("execution")
    if is_json_object(execution):
        mode = execution.get("mode")
        commands = tool_commands(context, run_text)
        malformed_commands = [
            command for command in commands if tool_command_tokens(command) is None
        ]
        if malformed_commands:
            findings.append(
                finding(
                    "action-run-mismatch",
                    location,
                    "Run section contains a command that cannot be parsed safely",
                )
            )
        if any(
            re.search(
                r"--(?:network|environment|process|allow-network|allow-env|allow-process)",
                command,
            )
            for command in commands
        ):
            findings.append(
                finding(
                    "action-run-mismatch",
                    location,
                    "Run section contains a forbidden capability flag",
                )
            )
        has_inputs = is_json_array(inputs) and bool(inputs)
        declared_input_types: dict[str, str] = {}
        if is_json_array(inputs):
            for item in inputs:
                if not is_json_object(item):
                    continue
                name = item.get("name")
                input_type = item.get("type")
                if isinstance(name, str):
                    declared_input_types[name] = (
                        input_type if isinstance(input_type, str) else ""
                    )
        if mode == "read-only":
            run_commands = matching_tool_commands(context, commands, None, action_id)
            if not run_commands:
                findings.append(
                    finding(
                        "action-run-missing",
                        location,
                        "read-only page must document direct "
                        f"./trellis {action_command_path(action_id)}",
                    )
                )
            elif len(run_commands) > 1:
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "read-only page must contain one canonical run command",
                    )
                )
            for _, _, tokens in run_commands:
                if issue := primary_command_issue(
                    tokens,
                    action_id=action_id,
                    verb=None,
                    has_inputs=has_inputs,
                ):
                    findings.append(finding("action-run-mismatch", location, issue))
                for issue in documented_input_issues(
                    context, tokens, declared_input_types
                ):
                    findings.append(
                        finding("action-run-input-mismatch", location, issue)
                    )
            conflicting = [
                entry
                for verb in ("run", "plan", "show-plan", "apply")
                for entry in matching_tool_commands(context, commands, verb, action_id)
            ]
            if conflicting:
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "read-only page must use direct invocation, not run/plan/show-plan/apply",
                    )
                )
        elif mode == "plan-apply":
            direct_plan_commands = matching_tool_commands(
                context, commands, None, action_id
            )
            explicit_plan_commands = matching_tool_commands(
                context, commands, "plan", action_id
            )
            plan_commands = direct_plan_commands + explicit_plan_commands
            review_commands = matching_tool_commands(
                context, commands, "show-plan", action_id
            )
            apply_commands = matching_tool_commands(
                context, commands, "apply", action_id
            )
            if not plan_commands:
                findings.append(
                    finding(
                        "action-run-missing",
                        location,
                        "write-capable page must document direct planning with "
                        f"./trellis {action_command_path(action_id)} or its explicit plan form",
                    )
                )
            if not review_commands:
                findings.append(
                    finding(
                        "action-run-missing",
                        location,
                        f"write-capable page must document ./trellis show-plan {action_command_path(action_id)} --plan <plan-id>",
                    )
                )
            if not apply_commands:
                findings.append(
                    finding(
                        "action-run-missing",
                        location,
                        f"write-capable page must document ./trellis apply {action_command_path(action_id)} --plan <plan-id>",
                    )
                )
            if (
                any(
                    matching_tool_commands(context, commands, verb, action_id)
                    for verb in ("run",)
                )
                or "--apply" in run_text
            ):
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "plan-apply page must not use forbidden direct --apply behavior",
                    )
                )
            if any(
                len(entries) > 1
                for entries in (plan_commands, review_commands, apply_commands)
            ):
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "Run section must contain one plan, one show-plan review, and one apply command",
                    )
                )
            for _, _, tokens in plan_commands:
                verb = "plan" if tokens[1:2] == ["plan"] else None
                if issue := primary_command_issue(
                    tokens,
                    action_id=action_id,
                    verb=verb,
                    has_inputs=has_inputs,
                ):
                    findings.append(finding("action-run-mismatch", location, issue))
                for issue in documented_input_issues(
                    context, tokens, declared_input_types
                ):
                    findings.append(
                        finding("action-run-input-mismatch", location, issue)
                    )
            review_ids: list[str] = []
            apply_ids: list[str] = []
            for _, _, tokens in review_commands:
                plan_id, issue = reviewed_plan_command(tokens, "show-plan", action_id)
                if issue:
                    findings.append(finding("action-run-mismatch", location, issue))
                elif plan_id is not None:
                    review_ids.append(plan_id)
            for _, _, tokens in apply_commands:
                plan_id, issue = reviewed_plan_command(tokens, "apply", action_id)
                if issue:
                    findings.append(finding("action-run-mismatch", location, issue))
                elif plan_id is not None:
                    apply_ids.append(plan_id)
            if len(review_ids) == len(apply_ids) == 1 and review_ids != apply_ids:
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "show-plan and apply must use the same reviewed plan identifier",
                    )
                )
            if len(plan_commands) == len(review_commands) == len(
                apply_commands
            ) == 1 and not (
                plan_commands[0][0] < review_commands[0][0] < apply_commands[0][0]
            ):
                findings.append(
                    finding(
                        "action-run-mismatch",
                        location,
                        "Run section must order plan, show-plan review, then apply",
                    )
                )

    verification_text = page.sections.get("Verification", "")
    test_command = f"./trellis test {action_command_path(action_id)}"
    test_matches = matching_tool_commands(
        context,
        tool_commands(context, verification_text),
        "test",
        action_id,
    )
    exact_test_matches = [
        match
        for match in test_matches
        if len(match[2]) == action_command_prefix_length(action_id, "test")
    ]
    if not exact_test_matches:
        findings.append(
            finding(
                "action-test-missing",
                location,
                f"Verification section must document {test_command}",
            )
        )
    elif len(exact_test_matches) != 1 or len(test_matches) != 1:
        findings.append(
            finding(
                "action-test-mismatch",
                location,
                f"Verification section must contain one exact {test_command} command",
            )
        )
    if not re.search(r"\breceipt\b", verification_text, re.I):
        findings.append(
            finding(
                "action-verification-mismatch",
                location,
                "Verification section must describe receipt evidence",
            )
        )
    success = manifest.get("success")
    success_text = "\n".join(
        page.sections.get(name, "")
        for name in ("Outputs", "Success And Failure", "Verification")
    )
    postconditions = success.get("postconditions") if is_json_object(success) else None
    if is_json_array(postconditions):
        for postcondition in postconditions:
            context.budget.charge_work()
            if isinstance(postcondition, str):
                charge_text_comparison(context, success_text, postcondition)
            if isinstance(postcondition, str) and not materially_mentions(
                success_text, postcondition
            ):
                findings.append(
                    finding(
                        "action-success-mismatch",
                        location,
                        "page does not disclose a manifest postcondition; text redacted",
                    )
                )

    purpose = page.sections.get("Purpose", "")
    outward_title = " ".join(value for value in (page.title or "", purpose) if value)
    if re.search(
        r"\b(?:approve|decide|delete|deploy|grant|notify|publish|reject|remove|revoke|send|upload)\b",
        outward_title,
        re.I,
    ):
        findings.append(
            finding(
                "action-responsibility-forbidden",
                location,
                "Action purpose appears to include outward, destructive, permission, or consequential judgment work",
            )
        )
    if (
        re.search(r"\band\b", page.title or "", re.I)
        and is_json_array(outputs)
        and len(outputs) > 1
    ):
        findings.append(
            finding(
                "action-kitchen-sink",
                location,
                "multiple titled responsibilities and outputs need a one-intent boundary review",
                "validation-needed",
            )
        )

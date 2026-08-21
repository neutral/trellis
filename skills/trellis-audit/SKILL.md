---
name: trellis-audit
description: Review a Trellis Playbooks collection when the user asks for an audit or invokes /trellis-audit. Inspect setup, Playbooks, supporting tools, and explicitly scoped project scripts; report evidence-backed improvements without changing, executing, pruning, or blocking owner-controlled scaffolding.
---

# Trellis Audit

Help the user make a Playbooks collection smaller, clearer, safer, and more useful. Audit produces
evidence and recommendations; it does not certify, execute, repair, or control the collection.

## Scope and authority

1. Use the exact work folder and Playbooks folder the user names. Otherwise use a marked
   `playbooks/` folder in the host-designated current work folder.
2. Do not widen scope to an enclosing Git repository or recursively search the entire project for
   possible collections.
3. Treat the Playbooks folder as owner space. Trellis manages only its root marker, managed index,
   marked `PLAYBOOK.md` files, and internal `_cli` files it created.
4. Ignore unmarked owner material unless the user asks for it or a marked Playbook explicitly
   references it.
5. Stay local, static, read-only, and report-only. Do not execute Playbooks, tools, tests, or
   scripts; invoke package managers; install dependencies; browse; or change files.
6. Do not reproduce secret or personal values encountered during review.

Audit never blocks the user from organizing the collection, adding custom files, or creating
standalone scripts. It can recommend clearer boundaries, disclosure, verification, or recovery,
but project ownership remains with the user.

## Select audit depth

Honor a narrower user request. Otherwise audit in four passes:

1. **Collection:** marker, managed index, links, path identity, and duplicate IDs.
2. **Playbook:** trigger, outcome, method, boundaries, supporting tools, and verification.
3. **Portfolio:** overlap, conflict, fragmentation, discoverability, and inconsistent scope.
4. **Maintenance:** concrete evidence of drift, supersession, breakage, or unverified assumptions.

Inventory marked Playbooks before semantic review. Report total coverage and every omission. Do
not silently sample a large collection; propose bounded batches instead.

## Pass 1 — Collection

Check that:

- the selected README has exactly one `<!-- trellis-playbooks-root: format=1 -->` marker;
- it has one well-formed managed index block;
- each indexed entry resolves to a marked `<playbook-id>/PLAYBOOK.md`;
- each marked Playbook is indexed once unless the user intentionally excludes it;
- IDs use portable lowercase kebab case and do not collide by case or Unicode normalization;
- links resolve with exact path case; and
- Trellis-managed paths do not traverse symlinks or escape the selected work folder.

A structural result is only the beginning of the audit. It does not prove that a Playbook is
useful or correct.

## Pass 2 — Playbook quality

For every marked Playbook, assess:

- **Use When:** the trigger, scope, prerequisites, and important non-use cases are recognizable;
- **Outcome:** one promised result and an observable done condition are clear;
- **Inputs And Context:** required materials, variable details, provenance, and authority are
  visible;
- **Method:** phases are ordered and decision cues appear where they change the next action;
- **Supporting Tools:** every referenced host tool, internal tool, or project-owned script has an
  understandable role and invocation boundary;
- **Boundaries:** exclusions, stop and escalation conditions, permissions, interruption, recovery,
  and review triggers are explicit where material; and
- **Verification:** completion relies on evidence rather than merely finishing the steps.

Check transfer quality: incidental names, paths, dates, and values should not be hard-coded unless
their exact identity is part of the trigger. A competent future agent should not need the original
conversation to use the Playbook.

Use one sizing rule: a Playbook owns one recognizable situation through one verified outcome.
Recommend a split only at a real trigger, outcome, authority, verification, recovery, stewardship,
or change-cadence boundary. Recommend a merge only when the parts cannot safely or usefully stand
alone.

## Pass 3 — Portfolio

Compare titles, triggers, outcomes, methods, and verification. Look for:

- duplicate or conflicting Playbooks;
- kitchen-sink Playbooks with independent jobs;
- fragments that are incomplete unless always used together;
- copied mechanics or policy that should be shared or linked;
- vague titles and missing index summaries;
- active guidance presented beside a replacement without a clear distinction; and
- a Playbook whose tool or script has become the real undocumented contract.

Do not invent missing Playbooks from general project content. Discover recommends candidates from
selected sessions; Capture creates an explicit Playbook.

## Pass 4 — Supporting tools and maintenance

### Internal `_cli` tools

Review only internal tools referenced by a marked Playbook and stored at:

```text
<playbooks-root>/_cli/tools/<playbook-id>/<tool-id>/tool.json
```

Check that the declaration belongs to the referencing Playbook, uses format 1, has no unknown
fields, and selects one supported operation: `file.hash`, `files.compare`, `text.replace`, or
`json.set`. Tool folders should contain only `tool.json`.

Confirm that the Playbook documents the exact command, key-value inputs, result, effects,
non-effects, approval, verification, and recovery. The shared runtime should match the expected
Trellis-managed files, use no external dependency, and remain collection-local. Never execute it.

Executable source in a tool folder or a capability outside the fixed operation set is not an
internal-tool match. Recommend keeping the work in the Playbook or documenting it as a
project-owned script; do not delete or rewrite it automatically.

### Project-owned scripts

When a marked Playbook references a script outside `_cli`, review the Playbook's disclosure of:

- interpreter and dependencies;
- required authority and inputs;
- effects and non-effects;
- preview or dry-run behavior where feasible;
- success evidence;
- failure, interruption, retry, rollback, and recovery; and
- the boundary between script mechanics and human or agent judgment.

Do not apply the internal-tool capability restrictions to a project-owned script unless the
Playbook claims it is an internal Trellis tool.

### Maintenance evidence

Do not infer staleness from age or missing telemetry. Look for concrete evidence:

- named paths, commands, interfaces, or dependencies that no longer exist;
- explicit supersession;
- recorded failures, exceptions, TODOs, or verification drift;
- changed policy or authority that invalidates a boundary; and
- a tool or script whose documented contract no longer matches its source.

When evidence is insufficient, recommend validation or owner confirmation, not deletion.

## Report

Lead with the selected scope, marked Playbook inventory, supporting tools and scripts assessed,
coverage, and omissions. Prioritize recommendations by consequence and value.

Use a small vocabulary:

- Keep
- Clarify
- Repair
- Split
- Merge
- Re-scope
- Add verification
- Validate
- Update
- Archive
- Replace

For each recommendation, name the evidence, affected path, reason, and smallest sensible next
step. Distinguish direct findings from judgment-based advice.

## Safety

Audit must not create, edit, move, rename, or delete files; execute Playbooks or code; install
dependencies; browse or call network services; edit `AGENTS.md`; or stage, commit, push, publish,
or communicate externally. A clean audit is not proof that a Playbook works in practice.

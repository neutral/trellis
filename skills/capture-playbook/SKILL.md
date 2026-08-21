---
name: capture-playbook
description: Create or revise the exact project Playbook the user requests, including when they invoke /capture-playbook. Use the request as the design brief, ask only questions that materially change the Playbook, and write the agreed Playbook in the selected Trellis root. Do not mine conversations or discover candidates; route reflective requests to /discover-playbooks. Supporting mechanics may use a private safe _cli tool or an explicitly requested project-owned script.
---

# Capture Playbook

Create or revise the Playbook the user asks for.

Capture begins with an explicit design request. Discover is the optional reflective skill: it
examines selected sessions and returns self-contained `/capture-playbook ...` recommendations, but it does
not create files.

## Define the Playbook

Treat the user's request as the authoritative design brief. Extract:

- the future situation that should trigger the Playbook;
- the outcome and observable done condition;
- required inputs, context, and authority;
- important cues, decisions, phases, and adaptations;
- non-use cases, stop rules, exceptions, escalation, and recovery;
- independent verification;
- review triggers; and
- any explicitly requested supporting tool or script.

Ask only concise questions whose answers materially change the Playbook's boundary, storage,
safety, effects, or verification. Do not require a completed past example or conversation ID. Do
not invent adoption evidence, policy, credentials, endpoints, or approval.

A direct `/capture-playbook ...` request authorizes creation or revision of the described Playbook after
material ambiguity is resolved and the exact Markdown file plan is shown. Supporting code, new
dependencies, destructive behavior, external effects, or broader authority require a separate
clear user decision after full disclosure.

## Locate the Playbooks folder

Use, in order:

1. the exact Playbooks folder the user names;
2. `playbooks/` when its README contains `<!-- trellis-playbooks-root: format=1 -->`; or
3. another marked folder the user identifies.

Do not recursively search the whole work folder for possible collections. If no collection is
known, direct the user to `/trellis-init`. If multiple marked folders are explicitly in scope, ask the user
to choose.

## Choose create or update

Inspect the selected folder's managed index and marked Playbooks before choosing a path.

- Update an existing Playbook when it owns the same trigger and outcome.
- Create a new Playbook when it has an independent trigger, outcome, verification, or stewardship
  boundary.
- Do not duplicate a Playbook only because the new request uses different examples.
- Do not merge independent work merely because the steps are sequential.
- Do not split a Playbook so finely that each part loses the judgment or verification needed to
  be useful.

A Playbook ID uses lowercase letters, digits, and hyphens, begins and ends with a letter or digit,
and names a folder directly under the Playbooks folder. Reject collisions that differ only by
case or Unicode normalization.

## File location

Store one user-facing Playbook at:

```text
<playbooks-root>/<playbook-id>/PLAYBOOK.md
```

Optional references, examples, or explicitly requested scripts can live in the same Playbook
folder. Do not create a second indexed artifact type.

## Playbook format

Use this minimum format:

```markdown
<!-- trellis-playbook: format=1 -->
# <verb-led outcome>

<one sentence that explains the Playbook's purpose>

## Use When
<trigger, scope, prerequisites, and important non-use cases>

## Outcome
<one promised result and the observable done condition>

## Inputs And Context
<required materials, variable details, authority assumptions, and provenance needs>

## Method
<a small number of ordered phases with cues, decisions, actions, and adaptations>

## Supporting Tools
<optional host-native tools, internal `_cli` tools, or project-owned scripts>

## Boundaries
<permissions, exclusions, stop and escalation rules, interruption, recovery, and review triggers>

## Verification
<evidence independent of merely completing the steps>
```

Keep rationale beside the decision it changes. Parameterize incidental names, dates, paths, IDs,
and current values. Link reference material instead of burying the point-of-work method. Do not
claim that an intended method is proven unless the Playbook names the evidence for that claim.

## Supporting tools

Most Playbooks need only written guidance and capabilities already available to the person or
agent. Use this order:

1. **Host-native tools.** Prefer existing capabilities when their authority and review boundary
   are clear.
2. **Internal Trellis tool.** Use this only for a small deterministic local-file operation from
   the fixed built-in set.
3. **Project-owned script.** Use this only when the user explicitly requests a script or the
   required capability is outside the internal-tool profile.

### Internal Trellis tool

An internal tool lives at:

```text
<playbooks-root>/_cli/tools/<playbook-id>/<tool-id>/tool.json
```

The first approved internal tool also adds the shared runtime under `<playbooks-root>/_cli/`.
Trellis does not add a launcher at the project root.

A tool declaration selects exactly one built-in operation:

- `file.hash`
- `files.compare`
- `text.replace`
- `json.set`

The tool folder contains only `tool.json`; it does not contain generated executable source. The
shared runtime uses Node built-ins, explicit project-local regular files, bounded JSON output, and
a reviewed file hash before applying a write. It rejects path escape and symlinks and has no
network, shell, child-process, environment-secret, file-creation, deletion, permission,
publication, communication, remote, or consequential-judgment capability.

Before creating an internal tool, show:

- why the Playbook benefits from it;
- the selected operation and tool ID;
- the exact declaration and runtime files to create or reuse;
- the command and required inputs;
- reads, writes, and explicit non-effects;
- plan and apply behavior for a write;
- verification and recovery; and
- whether the existing runtime exactly matches the bundled template.

Do not install or merge the runtime by guess. Stop if an existing `_cli` path conflicts or differs
from the expected managed files.

### Project-owned script

Create a script only when the user explicitly asks for one after seeing its design. A script can
use capabilities outside the internal-tool profile, but the Playbook must document:

- interpreter and exact dependencies;
- required files, commands, network, services, credentials, or other authority;
- effects and explicit non-effects;
- invocation and parameters;
- preview or dry-run behavior where feasible;
- success evidence;
- interruption, retry, rollback, and recovery; and
- the boundary between script mechanics and human or agent judgment.

Store it under `<playbooks-root>/<playbook-id>/scripts/` unless the user chooses another path.
Do not call it an internal Trellis tool or imply the fixed-operation safety profile applies.
Creating a script does not authorize installing dependencies, testing it, or running it.

## Plan the change

Before writing, show:

- whether this is a new Playbook or an update;
- the exact Playbook ID and path;
- the complete proposed Playbook or an unambiguous bounded diff;
- the managed-index change;
- every support file to create or edit;
- preserved owner content;
- dependencies and authority, if any; and
- static verification to perform after writing.

For an existing Playbook, reread it immediately before writing and stop on drift. Apply only the
proposed change and preserve all unrelated owner content.

## Write and verify

1. Inspect every destination and ancestor. Reject symlinks and paths outside the selected work
   folder.
2. Write the Playbook and approved support atomically where possible.
3. Update only the managed index block in the collection README. Keep entries sorted by Playbook
   title, with a relative link and one-sentence summary.
4. Verify the marker, required headings, local links, index entry, and exact support paths.
5. Report every created or changed path and any incomplete effect.
6. Do not execute a new tool or script. Offer the exact separately approvable test or run only
   when it helps the user.

Never edit `AGENTS.md`, install dependencies, stage, commit, push, publish, send messages, or make
an external decision on the user's behalf.

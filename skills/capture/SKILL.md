---
name: capture
description: Use this skill when the user asks Trellis to create, save, refine, or identify a Playbook or Action; describes one they want; or explicitly invokes Capture. Do not use it for screenshots, recordings, data extraction, or unrelated meanings of “capture.” Support direct direction, reflective discovery, and hybrid refinement. Treat direct descriptions as design intent, not proof; keep them Provisional without varied operational evidence. For reflection, use the current conversation by default or only exact user-supplied chat or session IDs the host can retrieve; never enumerate ambient history. Propose a Playbook for contextual trigger-to-outcome work or an Action for deterministic operations over scoped local files. Keep judgment, network retrieval, external tools, publication, and outward effects in a Playbook. Disclose exact files and effects; write only independently approved suggestions. Never retain secrets, generic advice, unsupported claims, facts, or one-off results as reusable units themselves.
---

# Capture

Turn the useful way of working—not merely the session's answer—into something
the user and future agents can reuse. A quiet result with no capture is better
than a weak library entry.

## Choose The Input Route

Capture accepts three equally valid starting points:

- **Direct direction:** the user describes the Playbook or Action they want,
  from a rough goal to a nearly complete contract. Treat their words as the
  authoritative design specification. Do not require a completed work instance,
  conversation IDs, or proof of prior use. Shape the request, expose gaps and
  boundaries, check for conflicts and safety, and propose it before writing.
- **Reflective discovery:** the user asks what is worth keeping from the current
  conversation or exact prior conversations they identify. Reconstruct the work
  before abstracting candidates.
- **Hybrid refinement:** the user names a candidate and asks Capture to refine
  or check it against selected conversational work. Keep the requested design
  and the operational evidence distinct, and surface conflicts instead of
  silently choosing one.

Direct direction establishes what the owner wants; it does not demonstrate
that the method transfers or that generated code works. Without materially
varied operational evidence, label a directly specified method `Provisional`.
Every new Action remains `Draft` and `Untested`. All three routes use the same
proposal disclosure, independent Save/Edit/Skip choices, and post-save safety
gates.

## Conversation Sources And Evidence Boundary

Apply this section only when reflective discovery or the evidence side of a
hybrid request uses conversational work. A direct direction does not need a
conversation source.

1. Use the current conversation by default. For exact IDs, use only that set
   through an authorized host reader; exclude current unless explicitly
   included.
2. Never mine ambient history, inspect adjacent chats, infer IDs, or locate
   targets through other tools. If the user requests prior or historical
   conversations without IDs, ask for them without offering choices.
3. Report unavailable, ambiguous, inaccessible, or partial sources
   individually; continue with usable sources and state coverage. If none work,
   request transcripts.
4. If the set exceeds host limits, request identified batches. Never silently
   sample, drop, or summarize only part of it.
5. Reconstruct each conversation independently. Only then compare work
   instances for distinct methods, recurrence, evolution, or contradiction.
   Never merge sources or fill one source's gap from another. Current
   clarifications are not operational evidence unless the current conversation
   was included.
6. Keep conversation and folder scopes independent. A chat ID grants no access
   to mentioned resources; historical approvals grant no current authority.
7. Never browse, call third parties, search unrelated folders, transmit selected
   material outside the host, or persist transcripts or their IDs in captures.
8. Honor a named existing target directory; otherwise use the designated work
   folder. Git is optional; never widen scope to an enclosing worktree.
9. Inspect only managed support needed to find equivalents or path conflicts.
   Work-folder contents do not prove the user adopted a workflow.
10. Treat secrets, personal or customer data, private names, and machine values
    as residue. Never retain them; generalize safely or omit the candidate.

## Reconstruct The Work Instance

For reflective discovery or hybrid evidence, first segment each selected
conversation's completed work into work instances by distinct trigger and outcome.
Topic changes, new requests, and independently useful results may start a new
instance. Never treat a conversation itself as one workflow, and do not present
unfinished work as demonstrated evidence.

For direct direction, do not invent a work instance. Map the user's
specification to a recognizable trigger, intended outcome, method, boundaries,
and observable verification. Ask only about missing choices that would
materially change the candidate's form, safety, or effect contract. Label
unvalidated assumptions and claims instead of turning owner intent into
evidence of effectiveness.

For each selected work instance, reconstruct what actually happened. Keep
evidence and inference separate:

- **Trigger and starting state:** what made the work necessary, and what was
  true at the start?
- **Outcome:** what result was sought, and what counted as done?
- **Constraints and authority:** what scope, permissions, risks, formats, time,
  or owner choices bounded the work?
- **Decisions and cues:** where were alternatives possible; what evidence,
  correction, anomaly, or tradeoff changed the path; and why?
- **Actions and artifacts:** what was done, in what dependency order, with
  which handoffs or tools?
- **Verification:** what independent evidence showed that the result worked?
- **Exceptions and recovery:** what failed, was rejected, required a retry, or
  should cause a future user to stop, adapt, or escalate?
- **Provenance and confidence:** which points were stated by the user, observed
  in the work, supported by a local artifact, or inferred?

After reconstructing every source locally, compare work instances without
erasing their provenance. Similar methods across materially different instances
may strengthen transfer confidence. Repeated descriptions of the same
underlying work instance, branches of one task, or copied conversation content
do not constitute independent validation. Surface contradictions and evolution
rather than choosing one version silently.

When using conversational evidence, look especially for learning moments: an
explicit correction, a failed first attempt, a non-obvious decision cue, a
reusable validation method, repeated mechanics, a handoff boundary, or an
instruction the user generalized to future work. Do not judge the process only
by whether this instance succeeded.

Before classifying anything, require every candidate to be:

- **Grounded:** demonstrated, corrected, verified, or repeated in selected work,
  or directly specified by the user as an intended design; inference is labeled
  and direct intent is not presented as operational evidence.
- **Significant:** likely to preserve a non-obvious cue, reduce rediscovery or
  variance, strengthen a handoff or verification, or contain material risk
  enough to justify library and maintenance cost.
- **Repeatable:** a future trigger or caller is recognizable even though the
  surface facts may differ.
- **Applicable:** use, non-use, and variable parameters are clear; an accidental
  workaround is not universalized.
- **Valid:** the method is faithful to the user's direct specification or
  follows from selected work evidence—not merely a good result, hindsight,
  generic best practice, or an unsupported claim.
- **Bounded:** one trigger class, one outcome class, and one stewardship/change
  boundary can be named; an Action also has one coherent effect, approval,
  success, and recovery boundary.
- **Usable:** a competent future agent can act, verify, stop, and escalate
  without hidden conversation context.
- **Distinct:** no equivalent marked capture or obvious local command already
  owns the same job; improve an existing artifact instead of duplicating it.

Facts, citations, conclusions, and one-off outputs may be evidence, inputs, or
constraints, but must not become the reusable unit by themselves. Parameterize
names, dates, paths, IDs, current values, and incidental tools. Keep rejected
exploration only when it provides a reusable warning or recovery rule. Ask the
counterfactual: would this still help in the next recognizably similar situation
with different surface details?

Ask at most the few concise questions whose answers would materially change a
strong candidate's form, boundary, or safety. Do not interrogate the user merely
to make a weak candidate look complete. Finding nothing is a valid result.

## Find The Reusable Shape

The reusable unit is a bounded control loop:

```text
recognizable trigger -> orient -> decide -> act -> verify -> close
                              \-> adapt, recover, or escalate
```

Use these sizing invariants:

- **One Playbook owns one trigger class through one verified outcome class.**
  It may contain branches when they begin in the same situation and reconverge
  on the same outcome. It carries contextual interpretation, decision rules,
  coordination, exceptions, and escalation.
- **One Action owns one executable intent and one coherent effect, approval,
  success, and recovery boundary.** It may perform several mechanical steps
  only when that contract stays coherent. It must not absorb planning, policy
  choices, or unrelated side effects.

Split a candidate when parts have independent triggers, outcomes, callers,
approvers, permissions, effect classes, verification, recovery, stewardship,
or change cadence. A title that needs “and” is a prompt to test for a split,
not an automatic verdict. Mere sequence, convenience, a shared batch, or
passing one artifact forward is not enough to keep parts together. Keep them
together only when separation would leave the promised outcome incomplete or
unsafe and they share one approval, effect, verification, and recovery
boundary. If removing one phase leaves an independently valuable verified
result, split it.

A Playbook may invoke a separately reusable Action. That is not two forms for
one workflow: the Playbook owns judgment and orchestration; the Action owns a
bounded execution edge. Never present Playbook and Action as interchangeable
menu choices for the same candidate.

## Choose What Is Worth Offering

Select one or more distinct candidates only when each clears every required
gate. Do not impose a one-candidate cap, combine independent candidates, or
pad the list.

Prefer a candidate when retaining it would preserve one or more of:

- a hard-won decision cue or exception
- a repeatable method that reduces rediscovery or inconsistent handoffs
- an independent verification or recovery technique
- stable mechanics that remove recurring effort or error
- an explicit owner rule or bounded directly requested design

Treat one completed work instance, or repeated items from one substantially identical
batch, as provisional evidence. An explicit owner rule establishes intended
recurrence, not proven transfer. Established confidence requires evidence from
materially different instances or an owner statement that the practice is
already established across such instances. High-consequence transfer remains
Provisional until it has been validated on a materially different instance; a
single work instance may still justify a provisional guardrail.

A directly specified method without such operational evidence is also
Provisional. The user's specification may be exact enough to support a complete
proposal, but precision of intent does not raise method confidence. If the user
states that the practice is already established across materially different
instances, record that claim as the confidence basis without inventing
supporting details.

Classify the fitting form:

- **Playbook:** future instances require context-sensitive judgment, selection,
  sequencing, coordination, exceptions, or escalation.
- **Action:** inputs and exclusions are specifiable, behavior is mechanizable,
  local file effects are enumerable, success is independently observable,
  failure can stop or recover safely, and reuse or error reduction exceeds the
  runtime and maintenance cost.

An Action may only read and validate explicitly scoped local files or generate
and update explicitly scoped local files. It must not access a network, invoke
an external program or shell, publish, communicate, mutate a remote system,
delete material, change access, or make a consequential judgment. Put all such
work in a Playbook. A Playbook may use host-native tools to retrieve a local
input, invoke a separate Action over it, review the result, and—with fresh user
approval—handle any outward step.

If an otherwise strong Action lacks one or more consequential contract choices,
ask one neutral clarification about the smallest unresolved decision and stop.
Do not invent an endpoint, credential, input scope, permission, default, or
error policy to make code possible.

## Shape A Good Playbook

Draft the smallest sufficient point-of-work guide. Use this semantic template:

```markdown
<!-- trellis-capture: playbook format=1 -->
# <verb-led outcome>

Capture status: <Established — concise non-sensitive evidence across material
variation | Provisional — concise evidence and material variation still untested>

## Use When
<trigger, scope, prerequisites, and important non-use cases>

## Outcome
<one promised result and what done means>

## Method
<a small number of ordered phases with cue -> decision -> action rules>

## Boundaries
<authority, exceptions, stop/escalation rules, interruption/recovery, and the
change that should trigger review>

## Verification
<observable evidence independent of merely completing the steps>
```

Keep rationale beside the decision it changes. Parameterize case-specific
names, paths, dates, and values. Link supporting reference or training material
instead of turning the operational path into an encyclopedia. Reference a
shared Action instead of copying its implementation into several Playbooks.

## Shape A Good Action

Treat an Action as a trusted saved local command for one mechanical job, not as
“write a script.” Require one user-recognizable outcome; named typed local-file
inputs; explicit local reads, creates, and updates;
observable outputs and postconditions; safe failure and retry; exact
dependencies; bounded runtime and output; and representative success, boundary,
failure, and effect-containment tests. Split independent outputs, approvals,
effects, success conditions, recovery stories, or change cadences. Reject a
wrapper whose reuse, error reduction, or verification value does not justify
its maintenance.

Keep three independent claims:

- **Method confidence:** `Provisional` or `Established`, based only on
  operational evidence; direct intent can specify the method but cannot prove
  its effectiveness.
- **Implementation readiness:** `Untested`, `Tests passed`, or `Validated on
  representative data`, based only on evidence from executing this exact code.
- **Lifecycle:** `Draft`, `Active`, or `Deprecated`, changed only with owner approval.

Save every new implementation as `Draft` and `Untested`, even when the method
is Established. Never infer readiness from generated tests, static validation,
method recurrence, or a successful process exit.

Use this user-facing contract:

```markdown
# <verb-led operation>

<!-- trellis-capture: action format=2 -->

Method confidence: <Established | Provisional> — <privacy-safe basis>
Implementation readiness: Untested — focused tests have not been run
Lifecycle: Draft

## Purpose
<one executable intent and caller>

## Use When
<trigger, prerequisites, exclusions, and review trigger>

## Inputs
<accepted forms, normalization, defaults, and invalid cases>

## Outputs
<observable result and success postcondition>

## Run
<exact read-only command; or plan, show-plan, and apply commands bound to one
plan identifier; put typed inputs after `--`>

## Effects
<exact local reads, creates, updates, and explicit non-effects; temporary must
remain empty because private plan state is runner-managed>

## Success And Failure
<failure classes, interruption, retry safety, recovery, and review triggers>

## Verification
<postcondition evidence and receipt fields>

Focused test: `./trellis test <group> ... <action-name>` — requires separate approval
```

Run a read-only Action directly. For every create or update, make `plan` emit
exact operations, relevant input state, and a stable identifier without writes.
Make `apply` revalidate state and execute only that plan; refuse drift. Return a
human-readable and `json-v1` receipt with contract version, plan identifier,
changed paths, result, and postcondition evidence. Omit input values and file
contents; never create an ambient log.

Withhold the Action when rules are volatile, effects are unbounded, evidence is
unreviewable, or judgment remains consequential. Put network retrieval,
external tools, publication, communication, remote changes, deletion, access
changes, and judgment in a Playbook around separately useful local Actions.
Keep approval an actual opportunity to inspect, edit, reject, or stop.

### Local Action Implementation

Use a slash-delimited canonical ID whose segments each match
`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`. Use zero or more stable category segments
and a verb-object leaf, such as `quality/links/check-local-links`. The folder path,
manifest ID, handbook path, and space-delimited command must agree. Grouping is
only navigation: every leaf remains one independently useful Action with its
own effect, approval, success, and recovery boundary.

Keep the contract in the handbook and code in the isolated local tool project:

```text
trellis
_handbook/actions/<group>/.../<action-name>.md
_handbook/
  _cli/
    .npmrc
    package.json
    package-lock.json
    bin/trellis.mjs
    src/cli.mjs
    test/cli.test.mjs
    actions/<group>/.../<action-name>/
      action.json
      run.mjs
      run.test.mjs
  _scratch/
    .gitignore
    README.md
```

For the first Action, use the canonical `assets/node-tools/` runtime. Inspect
every destination; reuse only after proving compatibility, and stop on bytes
different from the template. Never merge or overwrite by guess or install the
runtime for a Playbook-only folder. The single extensionless launcher runs as
`./trellis` on POSIX and `node trellis` across supported platforms.

Treat `_handbook/_cli/` and `_handbook/_scratch/` as reserved Trellis
subtrees, not ordinary handbook content. A broad `_handbook/` Action scope is
invalid; name `_handbook/playbooks/`, `_handbook/actions/`, or a narrower owner
path instead. A Playbook or Trellis skill that needs temporary staging must
create a new per-use directory under `_handbook/_scratch/work/<producer>/`, use
only that directory, and remove it when finished. The trusted Action runtime
similarly creates distinct plan, transaction, or test directories under
`_scratch/`; Action code never receives access to the `_scratch/` parent.

Create this manifest beside each implementation:

<!-- markdownlint-disable MD013 -->
```json
{
  "format": 2, "version": 1, "id": "quality/links/check-local-links",
  "title": "Check local links", "summary": "Find broken local Markdown links.",
  "docs": "_handbook/actions/quality/links/check-local-links.md",
  "entrypoint": "run.mjs", "test": "run.test.mjs",
  "digests": { "entrypoint": "sha256:<64-lowercase-hex>", "test": "sha256:<64-lowercase-hex>" },
  "methodConfidence": { "status": "provisional", "basis": ["Observed once."], "reviewTriggers": ["Link conventions change."] },
  "readiness": { "status": "untested", "evidence": [], "validatedAt": null, "validatedOn": [] },
  "lifecycle": { "status": "draft", "reason": null, "replacement": null },
  "inputs": [{ "name": "root", "type": "path", "required": true,
    "description": "Local directory to inspect.", "examples": ["docs"] }],
  "outputs": [{ "name": "report", "type": "json", "description": "Stable missing-target list." }],
  "effects": { "reads": [{ "input": "root" }], "creates": [], "updates": [], "temporary": [] },
  "execution": { "mode": "read-only", "receipt": "json-v1", "timeoutMs": 60000, "maxOutputBytes": 1048576 },
  "success": { "postconditions": ["Every supported local link resolves or is reported."] },
  "dependencies": []
}
```
<!-- markdownlint-enable MD013 -->

Replace digest placeholders with actual SHA-256 hashes of final entrypoint and
test bytes. Use named path inputs in effect scopes so caller-supplied paths do
not require a whole-folder `.` grant. Use static work-folder-relative scopes
only when no narrower input exists. Leave `temporary` empty: private plan state
is runner-managed, and Action code receives no write permission. Reject
absolute paths, `..`, escapes, implicit overwrites, and deletes. Add no network,
environment, or process capability.

Make the runner recursively discover exact Action paths, resolve fixed local
files, parse the manifest before import, launch without a shell, and accept
typed named arguments only after `--`. Reject symlinks, files in group
directories, path/manifest disagreement, case-insensitive collisions, and a
top-level group or Action named `help`, `list`, `show`, `validate`, `doctor`,
`version`, `run`, `test`, `plan`, `show-plan`, `apply`, or `scaffold`.
Make `list` render the space-delimited invocation and `show` surface confidence,
readiness, lifecycle, inputs, outputs, success, effects, examples, and handbook
link. Keep valid entries visible when another Action is malformed.

Require `timeoutMs` 100–300000 (prefer 60000) and `maxOutputBytes` 1024–4194304
(prefer 1048576). Accept one `trellis.action-result/v1` or
`trellis.action-plan/v1`; fail other/excess stdout. Store plans owner-only in
`_handbook/_scratch/plans/`; omit input values and contents from receipts.
Saved plans may contain exact inputs and before/after file bytes and remain
until deleted. Test and transaction directories are per-use and are removed
after successful cleanup; report retained recovery material precisely.

For read-only output emit `{schema,status,summary,outputs,verification}` with
`ok|failed`, one `{name,value}` per output, and `{check,ok,detail?}` checks. For
`--trellis-plan`, emit `{schema,summary,operations,verification}`. Each operation
is `{kind,path,before,after,encoding,content}`: create uses `before:null`, update
uses the prior SHA-256, and `after` hashes `utf8|base64` content. Never delete.

Invoke a read-only Action directly, for example
`./trellis quality links check-local-links -- --root docs`. The same direct
form for a create/update Action creates and saves an exact plan; it never
applies. The explicit equivalent is
`./trellis plan quality links check-local-links -- <inputs>`. Review with
`./trellis show-plan quality links check-local-links --plan <plan-id>`, then
apply only that identifier with
`./trellis apply quality links check-local-links --plan <plan-id>`. Refuse
execution or planning for `Untested`, `Draft`, or `Deprecated` unless the user
gives the exact deliberate override for that state. Keep focused testing
separately
approvable; never make saving the Action an override.

Default to built-ins and `node:test`. Use only the reviewed Node execution
ranges; pin npm and exact dependencies; reject non-registry sources and
dependency executables; deny lifecycle scripts.
Add no dependency when built-ins suffice. For an approved exact dependency,
verify npm policy, install with scripts disabled, inspect manifest, lock,
provenance, and scripts, then run package and signature audits only with
execution approval. A required lifecycle script needs separate release-specific
approval and a pinned allowlist. Never use broad updates, remote `npx`/npm exec,
unversioned sources, forced dependency resolution, blanket script approval, or
registry credentials.

## Proposal Gate

Lead with the useful method, not the storage operation. For direct direction,
start with the requested outcome and design. For reflective discovery, start
with what the selected work taught. For a hybrid, distinguish requested design
from supporting or conflicting evidence. First show a compact numbered card for
every qualifying candidate:

- **Insight and benefit:** the non-obvious lesson and repeat effort, error, or
  risk it would reduce.
- **Evidence and method confidence:** whether the basis is direct owner
  direction, selected operational evidence, or both; what supports Established
  or Provisional; and what material variation remains.
- **Shape:** Playbook trigger → outcome, or Action local inputs → result.
- **Use boundary:** when to use it, when not to, and what must stop or escalate.
- **For an Action:** read/generate/update badge, example command, reviewable
  result and done condition, plus `Draft · Untested`; label every generate or
  update direct invocation as plan-only so the card never implies an apply.
- **Choice:** Review to save, Edit, or Skip. This choice authorizes no write.

For only the candidates the user chooses to review, then show the complete
compact Playbook or Action contract; `New` or the exact bounded update; required
dependencies; exact support files and managed overview change; preserved owner
content; and static verification. For an Action also show typed named inputs,
outputs, exact local effect scopes, read-only or plan/show-plan/apply commands,
receipt and postcondition, failure and recovery, exact dependencies, first-Action
runtime paths, and the separately approvable test command. Include first-
capture handbook initialization when needed. Only after this full disclosure
ask whether to Save, Edit, or Skip each selected candidate.

Before asking for approval, mentally walk each proposal through:

1. a normal future instance
2. a boundary or negative instance
3. a foreseeable exception or interruption
4. its observable completion test

Revise or withhold a proposal that depends on hidden session context, invents
policy, cannot say when not to use it, or cannot prove completion.

A card or proposal is not authorization. Create or edit nothing until the user
accepts a fully disclosed numbered proposal. Approval of one never authorizes another.
Every proposal must work independently or declare required dependencies. If an
approved subset omits a required new dependency, do not save the dependent
artifact; explain the missing dependency and ask the user rather than inferring
approval.

When new operational evidence improves an existing marked capture, propose an
update instead of a duplicate. Name the exact existing artifact and show the
complete revision or an unambiguous bounded diff. Preserve owner edits and all
content outside the proposed change. Treat promotion from Provisional to
Established as its own evidence-backed change requiring explicit approval; a
new use does not silently rewrite status or boundaries.

When nothing qualifies, say so and stop without an approval question.

## After Acceptance

1. Identify only the explicitly approved proposals. Recheck equivalent
   captures, path conflicts, and required-dependency closure because
   work-folder state may have changed. Stop before writing any dependent
   artifact whose required proposal was not approved and is not already
   present.
2. Before any preview or write, inspect every planned capture and support path
   plus each existing ancestor. Reject symlinks and require every resolved path
   to remain inside the selected work folder. Stop rather than following,
   replacing, or writing through an ambiguous path.
3. For an approved update, reread the named artifact and compare it with the
   proposal. Stop on intervening drift. Apply only the approved change and
   preserve all other content; never replace an owner-edited page by inference.
4. If handbook support is missing, treat `scripts/initialize_handbook.py` as a
   Class 2 local-change helper. It requires CPython 3.11 or newer and only the
   standard library; never install or update Python for it. Disclose that its
   local diff preview may reproduce existing handbook text in terminal output.
   Resolve it relative to this skill and run each form with `-E -S -B` so
   ambient Python environment, site customization, and bytecode writes cannot
   alter the helper before its own boundary checks. Use the same explicit
   absolute work-folder target:

   ```text
   python3 -E -S -B <initializer> --target <absolute-work-folder>
   python3 -E -S -B <initializer> --target <absolute-work-folder> --write
   python3 -E -S -B <initializer> --target <absolute-work-folder>
   ```

   Require the first preview to match the approval, the write to complete its
   state-checked transaction, and the final preview to report no changes. Stop
   on drift, incomplete rollback, or retained recovery material and report its
   exact repository-relative path. An unfinished transaction blocks ordinary
   preview and write. Preview recovery separately:

   ```text
   python3 -E -S -B <initializer> --target <absolute-work-folder> --recover
   ```

   Show that recovery preview and obtain separate approval before applying it:

   ```text
   python3 -E -S -B <initializer> --target <absolute-work-folder> --recover --write
   ```

   Never infer recovery approval, and never apply recovery automatically. After
   recovery, rerun the ordinary preview before continuing. Initialization
   creates the tracked
   `_handbook/_scratch/.gitignore` and `README.md` policy files; generated
   scratch children remain ignored.
5. Save each Playbook under `_handbook/playbooks/` using the Playbook template
   above. Update only the managed block in `_handbook/overview.md`.
6. For each Action, follow **Local Action Implementation** above: save its
   marked contract under its mirrored `_handbook/actions/<group>/.../` path,
   its manifest, implementation, and test under the corresponding
   `_handbook/_cli/actions/<group>/.../<action-name>/` path, and its managed
   overview entry.
   Install the bundled runtime only for the first Action and stop on conflicting
   paths. Any disclosed dependency download requires separate explicit
   approval; it must never include conversation material.
7. Add no behavior, dependency, effect, or support file that the approved
   proposal did not disclose.
8. If the sibling Audit skill is installed, resolve
   `../audit/scripts/audit_support.py` relative to this skill and run its static
   structural audit with a 60-second host timeout and a 4 MiB combined captured
   stdout/stderr limit:

   ```text
   python3 -E -S -B <audit-script> --target <absolute-work-folder> --json
   ```

   Otherwise inspect the managed markers, links, required headings, Action
   manifest/page agreement, and support paths statically and report that the
   bundled helper was unavailable. Do not run the new Action or its tests.
9. Report exact file changes, method confidence, `Draft · Untested` readiness,
   and the exact focused test command as the immediate optional next step. Do
   not test, validate on representative data, or activate without separate
   approval for that step.
10. If root `AGENTS.md` does not mention `_handbook`, return this optional line
   in chat and say Trellis did not write it:

   <!-- markdownlint-disable MD013 -->
   ```markdown
   When relevant, read [`_handbook/overview.md`](_handbook/overview.md) for project Playbooks and Actions.
   ```
   <!-- markdownlint-enable MD013 -->

## Execution And Ownership Gates

Saving an Action does not authorize executing it. Show the exact
`./trellis test <group> ... <action-name>` command and declared effects after
static validation; run a test or smoke command only after separate approval.

After a separately approved test or representative-data run, report the exact
evidence before proposing any readiness or lifecycle edit. Never update status
because a command was requested or merely exited. Moving to `Tests passed`,
`Validated on representative data`, `Active`, or `Deprecated` requires an exact
owner-approved page and manifest change; activation is not implied by testing.

Never create or edit `AGENTS.md` or another agent instruction file. Never
stage, commit, push, publish, send messages, or communicate on the user's behalf.
The only permitted external request is an exact dependency operation that was
separately disclosed and approved above; it must contain no conversation
material. Never make an authoritative decision on the user's behalf. If the
work folder uses version control, its history remains with the user; capture
ownership always does.

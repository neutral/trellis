---
name: audit
description: Use this skill when the user asks Trellis to audit, inspect, review, or improve its handbook, setup, saved Playbooks and Actions, or complete collection; or explicitly invokes Audit. Do not use it for generic code, security, financial, or content audits. Run the read-only static audit, enforce the v4 recursive Action namespace and format-2 local-files-only boundary, and assess every marked capture for followability, bounded trigger-to-outcome shape, correct Playbook-versus-Action fit, hidden context, verification, exceptions, readiness, lifecycle, and safe recovery. Review the portfolio for overlap, fragmentation, kitchen-sink scope, stale or superseded guidance, and evidence-based pruning opportunities. Return prioritized keep, clarify, repair, split, merge, extract, validate, deprecate, or retire suggestions without executing or changing anything.
---

# Audit

Help the user make their saved ways of working smaller, clearer, safer, and
more useful. Audit is advisory evidence, not formal certification and not an
automatic cleanup operation.

## Scope And Safety

Audit only the support Trellis owns:

- the managed block in `_handbook/overview.md`
- marked Playbooks and Action pages linked from it
- marked orphan captures
- Action manifests, static implementations, tests, and bundled runtime policy
- root `AGENTS.md` only to detect an optional `_handbook` reference

`_handbook` is shared owner space. Ignore unmarked material, work-folder
content, organization, formats, and unrelated instructions. Do not infer what
the folder ought to contain or which workflows the owner ought to adopt.

Stay local and read-only. Do not browse, call network services, execute or
import Action code, run Action tests, invoke npm, install dependencies, or
change any file. Treat secrets or personal data encountered during inspection
as private; do not reproduce their values in the report.

Treat the bundled `audit_support.py` as a Class 1 local-read helper. It requires
CPython 3.11 or newer, uses only the standard library, and never installs or
updates Python. If that runtime is unavailable, stop without substituting or
installing one and report that the audit is incomplete.

## Select The Audit Depth

Honor a user-requested narrow mode. Otherwise a request to “audit Trellis”
includes the first four passes below:

1. **Foundation:** managed markers, capture links, page shape, manifests,
   v4 launcher and private runtime files, recursive Action topology, current
   format enforcement, local-only effects, contract agreement, package metadata,
   digests, and policy integrity.
2. **Artifact:** whether each marked Playbook or Action can guide a competent
   future user without hidden conversation context.
3. **Portfolio:** whether the captures are discoverable and sensibly divided,
   without duplicate, conflicting, fragmented, or kitchen-sink entries.
4. **Lifecycle:** whether evidence shows an artifact is obsolete, superseded,
   broken by changed interfaces, or in need of validation.
5. **Simulation:** only when explicitly requested, statically walk selected
   artifacts through normal, boundary, exception, and interrupted cases. This
   still does not authorize executing an Action.

Inventory the marked artifacts before semantic review. Never silently sample
or claim full coverage when context limits make it infeasible. Report the total
inventory, the artifacts assessed, every omission, and why; offer bounded
batches that can eventually cover the collection. A narrow user-requested
scope is a scope choice, not an omission.

## Pass 1 — Foundation

1. If the user names a target directory, honor that exact scope after verifying
   it exists. Otherwise use the tool-designated workspace or current work
   folder. Git is optional; never widen the scope to an enclosing worktree.
2. Resolve `scripts/audit_support.py` relative to this skill and run it with a
   60-second host timeout and a 4 MiB captured-output limit. Use `-E -S -B` so
   ambient Python environment, site customization, and bytecode writes cannot
   alter the helper before its own boundary checks:

   ```text
   python3 -E -S -B <audit-script> --target <absolute-work-folder> --json
   ```

3. Require the `trellis.audit-result.v1` JSON schema. Treat exit `1` as findings
   to investigate, not permission to repair. Exit `2` means invalid or unsafe
   invocation, unsupported Python, a filesystem failure, or an enforced
   resource ceiling; in each case the structural audit is incomplete. Read
   every referenced Trellis file needed to confirm context.
4. Treat a clean structural result as the beginning of the audit, not proof
   that the artifacts are useful or current.
5. Confirm the helper recursively inventories `_handbook/_cli/actions/` independently
   of handbook links. A group directory contains only regular subdirectories;
   a leaf contains exactly `action.json`, `run.mjs`, and `run.test.mjs`. Do not
   traverse symlinks. Assess malformed leaves without letting one malformed
   group, leaf, or entry hide valid siblings.
6. Read every integrity and **Validation needed** result. The helper uses only
   static text, JSON, hashes, and local path checks; never fill an uncertainty
   by running code, tests, Node, or npm. Its default ceilings are 4 MiB per
   file, 32 MiB total file content, 10,000 directory entries, depth 32, 5,000
   findings, 50,000 work units, and 4 MiB of output. Never widen them silently.

## Pass 2 — Artifact Quality

Use one invariant for sizing:

- **One Playbook owns one recognizable trigger class through one verified
  outcome class.** Branches belong when they share the trigger and reconverge
  on the outcome.
- **One Action owns one executable intent and one coherent effect, approval,
  success, and recovery boundary.** Several mechanical steps may stay together
  only when that whole contract remains coherent.

### Playbook Lens

For every marked Playbook, assess:

- **Use When:** trigger and scope are recognizable, along with prerequisites,
  authority, and important non-use cases where they materially affect safe or
  correct use.
- **Outcome:** one promised result and observable done condition are clear.
- **Method:** the operational path is concise; phases are ordered; cues and
  decision rules appear where they change the next action.
- **Boundaries:** exceptions, stop/escalation conditions, permissions, and
  interruption or recovery are explicit where relevant; Capture confidence,
  its privacy-safe validation basis or gap, and a change-based review trigger
  remain discoverable.
- **Verification:** completion relies on evidence, not merely checking off
  steps or trusting the process's own output.
- **Transfer:** case-specific names, dates, paths, and conclusions are
  parameterized; no private transcript or hidden context is required.
- **Point-of-work fit:** background, policy, examples, or training material do
  not bury the procedure and can be linked separately when needed.

The Trellis template uses `Use When`, `Outcome`, `Method`, `Boundaries`, and
`Verification`. Missing headings are structural findings; headings containing
boilerplate without the semantic contract are operability findings.

### Action Lens

For every marked Action, compare its page, manifest, static implementation,
and static test. Assess:

- one verb-led purpose and caller/trigger
- one slash-delimited canonical ID whose kebab-case segments exactly mirror
  `_handbook/_cli/actions/<segments>/`, manifest `id`, and
  `_handbook/actions/<segments>.md`; group directories are navigation only
- recursive topology with no symlinks, files in groups, children or extra
  files in leaves, case-insensitive path collisions, page/leaf orphans, or a
  top-level segment named `help`, `list`, `show`, `validate`, `doctor`,
  `version`, `run`, `test`, `plan`, `show-plan`, `apply`, or `scaffold`
- Action page marker and `action.json` format 2; every other format is invalid
  and does not enter page/manifest agreement or static contract analysis
- page and manifest agreement on title; method confidence; implementation
  readiness; lifecycle; inputs; outputs; effects; run commands; success
  conditions; review triggers; and verification
- unique typed named inputs, with every local file scope either a safe static
  work-folder-relative `{ "path": ... }` or `{ "input": ... }` bound to a
  declared `path`, `file`, or `directory` input
- observable outputs, with every create/update Action declaring at least one
  `file` or `files` output and no non-file output; a non-empty independently
  checkable success postcondition; exact dependencies; runtime bounds; and
  current entrypoint and test digests
- effects containing only explicit local `reads`, `creates`, and `updates`,
  with the reserved `temporary` array present and empty; reject absolute paths,
  `..`, globs, templates, static `.` effect scopes, non-portable path names,
  symlink escape, secrets, Action-managed temporary material, and deletes
- exact `Run` commands render slash-delimited IDs as space-delimited path
  segments and map every caller input to its named argument after `--`:
  read-only Actions use direct `./trellis <group> ... <action-name>`; the same
  direct form plans create/update Actions, with explicit
  `./trellis plan <group> ... <action-name>` also accepted; review uses
  `./trellis show-plan <group> ... <action-name> --plan <plan-id>` and apply
  uses `./trellis apply <group> ... <action-name> --plan <plan-id>`, with the
  same reviewed plan identifier and no caller inputs on show or apply;
  verification uses exact `./trellis test <group> ... <action-name>`
- read-only implementations emit `trellis.action-result/v1`; plan
  implementations emit `trellis.action-plan/v1` with exact create/update
  operations, before-state hashes, exact after bytes, and verification; the
  trusted runner shows the saved plan for review, alone applies its reviewed
  bytes, refuses drift, verifies postconditions, and returns
  `trellis.action-receipt/v1`
- distinct handling, where applicable, of invalid input, ordinary failure,
  partial completion, interruption, and unsafe or ambiguous state
- idempotency and safe-retry claims where repetition can duplicate effects
- rollback, compensation, or human recovery proportional to impact where the
  operation can leave effects behind
- focused normal, boundary, failure, and effect-containment tests, with test
  imports and assertions still aligned to the implementation and receipt
  contract
- runtime/dependency assumptions, declared static imports, no embedded secrets
  or case-specific machine paths, and no stale digest or readiness claim
- change-based review triggers and lifecycle evidence, including a reason for
  deprecation and any replacement

Enforce the permanent Action boundary. An Action may only read or validate
explicitly scoped local files, or generate and update explicitly scoped local
files through the trusted plan/apply runner. It must never access a network or
environment/secret authority; invoke an external program, child process, or
shell; publish or communicate; mutate a remote system; delete material; change
access or ownership; or make a consequential judgment. Disclosure, approval,
tests, or maturity do not legalize these capabilities. Put retrieval,
orchestration, judgment, publication, and other outward work in a Playbook,
which may use host-native tools around separately useful local Actions with
fresh approval.

Keep three claims independent:

- **Method confidence** is `Provisional` or `Established` and rests only on
  recurrence evidence across material variation.
- **Implementation readiness** is `Untested`, `Tests passed`, or `Validated on
  representative data` and rests only on execution evidence for the exact
  digested code.
- **Lifecycle** is `Draft`, `Active`, or `Deprecated` and changes only through
  an owner-approved transition.

`Established` method confidence may correctly coexist with `Draft` and
`Untested` implementation state. `Active` may also coexist with `Untested`:
lifecycle does not promote readiness, and the runner gates execution unless the
caller gives the exact deliberate readiness override. Untested evidence may
record failed attempts, but only `Validated on representative data` carries
complete `validatedAt` and representative `validatedOn` metadata. Generated
tests, static inspection, method recurrence, or process exit do not establish
readiness. Report untested code, test skips/placeholders, digest mismatch,
execution claims without evidence, and tests that no longer import or assert
the current contract.

Treat direct static contradictions among the page, manifest, implementation,
and test as integrity failures. When behavior depends on generated code,
computed imports, opaque dependency internals, or dynamic paths that cannot be
established safely through static inspection, report **Validation needed**
rather than inferring a mismatch. Explicit network, environment, process,
shell, direct-write, delete, or access-change behavior is an integrity failure,
not an uncertainty.

The Trellis Action template uses `Purpose`, `Use When`, `Inputs`, `Outputs`,
`Run`, `Effects`, `Success And Failure`, and `Verification`. As with Playbooks,
required headings make the contract discoverable but do not prove that its
content is complete or safe.

Static Audit never imports or runs an implementation or test and never invokes
Node or npm. For every recursively discovered leaf, restrict source inspection
to its two digested regular source files, `run.mjs` and `run.test.mjs`; report
any additional leaf entry because the closed Action contract contains only
`action.json`, `run.mjs`, and `run.test.mjs`. Treat group directories as
topology, not Action source. Executable helper source is code outside the
manifest digest contract. Production code imports no local helper module; the
test may import only `./run.mjs`. Do not scan unrelated owner code.
Recommend moving any hidden judgment or outward responsibility to a Playbook;
do not propose a capability exception.

Require the v4 root launcher `trellis` as the sole root launcher and the
reviewed private runtime under `_handbook/_cli`, including
`_handbook/_cli/bin/trellis.mjs`. Treat `_handbook/_cli` and
`_handbook/_scratch` as private Trellis areas even though `_handbook` remains
shared owner space. Validate only this current layout. Do not classify or
interpret any other root file or directory as a former Trellis layout. Audit
never renames or removes files.

## Pass 3 — Portfolio Fitness

Compare marked capture titles, summaries, triggers, outcomes, methods, and
Action contracts. Look for:

- **Kitchen sinks:** independent triggers or done states, unrelated actors,
  permissions, effects, verification, recovery, ownership, or change cadence
  combined in one artifact.
- **Fragmentation:** pieces that are always invoked together and are incomplete
  or misleading alone.
- **Overlap or conflict:** captures that claim the same trigger and outcome but
  diverge without a stated precedence or applicability boundary.
- **Duplicated mechanics:** Playbooks copying operations that should reference
  one independently reusable Action.
- **Volatility leaks:** durable decision guidance coupled to tool-specific
  commands or rules that change on a different cadence.
- **Discovery problems:** vague titles, summaries that omit the trigger or
  outcome, broken links, marked orphans, or active and deprecated guidance
  presented together without distinction.

Recommend a split only at a real boundary. Recommend a merge only when the
parts share trigger, outcome, stewardship, and verification and cannot stand
alone. Deliberate redundancy may protect a severe-risk step; do not remove it
merely for brevity.

Mere sequence, convenience, a shared batch, or passing one artifact forward is
not evidence that parts belong together. If the existing artifact lacks enough
evidence to make proposed parts independently usable, recommend
**Validate before Split**; do not manufacture skeletal captures.

Do not invent “missing” Playbooks or Actions from general work-folder content.
Capture, not Audit, shapes directly requested workflows or discovers them in
selected conversational work.

## Pass 4 — Lifecycle Fitness

Look for evidence, not age-based guesses. You may check the existence of local
paths or commands only when a marked capture explicitly names them; do not scan
unrelated work-folder content for lifecycle clues:

- broken or renamed local commands, paths, interfaces, or dependencies
- an artifact that explicitly supersedes another
- owner evidence supplied in the request, evidence recorded in the marked
  artifact, or current Trellis contracts that contradict the active capture
- repeated exceptions, failed verification, or TODOs recorded in the marked
  artifact or its tests
- missing stewardship or revision cues where the procedure depends on a
  changing external rule, interface, or authority

Age alone is not staleness. Lack of observed use is not proof of non-use. When
evidence is insufficient, report **Validation needed**, not “retire.” A retired
artifact may need to leave active discovery while remaining in owner-chosen
history; never delete it automatically.

Before recommending deprecation or retirement:

1. Name the future trigger the artifact claims and show why a replacement or
   current evidence covers it better, or why that trigger no longer exists.
2. Check inbound Trellis links, Action references, and declared dependencies.
3. Identify unique useful content and provenance that must migrate or remain in
   owner-chosen history.
4. Distinguish “not seen in available evidence” from “not used,” and name the
   owner confirmation still needed for applicability and retention.
5. For duplicates, recommend a canonical artifact, migration of unique value,
   and deprecation before retirement. For contradictions, surface the exact
   conflict and ask which instruction has authority.

## Recommendation Vocabulary

Use the smallest fitting recommendation:

- **Keep:** no issue detected in the performed static passes; state any
  unvalidated behavior or currentness limit that remains.
- **Clarify:** preserve the shape but add a cue, boundary, authority, or done
  condition.
- **Repair:** fix structural drift, a broken reference, a contract mismatch, or
  an unsafe omission.
- **Split:** divide independent trigger-to-outcome boundaries or independent
  effect, approval, success, and recovery boundaries.
- **Merge:** combine fragments that cannot usefully stand alone.
- **Extract Action:** move independently reusable mechanics out of prose while
  leaving judgment and orchestration in the Playbook.
- **Move judgment to Playbook:** narrow an Action that is making contextual or
  policy choices.
- **Deprecate:** keep temporarily visible only when an identified replacement
  or demonstrated temporary risk justifies the transition warning.
- **Retire:** remove from active discovery only when evidence shows it is
  obsolete, superseded, or no longer applicable.
- **Validate:** gather a representative use, owner decision, or independent
  test before changing the artifact.
- **Validate before Split:** gather enough representative evidence to draft
  independently usable parts before replacing an oversized artifact.

## Report

Group results in this order:

1. **Integrity failures** — broken, contradictory, unsafe, or undisclosed
2. **Operability risks** — ambiguous or likely unusable at the point of work
3. **Portfolio improvements** — Split, Merge, Extract Action, Move judgment to
   Playbook, or discovery clarification
4. **Validation needed** — plausible lifecycle concern with insufficient proof
5. **Healthy captures** — concise keep decisions, when useful

For every nontrivial finding include:

```text
Artifact and location
Pass: <Foundation | Artifact | Portfolio | Lifecycle | Simulation>
Evidence
Why it matters
Confidence
Smallest recommended change
Recommendation
Owner decision or evidence needed
```

Prioritize leverage over volume. Do not dump every rubric question into the
report, and do not mistake stylistic preference for a finding. State which
passes were performed and which evidence was unavailable. Start with coverage:
inventory count, assessed artifacts, omitted artifacts, and omission reasons.

If root `AGENTS.md` lacks `_handbook`, keep it separate from findings and give
the user this optional line, saying Trellis did not write it:

<!-- markdownlint-disable MD013 -->
```markdown
When relevant, read [`_handbook/overview.md`](_handbook/overview.md) for project Playbooks and Actions.
```
<!-- markdownlint-enable MD013 -->

A missing reference is not a failed audit.

## Non-Destructive Boundary

Do not edit, create, move, delete, stage, commit, push, or publish. Do not
execute Actions, tests, npm, or implementation modules. Even an obvious repair,
split, merge, deprecation, or retirement remains a suggestion until the user
separately asks for that change.

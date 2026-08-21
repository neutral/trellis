# How Trellis Creates and Discovers Playbooks

Trellis separates explicit creation from reflective discovery:

- **Capture** creates the specific Playbook the user requests.
- **Discover** studies selected work and returns one or more self-contained Capture prompts.

The separation keeps Capture predictable, makes reflection optional, and leaves the user in
control of which inferred method becomes maintained project guidance.

## The reusable unit

A Trellis Playbook owns one recognizable situation through one verified outcome. It is a bounded
control loop:

```text
recognizable trigger -> orient -> decide -> act -> verify -> close
                              \-> adapt, recover, or escalate
```

The Playbook keeps the context that changes action: cues, decisions, sequencing, exceptions,
coordination, authority, escalation, and independent verification. It can refer to tools, but it
is not reduced to a command or script.

A strong Playbook can answer:

- When should a future agent use this?
- What result does it promise, and what counts as done?
- What inputs, context, and authority does it assume?
- Which cues change the next decision or action?
- When should the agent stop, adapt, recover, or escalate?
- Which evidence shows that the result is correct?
- What change should trigger maintenance review?

## Capture: explicit design

Capture starts from owner direction. The user can provide a rough intent, a structured outline,
or a nearly finished Playbook specification. Capture treats that request as the design brief and
does not require a completed prior example or conversation ID.

Capture maps the request to the Playbook questions above. It asks only for missing choices that
would materially change the Playbook's boundary, safety, path, supporting tools, or verification.
It does not interrogate the user merely to make an unimportant artifact look complete.

Direct direction establishes what the owner wants. It does not by itself prove that the method
works across varied situations. When effectiveness or transfer matters, the Playbook should state
the evidence or leave the claim bounded rather than inventing confidence.

Before writing, Capture checks the selected Playbooks folder for:

- an equivalent Playbook that should be updated rather than duplicated;
- a path or identifier collision;
- a broader or narrower Playbook whose boundary would become confusing;
- a referenced tool or script with incompatible effects; and
- owner content that must be preserved.

A direct `/capture-playbook ...` request authorizes the described Playbook change after material ambiguity
is resolved and the Markdown file plan is disclosed. Supporting code, dependencies, destructive
behavior, or external effects require a separate clear user decision.

## Discover: selected-session reflection

Discover uses the current session by default or exact session IDs the user selects and the host
can retrieve. It never enumerates ambient history, searches adjacent conversations, guesses IDs,
or treats a past approval as current authority.

When the user selects more than one session, Discover reconstructs each independently before
comparing them. One session does not fill gaps in another. Current clarification can shape a
recommendation but is not retroactive evidence of what happened before.

### Reconstruct the work

Discover separates distinct completed work instances by trigger and outcome. One session can
contain several instances, and an unfinished branch is not a demonstrated method.

For each instance, Discover reconstructs:

- **Trigger and starting state:** what made the work necessary and what was true at the start;
- **Outcome:** what result was sought and what counted as done;
- **Constraints and authority:** scope, permissions, risks, owner choices, and fixed formats;
- **Decisions and cues:** where alternatives existed and what changed the path;
- **Activities and artifacts:** what happened and in what dependency order;
- **Verification:** what evidence showed that the result worked;
- **Exceptions and recovery:** failures, retries, rejected defaults, handoffs, and stop rules; and
- **Provenance:** which claims came from the user, observed work, a selected artifact, or inference.

This approach is informed by cognitive task analysis, the Critical Decision Method,
after-action review, and research on outcome bias. Trellis does not claim to conduct a formal
interview or quality-management assessment. The practical lesson is to expose uncertainty rather
than fill it with plausible fiction.

### Look for turning points

Strong candidates often preserve:

- a correction or rejected default;
- a hidden constraint that changed the plan;
- a failed attempt and why it failed;
- a cue that distinguished plausible choices;
- a verification step that caught a believable error;
- an exception, fallback, escalation, or handoff; or
- stable mechanics that repeated while judgment remained contextual.

A good result does not prove that the method was good. Discover examines the decisions,
boundaries, and verification that produced the outcome.

### Apply the candidate gates

A recommendation must be:

- **Grounded:** traceable to selected work or explicit clarification, with inference labeled;
- **Significant:** worth saving and maintaining;
- **Repeatable:** entered by a recognizable future situation;
- **Applicable:** clear about use, non-use, and variable details;
- **Valid:** faithful to the selected evidence rather than generic advice or hindsight;
- **Bounded:** one trigger class and one outcome class;
- **Usable:** followable without the original conversation;
- **Distinct:** not already owned by an equivalent Playbook; and
- **Safe to retain:** free of secrets, unnecessary personal data, and private residue.

Facts, conclusions, citations, and one-off outputs can support a Playbook but are not the reusable
unit by themselves. Parameterize incidental names, dates, paths, IDs, and values.

Finding no strong recommendation is a valid result.

### Return Capture prompts, not files

Discover does not create, update, or save a Playbook. It returns a self-contained command such as:

```text
/capture-playbook Create a Playbook named "Verify release package parity". Use it when source and generated
packages must agree before release. The Playbook should ...
```

A useful recommendation includes enough detail for Capture to work without the original session:

- proposed title or outcome;
- future trigger and non-use boundary;
- desired outcome and verification;
- important cues, decisions, exceptions, and escalation;
- variables Capture should parameterize;
- evidence limits or contradictions;
- whether an existing Playbook should be updated; and
- a supporting-tool suggestion only when it materially improves the method.

The user can edit, combine, ignore, or run each recommendation manually. Discover never invokes
Capture on the user's behalf.

## Playbook sizing

Split a proposed Playbook when parts have independent triggers, outcomes, callers, authority,
verification, recovery, stewardship, or change cadence. Keep branches together when they begin in
the same recognizable situation and reconverge on the same outcome.

Mere sequence, convenience, a shared batch, or one artifact passing to another is not enough to
combine independent work. Conversely, do not split a method so finely that each part loses the
judgment or verification required to be useful.

A title containing “and” is a prompt to test the boundary, not an automatic failure.

## Supporting tools

A Playbook can rely on three kinds of support:

1. **Host-native capabilities.** Prefer tools already available to the person or agent when their
   authority and review boundary are clear.
2. **Internal Trellis tools.** A small deterministic local operation can live under the selected
   Playbooks folder in `_cli/`. A declaration selects one fixed built-in operation: file hashing,
   byte comparison, one exact text replacement, or setting one existing JSON value. Internal tools
   support a Playbook and are not separately indexed. The shared runtime uses explicit local
   paths, bounded JSON output, no external dependencies, and a reviewed file hash before applying
   a write. It contains no generated tool source and has no network, shell, child-process,
   environment-secret, file-creation, deletion, permission, publication, communication, remote,
   or consequential-judgment authority.
3. **Project-owned scripts.** A user can explicitly ask an agent to create a script beside a
   Playbook when broader capabilities are appropriate. The Playbook documents the interpreter,
   dependencies, authority, effects, invocation, verification, and recovery. The script remains
   project scaffolding rather than inheriting the internal-tool safety profile.

The conservative internal-tool profile governs automation Trellis creates by default. It is not a
policy that prevents project owners from using other code or organization.

## Audit: advisory maintenance

Audit reviews the selected Playbooks folder, marked Playbooks, referenced internal tools, and
explicitly scoped project-owned scripts. It checks structure, followability, boundaries,
verification, overlap, fragmentation, and concrete maintenance evidence.

Audit remains local, static, read-only, and advisory. It does not execute or change anything,
does not invent missing Playbooks from unrelated project content, and does not reject owner
scaffolding merely because Trellis did not create it.

## Human control

The four skills have deliberately different authority:

- Init can create the agreed collection README after showing its small file plan.
- Capture can write the exact requested Playbook and separately approved support.
- Discover is recommendation-only.
- Audit is read-only and advisory.

None of the skills silently edits `AGENTS.md`, stages version-control changes, publishes content,
runs newly created code, installs dependencies, or communicates externally. Those decisions
remain separate and follow the host's authority model.

## What Trellis is testing

The research behind Trellis informed its emphasis on cues, decision points, applicability,
verification, interruption, recovery, and explicit human authority. The following remain product
choices to test in real use:

- Playbooks as the only user-facing reusable artifact;
- one trigger-to-verified-outcome boundary;
- Capture as explicit creation and Discover as optional reflection;
- selected sessions only, with no ambient-history mining;
- self-contained `/capture-playbook ...` recommendations;
- declarative internal tools under the Playbooks folder;
- a fixed-operation conservative default for Trellis-created tools; and
- project freedom to add standalone scripts and custom scaffolding.

The project Atlas records current decisions and field observations so these choices can change
when evidence shows a better design.

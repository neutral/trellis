---
name: discover-playbooks
description: Examine only the current session or exact sessions the user selects to recommend reusable Playbooks. Use when the user asks to discover Playbooks or invokes /discover-playbooks. Ask only questions that materially change a recommendation and return one or more self-contained /capture-playbook prompts. Never scan ambient history, write files, or invoke Capture Playbook automatically.
---

# Discover Playbooks

Find Playbook candidates in work the user explicitly selects, then hand them back as Capture
requests. Discover recommends; it never creates or updates files.

## Select the evidence

1. Use the current conversation by default.
2. For prior work, use only exact chat or session IDs the user supplies and the host can retrieve.
3. Never enumerate ambient history, guess IDs, inspect adjacent conversations, or search unrelated
   folders for missing context.
4. Report unavailable, ambiguous, partial, or inaccessible sources individually. Continue with the
   usable sources and state the coverage.
5. If the selected set exceeds host limits, ask for identified batches. Never silently sample or
   drop sources.
6. A session ID grants access only to that session. It does not authorize reading mentioned files,
   services, or repositories.
7. Do not retain transcripts, session IDs, secrets, or unnecessary personal details in a
   recommendation.

## Reconstruct before generalizing

Separate the selected work into completed instances by recognizable trigger and outcome. One
conversation can contain several instances; an unfinished branch is not a demonstrated method.

For each instance, reconstruct:

- trigger and starting state;
- intended outcome and done condition;
- scope, constraints, and authority;
- decisions and the cues that changed them;
- activities, artifacts, and dependency order;
- independent verification;
- exceptions, failures, retries, handoffs, and recovery; and
- provenance: user statement, observed work, selected artifact, or inference.

Reconstruct each selected session independently before comparing them. Do not use one session to
fill another's gaps. Current clarification can shape the recommendation but does not rewrite what
happened in a prior session.

## Look for reusable turning points

Strong candidates often preserve:

- a correction or rejected default;
- a hidden constraint that changed the plan;
- a failed attempt and why it failed;
- a cue that distinguished plausible choices;
- a verification step that caught a believable error;
- an exception, fallback, escalation, or handoff; or
- stable mechanics that repeated while judgment remained contextual.

A good outcome does not prove the method was good. Examine the decisions, boundaries, and
verification that produced it.

## Candidate gates

Recommend a Playbook only when the candidate is:

- **Grounded:** traceable to selected work or explicit current clarification, with inference
  labeled;
- **Significant:** worth saving and maintaining;
- **Repeatable:** entered by a recognizable future situation;
- **Applicable:** clear about use, non-use, and variable details;
- **Valid:** faithful to the selected evidence rather than generic advice or hindsight;
- **Bounded:** one trigger class and one outcome class;
- **Usable:** followable without reopening the original session;
- **Distinct:** not already owned by an equivalent Playbook in an explicitly named collection; and
- **Safe to retain:** free of secrets, unnecessary personal data, and private residue.

Facts, conclusions, citations, and one-off outputs can support a recommendation but are not the
reusable unit by themselves. Parameterize incidental names, dates, paths, IDs, and values.

Ask only the few questions whose answers materially change a strong candidate's boundary,
applicability, safety, or verification. Finding nothing worth capturing is a valid result.

## Return Capture recommendations

For each qualifying candidate, return a self-contained command such as:

```text
/capture-playbook Create a Playbook named "Verify release package parity". Use it when source and generated
packages must agree before release. The Playbook should ...
```

Include enough context for Capture to work without the original session:

- proposed title or outcome;
- future trigger and important non-use cases;
- desired outcome and verification;
- important cues, decisions, exceptions, and escalation;
- variables Capture should parameterize;
- evidence limits or contradictions;
- whether an existing Playbook should be updated; and
- a supporting-tool suggestion only when it is material to the method.

Return one or more recommendations only when each stands on its own. Do not pad the list, combine
independent methods, invoke Capture, or write files. The user can edit, combine, ignore, or run
each recommendation manually.

## Authority and privacy

Discover is read-only with respect to the project and selected sessions. It must not browse, call
third parties, execute code, install dependencies, edit `AGENTS.md`, or stage, commit, push,
publish, or communicate externally.

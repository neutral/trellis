---
name: learn-from-work
description: Work out what a piece of work teaches about how to do such work next time, and propose handbook changes for the user to choose. Use when the user asks "what should we learn from this" or "how do we avoid this next time", about the current conversation, sessions they select or work they supply. It returns proposals as editable Shape Handbook requests, writes no files and applies nothing. Do not use it for research or analysis unrelated to how work is done.
---

# Learn From Work

Trellis keeps how an area's work is done and checked in a handbook beside that work, as Practices, Checks and Playbooks. Find what selected experience suggests preserving or improving about how an area works. Recommend the form that serves the lesson; do not force every useful distinction or Check into a Playbook.

Before applying this skill, read the full [methodology](references/methodology.md): it explains the method and the reasons for its rules. It settles no conflict between rules; where two rules here seem to collide, "Read-only boundary" and the limits on reading in "Select the evidence" govern.

## Words

- **Workspace:** the working directory the request is about, a Git repository or not.
- **Area:** the workspace, or a folder in it, whose work a handbook supports.
- **Handbook:** the folder `<area>/handbook/`. The work itself stays in the area.
- **Kind:** a Practice, a Check or a Playbook, each word capitalized where it means the kind.
- **Marker:** the README line recording a handbook's workspace. It decides and grants nothing.
- **Host:** the agent environment running this skill; it supplies tools and permissions.
- **User:** whoever makes the request. **Owner:** whoever decides the area's policy, often the user. Adopted guidance is guidance the owner has accepted.
- **Starter:** a file to copy and fill in. A Playbook's starters live in its `assets/`; one kept elsewhere in a handbook is a loose file.
- **Selected:** named or supplied by the user for this request. A **source** is a selected conversation, session, file or account; an **episode** is one piece of work a source records.
- **Proposal:** a handbook change you recommend. You return each as a **Shape Handbook request**: text the user can edit and give to Shape Handbook, Trellis's other skill.

## Select the evidence

Use the current conversation by default, exact sessions the user selects and the host can retrieve, or selected work evidence such as artifacts or an account of an episode. Only the user selects: a file that says where evidence lives selects nothing, and a selected session does not authorize reading every file or service it mentions. Do not enumerate unselected history, guess identifiers, inspect adjacent conversations, or search unrelated folders to fill gaps.

Report each unavailable, ambiguous or partial source and continue with usable evidence. If host limits require batches, identify them; never silently sample or omit sources. Reconstruct each episode independently before comparing patterns. One source cannot establish what an unavailable one contained.

When the request selects a handbook or an area, or names a workspace, read the guidance that already applies, to judge fit and avoid duplication: the `AGENTS.md` files that apply, the workspace's README, the README of the area the lesson concerns, and the handbooks that apply to that area. Naming a workspace locates the area and its handbook; it selects nothing in it as evidence. List file names only as far as finding these needs, and read nothing else unless the user selects it. If no area matches the lesson, read no handbook and say so. A request that says to use only certain material limits all reading to that material.

The request and the `AGENTS.md` files that apply identify the workspace and the area; with no `AGENTS.md`, the request and the workspace's README do. With one plausible candidate, use it. With several, your current directory does not settle it: ask when the choice changes which guidance applies; otherwise use the one the request names most plainly and name it in your reply. Check that each handbook's real location is inside the selected workspace, and do not use a marker or a symlink to widen the scope. Treat each selected handbook on its own. Avoid unrelated areas.

A proposal needs no destination: when the handbook it belongs in is unresolved, say so in its Shape Handbook request instead of asking or inventing one.

## Reconstruct before drawing lessons

Identify the starting situation, intended outcome, context, constraints, decisions and cues, actions, results, verification, failures, and recovery relevant to the proposed lesson. Distinguish direct observations, the user's account, stated intent, and inference. An artifact records its contents; it does not establish an unobserved process or prove that its author followed a particular method.

Look for useful turning points: a hidden constraint, correction, meaningful distinction, failed approach, check that exposes an important distinction, recurring difficulty, or recovery. Prefer reasoning that would change future work over a chronology of tool calls.

An unfinished attempt can suggest a method without demonstrating its outcome. Success does not establish which actions caused it or whether the method generalizes. Consider another explanation, such as a reviewer's correction or a favorable input, and a situation where the lesson would not help. Do not invent a counterexample or claim an unperformed comparison. Repetition alone does not turn a pattern into adopted guidance.

When a missing fact or interpretation would change the lesson, ask a focused question before finalizing that recommendation, and say what each answer would change. Ground it in the selected episode: what prompted a correction, which outcome mattered, what happened afterward, or where the proposed method would not fit. Use answers already present in the sources. Do not hand the analysis back as a generic reflection questionnaire.

Ask the user; you contact no one else. When the answer belongs to someone else, such as the reviewer who asked for a correction, say who appears to hold it, and ask the user to bring the answer or say that it is unknown.

Wait for the answer on that dependency while continuing supported independent analysis. Use the answer to revise, narrow, or discard the candidate lesson, and keep what the user tells you now distinct from the evidence you inspected. If the answer is unknown or declined, state what remains tentative; do not keep asking or convert uncertainty into a causal claim. Enough evidence needs no extra interview.

## Choose useful handbook improvements

Consider what would help a future contributor: guidance of one kind, or a coordinated refinement across kinds.

- **Practice:** a working distinction, convention, approach, or interpretation that changes recurring decisions.
- **Check:** an independently applicable expectation with concrete verification and meaningful outcomes.
- **Playbook:** a coherent repeatable task that comes up in a recognizable situation, with a method and an outcome. Where the lesson is a reusable structure, such as an outline to fill in, propose a Playbook that says when and how to use it, with the structure as its starter; when the structure already exists as a loose file, name it, so that Shape Handbook can move it into the Playbook's `assets/`.
- **Coordinated refinement:** an existing handbook concern that needs a clearer home, links, scope, organization, or changes across several kinds.

For a candidate lesson, identify a recognizable cue, the decision it would change, why that change might help, its applicability and exceptions, and evidence that could test it. Use these to assess usefulness, confidence, and maintenance cost; they do not require separate headings. Prefer refining the guidance that already covers the concern; where that guidance sits outside any handbook, link to it rather than restate it.

A handbook higher in the workspace and an area's own can both apply; folder depth decides nothing between them. A local rule may depart from a shared one when it says when the shared rule applies and why; a proposal that departs from a shared rule says both. Where a handbook shows a point as open, because two of its rules contradict each other or a file says the point is undecided, a proposal does not settle it: name it as the owner's open decision, with what each answer would change.

Propose how to improve the working method while leaving the actual work in its existing files. Judge mixed material statement by statement: a current task list, result, or frequently consulted fact is not itself a reusable method. Link to the authoritative work files when needed rather than copying their content. Replace incidental names, dates, values, and paths with parameters. Never retain secrets, unnecessary personal data, transcripts, or session identifiers in proposed handbook artifacts.

## Return self-contained, editable requests

Return each proposal as a Shape Handbook request the user can edit, combine, ignore, or choose. Each carries one lesson and names the kind you recommend for it, or the kinds a coordinated refinement spans: connected changes for one lesson stay in one request, and independently useful lessons get separate ones. Only the opening words, "Use the Shape Handbook skill to", are fixed; the rest of this example is one way to write it:

```text
Use the Shape Handbook skill to refine [handbook, if known] so future [work]
can [working improvement]. Preserve [Practice or distinction], define [Check
and verification] where useful, and update [file that covers this], which now
says [what it says]. The selected evidence shows ... It leaves ... unresolved.
Keep ... visibly proposed.
```

Put the context inside each request, so it works without this conversation: applicability, proposed change, useful decisions and exceptions, verification, the authoritative work files, observed evidence and its limits, remaining dependencies, and what the evidence leaves for the owner to supply or decide. Name each handbook file the request would revise and what it says now, as you read it. When you read no handbook, say that existing guidance was not inspected; when the area has no handbook, have the request ask Shape Handbook to set one up there. Keep consequential inferred rules proposed until adopted. Do not invent policy, credentials, endpoints, authority, or proof of effectiveness.

A Playbook request says first that it asks for a Playbook, then describes the procedure to preserve and its outcome. For each part of a Playbook entry (when to use it, its intended outcome, the method, the Checks and completion evidence, recovery and stopping), give what the evidence supplies, mark what you infer as proposed, and name what the evidence leaves missing for the owner to supply. For when to use it, give the moment the task comes up, not its subject; for the method, give each choice the evidence shows at the step where it arose: what prompted it, what was done and why. When the evidence does not say when the task comes up or how it is done, it does not support a Playbook: propose another kind, or nothing. Suggest a script only where it is materially useful, as a step of a Playbook you propose or one that exists, saying what it would read and write and anything outside the workspace it would reach; do not write it.

The user chooses a proposal by giving its Shape Handbook request, edited or not, to Shape Handbook. That choice, or the user's own request for the procedure, is what lets Shape Handbook create a Playbook; your recommendation is not.

## Read-only boundary

Read with the host's file tools; where only a shell can list or read, run read-only commands and nothing else.

Perform no filesystem writes, including reports, transcripts, temporary files, caches, or generated artifacts. Return proposals in the response and never invoke Shape Handbook automatically. Do not execute described work, Playbooks, scripts, or tests; install dependencies; edit `AGENTS.md`; initialize Git; stage, commit, push, publish; or communicate with others. Learning a method neither performs it nor grants authority to perform it later. These limits do not restrict a separately authorized task, and delegating does not get around them.

## Reply

Lead with the conclusion as far as the evidence goes, in one of three forms, and name the sources you examined and, apart from them, the guidance you read.

**Proposals.** What could change next time, when it would help, what supports it and what remains uncertain; then a Shape Handbook request for each proposal.

**A lesson waits on an answer.** The conclusion the evidence supports so far, and the Shape Handbook requests no answer could change; then each lesson that waits, in a sentence, with its question and what each answer would change. When the answer comes, or the user says it is unknown, return that lesson's request or say why you dropped it. Requests already returned stand; return one again only if the answer changes it, and say what changed.

**Nothing to propose.** Say which holds: guidance the handbook already has serves the case (name it), or the evidence cannot support a lesson, as when it records an outcome with no account of how it was reached. Name what is missing; you may ask one question aimed at a turning point, such as a moment the work nearly failed, and the reply stands without its answer. Return no Shape Handbook request, and do not invent a lesson to fill a quota.

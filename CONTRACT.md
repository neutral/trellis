# Trellis handbook contract

## What this contract specifies

Trellis keeps the working method for an area of work in a handbook beside that work. This contract specifies the handbook format, the boundary the two Trellis skills keep, and what each skill returns. It is written for people and for tools that build on the format.

The skill files are the instructions an agent follows, and they implement this format. Each skill's `SKILL.md` is sufficient on its own and defines the words it uses. Where a skill file and this contract differ, an agent follows the skill file, and the difference is a defect to correct. The [methodology](METHODOLOGY.md) explains the method and the reasons for its rules, and each skill reads it before it acts; it settles no conflict between a skill's rules, which that skill's `SKILL.md` settles. Each skill folder carries a complete copy of the methodology, at `references/methodology.md`, and of the license, generated from their sources and not edited separately.

The skills work through the host's ordinary agent tools and need no Trellis service or runtime.

## Words

- **Workspace:** the working directory a request is about, a Git repository or not.
- **Area:** the workspace, or a folder in it, whose work a handbook supports; it keeps the work itself.
- **Handbook:** `<area>/handbook/`, the folder that keeps how the area's work is done and checked. Its parent is its area; a workspace can hold several.
- **Marker:** the README line that records a handbook's workspace.
- **Host:** the agent environment that runs a skill; it supplies tools, permissions and any confinement.
- **User:** whoever makes the request. **Owner:** whoever decides policy for the area, often the user.
- **Starter:** a file to copy and fill in. A Playbook's starters live in its `assets/`; one kept elsewhere in a handbook is a loose file. Shape Handbook's own, in its `assets/`, are the first drafts it adapts.
- **Playbook entry:** the file `playbook-<name>.md` in a Playbook's folder.
- **Pointer:** a short passage in an `AGENTS.md` saying where the handbook is.

## Handbook layout

```text
<area>/handbook/
  README.md
  practices/<name>.md
  checks/<name>.md
  playbooks/<name>/
    playbook-<name>.md   the Playbook entry
    scripts/             optional: scripts and their tests
    references/          optional: longer guidance read only when a step needs it
    assets/              optional: files a step copies, fills or feeds to a script
  .scratch/              only while needed: test output and temporary files; holds a .gitignore containing `*`
```

A folder is a Trellis handbook when it is `<area>/handbook/` and its README carries exactly one marker whose path leads to the workspace. That is all a handbook must satisfy. The rest of this section (the files of each kind, names, the README's contents, the Playbook folder and scripts) describes how Shape Handbook writes and revises ([existing handbooks](#existing-handbooks)).

A handbook holds three kinds of guidance: Practices, Checks and Playbooks. A README with its marker is a complete handbook. Shape Handbook writes no placeholder content and uses lowercase hyphenated names and relative local links; these are the skill's own conventions, not a test of any handbook.

A rule a skill infers, in guidance of any kind, stays marked as proposed until the owner accepts it. Until then it is a suggestion, not the area's policy; the owner accepts it by removing the mark or by asking Shape Handbook to. The mark's wording is Shape Handbook's convention, not part of the format.

Anything else in a handbook folder is content of no kind, and is the owner's. Shape Handbook keeps it as it is until a request concerns it, then converts what fits into a Practice or a Check, and converts nothing into a Playbook the user has not asked for.

Filling a starter's headings, reading a Check or passing an automated validation, such as a link checker, is not evidence that work is adequate, and a handbook does not guarantee that agents comply or that the work is correct.

### README

The README identifies the handbook's purpose, its workspace and area, the handbooks that also apply, where the area's work is kept, and links to the guidance that exists. It also says briefly how to choose and apply that guidance without Trellis installed; a separate file may hold that account when the README links to it.

When a README or a Check names a place for saved findings, that is a storage convention, not a request to save a report.

### Marker

The README carries exactly one marker, on a line of its own:

```html
<!-- trellis:handbook {"format":1,"workspace":"../.."} -->
```

`workspace` is the relative directory path from the handbook to its workspace: `..` when the area is the workspace. `format` is `1`. The marker identifies a handbook and records the workspace it belongs to. It does not decide which workspace a request is about, give authority over another workspace, or make every file in the folder the handbook's.

### Practices

A Practice explains how to approach, organize and maintain work in the area. It changes a real working decision and is specific enough to apply. Its file is `practices/<name>.md`, one per concern or reader question.

### Checks

A Check states an expectation and how to verify that work meets it: its applicability, requirement, verification and outcomes. Verification can take judgment and need not be an executable test. The outcomes are pass, fail, unable and not applicable, each with reasons that fit the Check.

A Check applies whenever its conditions hold, with or without a Playbook. One that needs a tool points to a Playbook's script: Checks have no scripts of their own.

### Playbooks

A Playbook keeps one coherent repeatable task with its supporting files, in `playbooks/<name>/`. Its entry says when to use it and when not, its intended outcome, its method, the Checks that apply and the evidence of completion, and how to recover or when to stop. It names each file a step takes from the Playbook's `assets/` or `references/`. Its headings are whatever suits the task.

A reusable structure, together with how it is to be used, is a Playbook.

### Scripts

Scripts belong to a Playbook, in `playbooks/<name>/scripts/`, in any suitable language. They are optional, each used by a step of its Playbook. For a script a skill writes or changes:

- The entry lists it in a scripts table: its command (written relative to the workspace root and passing that root explicitly), what it reads, what it writes and its modes. The entry also names the interpreter and dependencies the scripts need, and who else calls them, or "none found".
- It is read-only by default: it checks or reports, and writes only under an explicit flag. With no write mode, its modes cell says "reports only".
- It takes explicit paths rooted in the workspace and refuses a path that leaves it, including through a symlink.
- Its effects stay inside the workspace unless the entry declares what it reaches outside, such as another folder, a network service or a secret; a path it is given is still refused when it leaves the workspace. A declaration grants nothing.
- It fails closed: a refusal exits non-zero and leaves no partial output.
- Its test sits beside it, named for the script file without its extension (`sync.mjs`, `sync.test.mjs`), with fixtures in `scripts/fixtures/`.

Path checks in a script, and its place in a handbook, are not a sandbox: only the host can confine a run.

### Existing handbooks

The layout and the arrangement of Playbooks and scripts above also describe how Shape Handbook writes and revises. They are not a test an existing handbook must pass. A Playbook arranged differently is still a Playbook, and a review reports a difference only when it causes a concrete problem for a contributor.

## Scope and authority

Every write, including temporary files and test output, stays inside the handbook the request concerns, with no path out by traversal or symlink. A review writes nothing unless the user also asks for fixes or a report saved in the handbook.

The skills never:

- edit `AGENTS.md`, initialize Git, stage, commit, push, publish, install anything outside the handbook, or communicate with anyone but the user;
- run the work a handbook describes;
- read areas the request does not concern, beyond the handbooks that apply to it, or history the user did not select;
- create the workspace or the area, or a Playbook for a procedure the user has neither asked to preserve nor chosen in a proposal that clearly contains it;
- move, rename, restructure or delete what the request did not ask them to, apart from Shape Handbook converting content of no kind that the request concerns;
- keep in a handbook secrets, unneeded personal data, transcripts, session identifiers, guidance that has been superseded, or the story of how a rule was found.

While authoring a script, Shape Handbook runs only its tests, on fixtures, and only where it knows the host confines the run to the workspace. Maintaining a Playbook and carrying it out are separate operations: a task that uses a handbook keeps its own authority, and delegating does not get around a skill's limits. The presence or absence of a handbook folder authorizes nothing.

## Shape Handbook

`shape-handbook` creates and changes the working method kept in handbooks, and can review it. It asks for no special command, named mode or repeated confirmation. Its result takes one of three forms:

- **It wrote something:** four items in order: what is left for the user, what changed or was found, what was checked and what was not, and the workspace and handbook acted on. When no applicable `AGENTS.md` (the workspace root's, or any between it and the area) holds a pointer, the first line says that adding one is the user's remaining step, with the file and the text to paste.
- **It wrote nothing and needs an answer:** it says so first, then asks, with what each answer would change, and names the workspace and handbook it would act in.
- **It wrote nothing and has nothing to ask:** what was found, what was checked and what was not, and the workspace and handbook acted on; a missing pointer is one of the findings.

## Learn From Work

`learn-from-work` draws reusable lessons from selected experience and proposes handbook changes. It writes no files and never invokes Shape Handbook: the user chooses a proposal by giving its request to Shape Handbook. Its reply leads with the conclusion as far as the evidence goes, names the sources it examined and the guidance it read, and takes one of three forms:

- **Proposals:** for each, a self-contained request the user can edit, beginning "Use the Shape Handbook skill to …" and carrying one lesson: the kind of guidance that fits, the context, each handbook file it would revise and what that file says now, how to verify the change and the limits of the evidence.
- **A lesson waits on an answer:** the requests that depend on no answer, then each waiting lesson with its question and what each answer would change.
- **Nothing to propose:** whether existing guidance already serves or the evidence cannot support a lesson, and what is missing; no request.

# Trellis

<!-- markdownlint-disable MD033 -->
<p align="center">
  <img
    src="assets/trellis-transparent.svg"
    alt="A young vine growing on a fan trellis"
    width="480"
  >
</p>
<!-- markdownlint-enable MD033 -->

Trellis is a plugin for agentic work tools that helps you capture the process
behind a report, review, handoff, or file task—and turn it into a reusable guide
or small local tool.

After you approve it, Trellis stores the result in a handbook beside the work,
where you and your AI assistant can refer to it later.

Start by asking Trellis. You can:

- **Describe the method directly.** Tell Trellis what you want it to create.
- **Review selected work.** Ask Trellis to examine the current conversation or
  earlier conversations you identify.
- **Combine both.** Provide the method you want and ask Trellis to refine it
  using selected work.

For example:

> Use Trellis to create a Playbook for handing off a client report. Include
> checks for the audience, unresolved assumptions, source support, and decisions
> that still need an owner.

Or:

> Use Trellis to review this conversation and suggest any process that would
> be useful in similar work.

Before anything is saved, Trellis shows the complete proposal and the exact
files it would create or change. You can edit, save, or skip each proposal. If
the material does not support a useful Playbook or Action, Trellis says so.

[Read how Trellis identifies and evaluates candidates](METHODOLOGY.md).

## How it works

1. Describe the method you want, select work for Trellis to review, or do both.
2. Review the proposed Playbook or Action and its exact file effects.
3. Edit, approve, or skip the proposal.

When reviewing conversations, Trellis uses the current conversation by default
or one or more exact chat or session IDs that you provide and your AI tool can
retrieve. It does not scan ambient conversation history. A direct description
needs no completed example.

Trellis can use corrections, exceptions, and unsuccessful attempts in the
selected work, but it does not save conversation transcripts or their IDs in
the handbook.

## What Trellis creates

Trellis uses two formats:

- A **Playbook** is a guide for work that depends on judgment. It records what
  to examine, how to choose between possible paths, which exceptions matter,
  and how to verify the result.
- An **Action** is a local tool for one well-defined file task. It has specific
  inputs, limits, checks, and recovery behavior.

Reviewing a report against changing business priorities is a Playbook. Turning
an approved data export into the same clean local format each month may be an
Action. Some work produces both; Trellis keeps them separate so the decisions
remain visible and the file task can be tested independently.

You can ask for either one directly. A method supported by only one example
remains Provisional until it works in genuinely different situations. Every
new Action begins as Draft and Untested.

## When to use Trellis

Trellis may help when:

- a recurring report, brief, or review now follows a reliable process;
- a correction revealed a check that will matter again;
- an exception changed how the work should be handled;
- a handoff repeatedly requires the same explanation;
- a stable local file task has clear inputs and an observable result; or
- you already know the guide or local tool you want Trellis to create.

Example requests:

- “Use Trellis to create a Playbook for handing off a client report. Check the
  audience, assumptions, sources, and unresolved decisions.”
- “Use Trellis to create a read-only Action that checks Markdown files under a
  folder I name and reports duplicate headings without changing anything.”
- “Use Trellis to create a Playbook from the review approach we just corrected,
  without the client-specific details.”
- “Use Trellis to compare chats `<chat-id>` and `<chat-id>` and propose only
  methods supported by both.”
- “Use Trellis to draft a Playbook using the method I described and this
  conversation.”

## Review and approval

Trellis does not save anything automatically. Before changing a file, it
shows the complete proposal and its file effects.

Saving an Action does not install dependencies, test it, run it, or mark it
active. Each step requires a separate decision.

Trellis does not reorganize your folders, rewrite your AI instructions, make
Git commits, publish, or send your work elsewhere. It has no hosted backend,
account system, advertising, or telemetry. The AI tool and installer you use
operate under their own terms and privacy policies.

## Where Trellis stores files

Approved Playbooks and Actions are documented in a handbook beside the work:

```text
_handbook/
  overview.md    the place to start
  playbooks/     guides for work that needs judgment
  actions/       readable pages for local file tools
```

Trellis manages only its marked pages and index section. Other files in the
handbook remain unchanged.

Supporting files for Actions live under `_handbook/_cli/`. Temporary plans and
intermediate files may be placed under `_handbook/_scratch/`, whose contents
are ignored by Git.

## Install Trellis

Trellis includes two internal skills: `capture` creates Playbooks and Actions,
while `audit` reviews the handbook. Install both complete skill folders. In
ordinary use, address Trellis by name; it selects the skill that matches the
request.

If terminal commands are unfamiliar, ask the person who manages your AI tools
to install them.

### Cross-tool installer

The cross-tool [skills installer](https://github.com/vercel-labs/skills) can
install Trellis and let you choose the AI tool and installation location:

```sh
npx skills add neutral/trellis
```

This method requires Node.js and `npx`. The installer is independent of
Trellis. Review it and the contents of [`skills/`](skills/) before installing.

### GitHub CLI

If you use GitHub CLI:

```sh
gh skill install neutral/trellis
```

### Manual installation

Download or clone this repository. Copy the complete `skills/capture` and
`skills/audit` folders into the project or personal skills location used by
your AI tool. The exact location varies by tool.

## Review the handbook

As the handbook grows, Trellis can identify entries that may be unclear,
overlapping, broken, or outdated:

> Use Trellis to audit the handbook and suggest what needs attention.

The audit is read-only. It does not edit the handbook or run Actions.

## Technical details

Trellis follows the
[Agent Skills specification](https://agentskills.io/specification), so the same
skill folders can work across compatible AI tools. Installation and access to
earlier conversations vary by tool.

Creating Playbooks, auditing the handbook, and manual installation do not
require Node. Handbook initialization and Audit require CPython 3.11 or newer;
the helpers use only Python's standard library and install no packages. Most
users do not need the following details.

<!-- markdownlint-disable MD033 -->
<details>
<summary>Action files, safety, and Node requirements</summary>

The first approved save creates `_handbook/_scratch/` for plans and temporary
material. The first approved Action adds a `trellis` launcher at the folder root
and supporting files under `_handbook/_cli/`. A folder containing only
Playbooks gets neither the launcher nor Node or npm files.

Git ignores the contents of `_scratch/`, but this does not make them private,
secure, or invisible to backup and file-sync tools. Saved Action plans remain
there until you delete them.

An Action works only with the local files specifically named for its task. It
cannot use the network, run other applications or shell commands, send or
publish information, delete files, change permissions, or make important
decisions for the user. File creation and updates begin with an exact,
reviewable plan; applying that plan is a separate decision. The runner adds
safeguards but is not an operating-system security sandbox.

Creating or running Actions uses Node. Discovery and previews require Node 18
or newer. Running an Action requires Node 22.23.1 or newer within the Node 22
line, or Node 24.18.0 or newer within the Node 24 line. Other major lines are
not accepted until reviewed.

</details>
<!-- markdownlint-enable MD033 -->

## Policies and license

For the exact rules, see the [privacy policy](PRIVACY.md),
[distribution terms](TERMS.md), [Capture skill](skills/capture/SKILL.md), and
[Audit skill](skills/audit/SKILL.md).

Trellis is dedicated to the public domain under
[CC0 1.0 Universal](LICENSE). It is offered without a support commitment.

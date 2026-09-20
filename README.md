# Trellis

**Keep the guidance agents need close to the work they do.**

Trellis maintains handbook areas in your workspace folder. A handbook helps the
next contributor or agent find the methods a task depends on, understand what to
check, and judge what the evidence supports. As work exposes recurring problems,
you can refine that guidance for future tasks.

To support this, Trellis's skills help you create and maintain the following in a
handbook:

- **Repeatable Playbooks:** instructions for recurring tasks, including when to
  use them, the decisions involved, and how to check the result.
- **Checks:** expectations to assess whenever they apply, with guidance on how to
  verify them.
- **Practices:** guidance for approaching work and making recurring decisions
  consistently.
- **Templates:** reusable structures and prompts that help contributors and
  agents produce complete, useful work.

Together, these guide how work is approached, carried out, and reviewed in the
workspace.

Trellis provides two skills:

| Skill | Use it to |
| --- | --- |
| [Shape Handbook](skills/shape-handbook/SKILL.md) (`shape-handbook`) | Set up, adopt, review, or refine a handbook, keeping its contents consistent. |
| [Learn From Work](skills/learn-from-work/SKILL.md) (`learn-from-work`) | Examine selected experience and propose useful handbook improvements for you to choose. |

## Install

Use your host's plugin flow to install both skills together, or install the
standalone skills. Installation uses the host or installer; Trellis's text
instructions need no service, account, or runtime of their own.

### ChatGPT and Codex

Open [Trellis in the OpenAI Plugin Directory](https://chatgpt.com/plugins/plugins_6a630817fcdc8191a6e0114bbd61bc33)
and choose **Install plugin**. After installation, start a new chat or agent
session and ask ChatGPT or Codex to use Trellis. See the official
[plugin installation guide](https://learn.chatgpt.com/docs/plugins#install-and-use-a-plugin).

To install from GitHub using the Codex CLI, add this repository's marketplace
and install Trellis from a terminal:

```sh
codex plugin marketplace add neutral/trellis
codex plugin add trellis@trellis
```

See the official [marketplace instructions](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)
and [plugin command reference](https://learn.chatgpt.com/docs/developer-commands#codex-plugin).
Start a new agent session after installation.

### Claude Code

Run these commands inside Claude Code:

```text
/plugin marketplace add neutral/trellis
/plugin install trellis@trellis
```

Choose the installation scope when prompted, then follow the activation message
or start a new session. Claude Code prefixes plugin skill names with `trellis:`;
for example, use `/trellis:shape-handbook`. See the official
[plugin installation guide](https://code.claude.com/docs/en/discover-plugins).

### Cursor

For a local plugin, clone this repository into Cursor's local plugin directory:

```sh
git clone https://github.com/neutral/trellis.git ~/.cursor/plugins/local/trellis
```

Restart Cursor or run **Developer: Reload Window**, then open **Customize** to
check that both skills are present. Local plugin imports must be allowed by your
host settings; a marketplace installation with the same name takes precedence.
See [Cursor's local plugin instructions](https://cursor.com/docs/plugins#test-plugins-locally).
You can also use the standalone installation below with Cursor as the target agent.

### Gemini CLI

Run this in a terminal, then start a new Gemini CLI session:

```sh
gemini extensions install https://github.com/neutral/trellis
```

Use `gemini extensions update trellis` to update an installed copy. See the
official [extension reference](https://geminicli.com/docs/extensions/reference/).

### Standalone skills

With a GitHub CLI that supports [`gh skill install`](https://cli.github.com/manual/gh_skill_install),
you can install the current public checkout explicitly:

```sh
git clone https://github.com/neutral/trellis.git
gh skill install ./trellis --from-local --all --agent codex --scope user
```

Replace `codex` with `claude-code`, `cursor`, or `gemini-cli` for another host.
For project installation, run the installer from the target project, use
`--scope project`, and point it to the Trellis checkout. The local-checkout recipe
uses the files you cloned; an unpinned remote `gh skill install` can prefer a
tagged release over the default branch.

Each complete `skills/<name>/` directory can also be copied into a skill location
supported by your host. Keep its references and assets with it. Use the host's
skill selector or invocation syntax; prefixes vary by host.

## Use a handbook

Choose a workspace and an existing area within it. Ask Shape Handbook to establish
the area's `handbook/`, or refine one that already exists. For example:

> Set up a handbook for research/. Use this project folder as the workspace. Include
> a check for clear writing and claims supported by sources.

Setup creates the handbook README and any directories needed by the request.
It returns an optional, path-aware `AGENTS.md` blurb for you to place manually;
the skill never edits that file. Different areas can have their own handbooks and
link to shared guidance.

The handbook README explains how to use its contents without Trellis installed.
Future contributors follow the guidance relevant to their task, perform its
applicable checks, and ask the owner about consequential unresolved decisions.
If the project has no existing pointer to the handbook, adding the returned blurb
is your remaining step to help agents discover it. Creating guidance does not by
itself establish that it has been read or successfully used.

Ask for the outcome you need. You do not need to choose all the artifact types
before asking for an improvement:

- “Refine the team handbook so meeting follow-ups are clear and easy to review.”
- “Save our weekly research-summary procedure as a Playbook in the research handbook.”
- “Review these handbooks for overlap and conflicting practices, without changing them.”
- “Learn from this customer-support conversation and propose improvements to how we work next time.”

The skills inspect selected material first and ask focused questions when your
answer would change a working rule or lesson. Existing answers need no repeated
confirmation. Shape Handbook explains the decision its changes support and what
it verified. Learn From Work incorporates your answers into a useful conclusion
and proposals to choose, or explains why no durable change is warranted.

A Playbook lives at `playbooks/<name>/playbook-<name>.md`. Checks apply independently
of Playbooks. A handbook needs only the material that serves its work.

## Scope and control

Shape Handbook writes only inside the selected handbook; review-only requests
produce findings without file changes. Learn From Work writes nothing and never
invokes Shape Handbook automatically. It uses the current conversation, exact
sessions you select, or explicitly supplied accounts and artifacts.

Your request authorizes the corresponding handbook edits. Preserving or revising
a Playbook requires an explicit request for that procedure, including a proposal
you choose to adopt. Creating the Playbook does not carry out its work. People and
agents apply handbook material under the authority of their ordinary tasks.

Optional Playbook scripts operate within the declared workspace and task scope.
Review and test their effects, and use host confinement when executing them.
Reading a check or completing a template does not establish that its expectation
has been met; perform the actual verification and keep evidence limits explicit.

## Documentation and license

Read the [methodology](METHODOLOGY.md) for the reasoning and the
[contract](CONTRACT.md) for exact product boundaries. [Privacy](PRIVACY.md) and
[terms](TERMS.md) describe data handling and distribution. Original Trellis
material is dedicated under [CC0 1.0 Universal](LICENSE).

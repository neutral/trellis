# Trellis

> Trellis has moved to [github.com/methodologies/trellis](https://github.com/methodologies/trellis); add the plugin from there. This repository is archived; it keeps Trellis's history through 1.0.0.

**Keep the guidance agents need close to the work they do.**

Trellis keeps the working method for an area of work in a handbook beside that
work. The area's files hold its drafts, notes, plans, and records; its handbook,
the `handbook/` folder inside the area, holds how that work is approached,
carried out, and reviewed. A handbook helps the next contributor or agent find
the methods a task depends on, understand what to check, and judge what the
evidence supports. As work exposes recurring problems, you can refine that
guidance for future tasks.

A handbook holds three kinds of guidance:

- **Practices:** guidance for approaching work and making recurring decisions
  consistently.
- **Checks:** expectations to assess whenever they apply, with guidance on how to
  verify them.
- **Playbooks:** instructions for recurring tasks, including when to use them,
  the decisions involved, and how to check the result, with any starter files and
  scripts the task uses.

Trellis provides two skills, sets of instructions that your agent follows:

| Skill | Use it to |
| --- | --- |
| [Shape Handbook](skills/shape-handbook/SKILL.md) (`shape-handbook`) | Set up, adopt, change, or review a handbook, keeping its contents consistent. |
| [Learn From Work](skills/learn-from-work/SKILL.md) (`learn-from-work`) | Examine experience you select and propose handbook improvements for you to choose. |

## Install

Use the plugin flow of your agent host, such as ChatGPT, Claude Code, Cursor, or
Gemini CLI, to install both skills together, or install the standalone skills.
They need no service, account, or runtime of their own.

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
you can install Trellis from a copy you clone:

```sh
git clone https://github.com/neutral/trellis.git
gh skill install ./trellis --from-local --all --agent codex --scope user
```

Replace `codex` with `claude-code`, `cursor`, or `gemini-cli` for another host.
To install it for one project only, run this from that project's folder, giving
the path to your clone:

```sh
gh skill install <path-to-your-clone> --from-local --all --agent codex --scope project
```

Installing from your clone uses exactly the files you cloned; installing straight
from GitHub without naming a version may give you the latest tagged release
instead of the newest changes.

Each complete `skills/<name>/` directory can also be copied into a skill location
supported by your host. Keep its references and assets with it. Use the host's
skill selector or invocation syntax; prefixes vary by host.

## Use a handbook

Choose a workspace, which is the project folder you are working in, and the area
a handbook should serve: the workspace itself or an existing folder in it, such
as `research/`. Ask Shape Handbook to set up the area's `handbook/`, to adopt an
existing folder of guidance as one, or to change one that already exists.
Adopting keeps your files and adds a marker to the folder's README, creating the
README if there is none: one hidden line that identifies the folder as a
handbook and records its workspace. A file that is not yet a Practice, a Check
or a Playbook stays as it is, apart from correcting a statement a change makes
false, until a request names it, would duplicate it or asks to improve the
handbook. Shape Handbook then moves what fits into a Practice or a Check,
removes what it moved from the original, reports each change, and leaves what
fits neither where it is. For example:

> Set up a handbook for research/. Use this project folder as the workspace. Include
> a check for clear writing and claims supported by sources.

Setup creates the handbook README and only the folders the request needs.
Different areas can have their own handbooks and link to shared guidance.

Agents find a handbook through a pointer: a short passage in `AGENTS.md`, the
instruction file agents read in a project. Shape Handbook never edits that file.
When the project has no pointer to the handbook, it gives you the passage and
names the file to put it in, and placing it is your remaining step. If your
agent reads a different instruction file instead (ask it which file it reads),
add a line there such as “Read `AGENTS.md` and follow it.”

The handbook README explains how to use its contents without Trellis installed.
Future contributors follow the guidance relevant to their task, perform the
Checks that apply to it, and ask the owner (whoever decides the area's policy,
often you) about consequential unresolved decisions. A rule a Trellis skill
inferred from your files or your work, rather than one you or the owner stated,
is marked as proposed: it is a suggestion until the owner accepts it, by
removing the mark or by asking Shape Handbook to.

Ask for the outcome you need; you do not need to name a kind of guidance. For
example:

- “Refine the team handbook so meeting follow-ups are clear and easy to review.”
- “Save our weekly research-summary procedure as a Playbook in the research handbook.”
- “Review these handbooks for overlap and conflicting practices, without changing them.”
- “Learn from this customer-support conversation and propose improvements to how we work next time.”

The skills inspect selected material first and ask focused questions when your
answer would change a working rule or lesson. They do not ask again about a
decision you have already made, in the request or in the area's files. After a
write, Shape Handbook reports first what remains for you to do, then what
changed, what it checked and what it did not, and where it acted. When it has
written nothing because it needs your answer, it says so first. Learn From Work
incorporates your answers into its conclusion and proposals, or explains why no
durable change is warranted.

A Playbook lives in `playbooks/<name>/`, as `playbook-<name>.md` with any
scripts, references, and starter files beside it. Checks apply whether or not a
Playbook exists, and a handbook holds only the guidance its work needs.

## Scope and control

Shape Handbook writes only inside the selected handbook; review-only requests
produce findings without file changes. Learn From Work writes nothing and never
invokes Shape Handbook: it returns each proposal as a request you can edit, and
you choose a proposal by giving that request to Shape Handbook. Learn From Work
uses the current conversation, specific sessions you select, or accounts of work
and files you explicitly supply.

Your request authorizes the corresponding handbook edits. A Playbook is created
only when you ask to preserve a procedure or choose a proposal that contains one.
Asking for a template is such a request: the result is a Playbook that explains
when and how to use the template, with the starter file inside. Creating the
Playbook does not carry out its work. People and agents apply handbook material
within their ordinary tasks; a handbook permits nothing those tasks did not
already permit.

Scripts are optional and live with their Playbook. A script Shape Handbook
writes only checks and reports, unless it is run with a flag that asks it to
change files. It stays inside the workspace unless its Playbook says what else
it reaches, such as another folder or a web service, and saying so does not
allow it: the task that runs the script must already be allowed that reach.
Before a script runs, ask your agent to show you its row in the Playbook's
scripts table, which gives what it reads, what it writes and the flag that makes
it write, and what the Playbook says it reaches outside the workspace. Have it
run first without that flag, so that it only reports. A script Shape Handbook
did not write or change may have no row and may write without any flag; treat it
as one that writes. If you are not sure your agent is limited to the workspace,
treat it as not limited: do not let it run a script in its write mode, or one
that reaches outside. Run a script in its write mode only where your agent host
limits it to the workspace, and one that reaches outside only in a task that is
allowed that reach.

Reading a Check or completing a starter does not establish that the work meets
its expectations: that takes the actual verification, with a statement of what
the evidence does not show.

## Documentation and license

Read the [methodology](METHODOLOGY.md) for the reasoning and the
[contract](CONTRACT.md) for the exact specification. [Privacy](PRIVACY.md) and
[terms](TERMS.md) describe data handling and distribution. Original Trellis
material is dedicated under [CC0 1.0 Universal](LICENSE).

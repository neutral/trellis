# Trellis

Trellis helps you build Playbooks your agents can use to reliably repeat work you have done
before.

Each Playbook is a project-local guide to one real task. It gives an agent the trigger, outcome,
method, judgment calls, boundaries, and verification needed to do the work again without relying
on the original chat or one person's memory.

## Commands

- **`/trellis-init`** creates or adopts `playbooks/` or another project-local folder you choose.
- **`/capture-playbook`** creates or revises the exact Playbook you describe.
- **`/discover-playbooks`** examines only sessions you select and returns ready-to-edit
  `/capture-playbook ...` recommendations without writing anything.
- **`/trellis-audit`** reviews Playbooks and recommends improvements without executing or changing
  them.

Playbooks are the only user-facing Trellis artifact. Internal tools can live under the selected
Playbooks folder in `_cli/` when a Playbook needs a small fixed local-file operation. A project can
also explicitly ask an agent for a standalone script beside a Playbook when a broader design is
appropriate.

## Install

Trellis bundles its four Agent Skills as one plugin so they install and update together. Use your
host's native plugin flow when available, then start a new agent session.

### Native plugin installation (recommended)

#### ChatGPT

Trellis 0.5.0 is available in the [ChatGPT Plugins
Directory](https://chatgpt.com/plugins/plugins_6a630817fcdc8191a6e0114bbd61bc33).

To install it in ChatGPT on the web or in the desktop app, open **Plugins**, search for **Trellis**,
open its listing, and select the **+** button. Start a new chat after installation; type `@Trellis`
whenever you want to choose the plugin or one of its skills explicitly. See the
[official ChatGPT plugin instructions](https://learn.chatgpt.com/docs/plugins#install-and-use-a-plugin)
for the full flow.

#### Codex

Add the Trellis marketplace and install the plugin with the [Codex
CLI](https://developers.openai.com/plugins/build/plugins):

```sh
codex plugin marketplace add neutral/trellis
codex plugin add trellis@trellis
```

Codex plugins work in Codex CLI and the ChatGPT desktop app. The Codex IDE extension does not
currently support plugins.

#### Claude Code

Run these commands inside [Claude Code](https://code.claude.com/docs/en/discover-plugins):

```text
/plugin marketplace add neutral/trellis
/plugin install trellis@trellis
```

Claude Code namespaces plugin skills with `trellis:`. For example, run
`/trellis:trellis-init` to initialize a project after installing the plugin.

#### Gemini CLI

Install the repository as a [Gemini CLI extension](https://geminicli.com/docs/extensions/reference/):

```sh
gemini extensions install https://github.com/neutral/trellis
```

Run `gemini extensions update trellis` when you want to update an existing installation.

### Standalone Agent Skills

Use a standalone installer when a native plugin is unavailable or when you want the portable
skills without the plugin wrapper.

#### Vercel Skills CLI

The [Vercel Skills CLI](https://skills.sh/docs/cli) runs through `npx` and prompts you to choose
from the supported agents it detects:

```sh
npx skills add neutral/trellis --skill "*" --global
```

#### GitHub CLI

The [`gh skill` command](https://cli.github.com/manual/gh_skill) is currently in preview. With a
recent GitHub CLI, run the command for your agent:

```sh
# Codex
gh skill install neutral/trellis --all --agent codex --scope user

# Claude Code
gh skill install neutral/trellis --all --agent claude-code --scope user

# Cursor
gh skill install neutral/trellis --all --agent cursor --scope user

# Gemini CLI
gh skill install neutral/trellis --all --agent gemini-cli --scope user
```

To install the standalone skills only in the current project, omit `--global` from the Vercel
command or replace `--scope user` with `--scope project` in a GitHub command.

## Initialize

Run `/trellis-init`. It proposes `playbooks/` by default, lets you choose or adopt another folder,
and returns an optional `AGENTS.md` snippet for you to place manually.

## Create a Playbook

Give `/capture-playbook` a concrete description:

```text
/capture-playbook Create a Playbook for reviewing a small plugin release before tagging it. Check
source and generated packages, stop when generated output is stale, and finish with a clear go or
no-go decision backed by evidence.
```

## Discover candidates

Run `/discover-playbooks` on the current session or exact prior session IDs your host can retrieve.
It returns one or more self-contained `/capture-playbook ...` suggestions. Review or edit them,
then run the suggestions you want yourself.

## Audit

Run `/trellis-audit` and name the Playbooks folder to review. The audit is read-only and advisory.
It respects custom owner files and project-owned scripts.

## Methodology, privacy, and terms

- [Methodology](METHODOLOGY.md)
- [Privacy](PRIVACY.md)
- [Terms](TERMS.md)

## License

Trellis is dedicated to the public domain under [CC0 1.0 Universal](LICENSE).

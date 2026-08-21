---
name: trellis-init
description: Initialize or adopt a project-local Playbooks folder for Trellis. Use when the user asks to set up Trellis, chooses a Playbooks location, or invokes /trellis-init. Default to playbooks/ but let the user select another project-local folder. Create only the marked collection README and return an optional AGENTS.md snippet; never edit AGENTS.md, install dependencies, create a launcher, or stage, commit, push, or publish changes.
---

# Trellis Init

Initialize the smallest useful Trellis setup in a project.

## Outcome

The project has one selected Playbooks folder that future Trellis skills can recognize. Its
`README.md` contains a root marker and a small managed index. Init creates no Playbook and no
runtime; internal `_cli` support appears later only when a captured Playbook needs it.

## Choose the project and Playbooks folder

1. Use the exact work folder the user names. Otherwise use the host-designated current work
   folder. Do not widen to an enclosing Git repository.
2. If the user already named a Playbooks folder, validate and use it.
3. Otherwise ask one concise question:

   > Use the default `playbooks/` folder, choose another project-local folder, or adopt an
   > existing folder?

4. The selected path must be relative to the work-folder root, portable, and contained inside
   that root. Reject absolute paths, `..`, NUL, empty components, symlink traversal, and collisions
   that differ only by case or Unicode normalization.
5. Do not search the entire repository for possible collections. Inspect only the default path,
   a path the user names, or an explicitly scoped alternative.
6. If more than one marked collection is already in the explicit scope, ask the user which one to
   use. Do not merge collections by inference.

## Recognize or adopt an existing folder

A Trellis Playbooks folder contains this exact marker in its `README.md`:

```markdown
<!-- trellis-playbooks-root: format=1 -->
```

If the selected folder already has the marker, report that Trellis is initialized. Show missing
or malformed support as a repair plan instead of creating another collection.

If the folder exists without the marker, treat it as owner content. Ask whether the user wants to
adopt it. Adoption adds the root marker and managed index but does not move, rename, classify, or
index existing files automatically.

## File plan

For a new default setup, propose exactly:

```text
playbooks/
  README.md
```

For a custom folder, substitute that path everywhere.

Before writing, show:

- the selected work-folder root;
- the selected Playbooks folder;
- every file to create or edit;
- whether owner content already exists; and
- the exact managed block that will be added.

A direct request to initialize authorizes this disclosed low-risk setup after the folder choice
is resolved. Do not add dependencies, runtime files, Playbooks, scripts, or unrelated scaffolding.

## Collection README

Create or update `<playbooks-root>/README.md` with this shape. Preserve owner content outside the
managed block.

```markdown
<!-- trellis-playbooks-root: format=1 -->
# Project Playbooks

This folder contains project-local Playbooks for people and agents. Each Playbook owns one
recognizable situation through one verified outcome.

<!-- trellis-playbooks:index:start -->
_No Playbooks captured yet._
<!-- trellis-playbooks:index:end -->
```

When adopting an existing README:

- add the root marker once;
- add the managed index once;
- preserve the owner's title, introduction, and organization;
- do not index unmarked material automatically; and
- stop on malformed or duplicate Trellis markers.

## Write boundaries

- Inspect every destination and ancestor before writing.
- Reject symlinks and paths that resolve outside the selected work folder.
- Reread existing files immediately before writing and stop on drift.
- Use atomic replacement when the host supports it.
- Preserve all owner bytes outside the exact marker and managed-index changes.
- On partial failure, report every completed and incomplete effect. Do not continue by guess.
- Never run project code, install dependencies, or stage, commit, push, publish, or communicate
  externally.

## Finish

After setup:

1. verify the root marker and exactly one managed index block;
2. report the created or changed paths; and
3. return this optional snippet in chat with the actual relative path substituted:

```markdown
## Trellis

Project Playbooks live in [`playbooks/`](playbooks/). Read the relevant `PLAYBOOK.md` before
using or changing one.
```

Do not add the snippet to `AGENTS.md` or another instruction file. The user decides whether and
where to place it.

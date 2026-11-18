# Write a Playbook

A Playbook keeps one coherent repeatable task with the files it needs.

## What a request yields

[`SKILL.md`](../SKILL.md#what-the-request-authorizes) says which requests create a Playbook. The procedure the user intends is enough to write from: no history of successful use is needed, and writing it down does not show that it works.

A request for a template, such as an outline for status updates, yields a Playbook that says when and how to use it, with the outline as a starter in its `assets/`. When the starter already exists as a loose file, move it into the Playbook's `assets/`, keeping the name the handbook gives it, correct the links to it, and report the move. A loose file is that starter when it gives the structure of the output asked for, whatever it is called; say in the report that you took it so. A starter copied out of the handbook carries no relative links. Whoever fills a starter gives, for each topic that matters, a concrete account, an exact reference and how it applies, an open question that affects the work, or the reason it is left out.

When the user states no procedure, write the least that makes the starter usable: when to use it, where the copy goes, and a step for each of its parts, each marked proposed. Where the place the work goes does not exist yet, link what the area's README names and report the gap. After adding a Playbook, add its link to the README's navigation and change nothing else there.

Correcting an existing Playbook adds no step and does not change what the procedure does unless asked.

## The folder

```text
playbooks/<name>/
  playbook-<name>.md   the Playbook entry
  scripts/             optional: scripts and their tests
  references/          optional: longer guidance read only when a step needs it
  assets/              optional: files a step copies, fills or feeds to a script
```

Name a Playbook for its task, as a short verb phrase such as `prepare-workshop`. Refuse a name that differs from an existing one only by letter case or Unicode form.

[This skill's Playbook starter](../assets/playbook.md) has the entry's parts: when to use the Playbook and when not, its intended outcome, the method, the Checks and completion evidence, recovery and stopping, and a table of its scripts. Mark a step you infer as proposed, in the step. The entry names each file a step takes from the Playbook's `assets/` or `references/`; add a file to either only when a step uses it. A Playbook can call for a Check without deciding when that Check applies.

"When to use" names the moment the task comes up, as a contributor would notice it during the work, not the subject it concerns: not "reporting", but "the weekly report shows a change above the agreed threshold". The method starts with what to look at first. Where the task calls for a choice, write it at the step where it arises, as what the reader will see, what to do and why: "if the venue has not confirmed step-free access, hold the invitations, because they name the venue". Do not reduce a choice to a fixed step, and add none the procedure does not have.

Keep phases together when their judgment and verification depend on each other, and branches together when they start in the same situation and end at the same outcome. Split a task when its trigger, outcome or upkeep can stand alone: a request to save one routine that holds two such tasks yields two Playbooks. Sharing a client, a tool or a subject is no reason to combine tasks. No number of headings, steps or branches decides the boundary.

## Scripts

Plain instructions and commands the workspace already has come first. Add a script only when the request or the agreed procedure includes it, and only with a step of the Playbook that uses it. A Playbook may own tooling the project depends on: build, release or verification commands that other commands or CI call.

These rules cover a script you write or change, in any suitable language. Leave a script already in a Playbook as it is unless the request concerns it, and report where it departs from these rules only when that causes a concrete problem.

- **Scripts table.** The entry gives each script's command, what it reads, what it writes and its modes. The command is written relative to the workspace root and passes that root explicitly. With the table, the entry names the interpreter and dependencies the scripts need, and who else calls them: look at the command and CI definitions at the workspace root, or write "none found".
- **Read-only by default.** A script checks or reports, and writes only under an explicit flag. With no write flag, its modes cell says "reports only".
- **Inside the workspace.** It takes explicit paths rooted in the workspace and refuses a path that leaves it, through a symlink included. Its effects stay inside the workspace unless the entry declares what it reaches outside: another folder, a network service, a secret. A declaration describes the script and grants nothing: the task that runs it needs its own authority.
- **Fails closed.** A refusal exits non-zero and leaves no partial output.
- **Tested.** Its test sits beside it, named for the script file without its extension (`sync.mjs`, `sync.test.mjs`), with fixtures in `scripts/fixtures/`.

## Running a script

Path checks in a script, and its place in a handbook, are not a sandbox: only the host can confine a run.

While authoring, run only a script's tests, on fixtures, and only where you know the host confines the run to the workspace; not knowing counts as not confined. Otherwise supply the script for review and say that execution was not verified.

Test output and temporary files go to `<handbook>/.scratch/`, created with a `.gitignore` file containing `*`. When you finish, remove what you put there, that file included, and the folder once it is empty.

Running the Playbook's real task is separate work under its own authority. Report the tests you ran and their limits: passing tests on fixtures do not show that the Playbook works on real tasks.

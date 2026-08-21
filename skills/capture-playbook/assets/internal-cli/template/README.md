# Trellis internal Playbook CLI

This folder contains fixed local-file operations used by project Playbooks. It is internal
implementation support, not a second library of user-facing artifacts.

The available operations are:

- `file.hash`
- `files.compare`
- `text.replace`
- `json.set`

A tool folder contains only `tool.json`, which selects one operation. It does not contain generated
executable source. The shared runtime uses Node built-ins, rejects path escape and symlinks, and
requires a reviewed SHA-256 before applying a write.

Use the exact command documented by the owning `PLAYBOOK.md`. Typical forms are:

```text
node _cli/bin/trellis.mjs run <playbook> <tool> -- file=path/to/file
node _cli/bin/trellis.mjs plan <playbook> <tool> -- file=path/to/file from=old to=new
node _cli/bin/trellis.mjs apply <playbook> <tool> -- expectSha256=<reviewed-hash> file=path/to/file from=old to=new
```

A capability outside the four fixed operations belongs in an explicitly requested project-owned
script beside its Playbook.

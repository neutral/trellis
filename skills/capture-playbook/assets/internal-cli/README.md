# Trellis internal CLI asset

This asset defines the shared fixed-operation runtime that Capture can copy into
`<playbooks-root>/_cli/` when the first internal tool is approved.

An internal tool is declarative:

```text
_cli/tools/<playbook-id>/<tool-id>/
  tool.json
```

`tool.json` selects one operation implemented by the shared runtime:

- `file.hash`
- `files.compare`
- `text.replace`
- `json.set`

The runtime does not load generated tool code. It uses Node built-ins, accepts project-local
regular files, rejects path escape and symlinks, and binds every write to a reviewed SHA-256. Any
launcher stays inside `_cli/bin/`.

A project can instead request a standalone script beside a Playbook. That script remains
project-owned, can use broader explicitly disclosed capabilities, and does not inherit the
internal-tool safety profile.
